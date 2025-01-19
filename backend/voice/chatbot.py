
import os
import asyncio
import numpy as np
from dotenv import load_dotenv
from voice.personalities import PERSONALITIES, get_personality_chains
from langchain_openai import ChatOpenAI
from elevenlabs import ElevenLabs, play
import pyaudio
from faster_whisper import WhisperModel
import concurrent.futures
from langchain.schema import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.callbacks.base import BaseCallbackHandler

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file.")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in .env file.")

# -------------------------------------------------
# Initialize FasterWhisper
# -------------------------------------------------
whisper_model = WhisperModel(
    "small.en",
    device="cpu",
    compute_type="int8"
)

# Optionally, initialize ElevenLabs for TTS
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Load personalities (with multi-route prompt)
personalities = get_personality_chains(OPENAI_API_KEY)
PERSONALITY_NAMES = list(personalities.keys())

# -------------------------------------------------
# Custom Handler
# -------------------------------------------------
class NonStreamingCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.complete_response = []
        
    async def on_llm_start(self, *args, **kwargs):
        pass

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.complete_response.append(token)
        print(token, end="", flush=True)

    async def on_llm_end(self, *args, **kwargs):
        pass

    def get_complete_response(self):
        # Join tokens, remove any triple-backticks
        return ''.join(self.complete_response).replace('```', '').strip()

# # -------------------------------------------------
# # Optional TTS
# # -------------------------------------------------
async def generate_and_play_audio(text: str, voice_id: str):
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_flash_v2"
        )
        await asyncio.to_thread(play, audio)
    except Exception as e:
        print(f"TTS Error: {e}")

# -------------------------------------------------
# parse_personality_response
# -------------------------------------------------
def parse_personality_response(full_response: str):
    route, target, message = None, None, None
    lines = [ln.strip() for ln in full_response.splitlines() if ln.strip()]

    for ln in lines:
        low = ln.lower()
        if low.startswith("route:"):
            val = ln.split(":",1)[1].strip()
            if val in ["1","2"]:
                route = int(val)
        elif low.startswith("target:"):
            target = ln.split(":",1)[1].strip()
        elif low.startswith("message:"):
            message = ln.split(":",1)[1].strip()

    if route not in [1,2]:
        route = 2
        message = full_response
    if route == 1 and not target:
        route = 2
    if not message:
        message = full_response

    return route, target, message

# -------------------------------------------------
# get_response: multi-route
# -------------------------------------------------
async def get_response(personality_name, history, user_input):
    """
    Asks the chosen personality to respond. Possibly re-routes or speaks to user.
    """
    personality_data = personalities.get(personality_name)
    if not personality_data:
        print(f"[Error] Personality '{personality_name}' not found.")
        return 2, None, "Personality not found."

    chain = personality_data["chain"]
    voice_id = personality_data["voice_id"]

    handler = NonStreamingCallbackHandler()
    try:
        await chain.ainvoke(
            {"history": history, "user_input": user_input},
            config={"callbacks": [handler]}
        )
        raw_response = handler.get_complete_response()
        route, target, message = parse_personality_response(raw_response)
        print(f"[Response] Route: {route}, Target: {target}, Message: {message}")
        return route, target, message
    except Exception as e:
        print(f"Error in get_response: {e}")
        return 2, None, f"Encountered an error: {str(e)}"

# -------------------------------------------------
# Silence-based audio
# -------------------------------------------------
def record_audio(rate=16000, chunk=220, silence_threshold=100, silence_duration=2):
    """
    Records one chunk of user speech, ending after 'silence_duration' seconds of silence.
    """
    audio = pyaudio.PyAudio()
    stream = audio.open(
        rate=rate, format=pyaudio.paInt16, channels=1,
        input=True, frames_per_buffer=chunk
    )
    frames = []
    long_term_noise = 0.0
    curr_noise = 0.0
    voice_detected = False
    silent_time = 0.0

    print(f"Start speaking... (Stop after {silence_duration}s of silence)")

    while True:
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        pegel = np.abs(np.frombuffer(data, dtype=np.int16)).mean()

        long_term_noise = 0.99 * long_term_noise + 0.01 * pegel
        curr_noise = 0.90 * curr_noise + 0.10 * pegel

        if voice_detected:
            if curr_noise < long_term_noise + silence_threshold:
                silent_time += chunk / rate
                if silent_time >= silence_duration:
                    break
            else:
                silent_time = 0.0
        else:
            if curr_noise > long_term_noise + silence_threshold:
                voice_detected = True
                silent_time = 0.0

    stream.stop_stream()
    stream.close()
    audio.terminate()

    audio_bytes = b''.join(frames)
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    return audio_np

async def transcribe_audio_async(audio_np):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        text = await loop.run_in_executor(pool, transcribe_audio, audio_np)
    return text.strip()

def transcribe_audio(audio_np):
    segments, info = whisper_model.transcribe(audio_np, beam_size=1)
    return " ".join(s.text for s in segments).strip()

# -------------------------------------------------
# Decider
# -------------------------------------------------
decider_llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-4o-mini",
    temperature=0.0,
    streaming=False
)

def generate_decider_prompt(personalities):
    """
    Dynamically generates the DECIDER_SYSTEM_PROMPT based on the personalities in personalities.py.
    """
    personality_details = "\n".join(
        [f"- {p['name']}: {p['description']}" for p in personalities]
    )
    return f"""You are a router that chooses which personality is best suited to respond based on the user's message. 
Choose the most appropriate personality from the following list and reply with only one name:
{personality_details}

Do not include any additional text."""


# DECIDER_SYSTEM_PROMPT = # Generate DECIDER_SYSTEM_PROMPT dynamically
DECIDER_SYSTEM_PROMPT = generate_decider_prompt(PERSONALITIES)


async def decide_personality(user_text: str) -> str:
    msgs = [
        {"role":"system", "content":DECIDER_SYSTEM_PROMPT},
        {"role":"user", "content":user_text}
    ]
    out = await decider_llm.agenerate([msgs])
    decided = out.generations[0][0].text.strip()
    # Validate the decision
    valid_personalities = [name.lower() for name in PERSONALITY_NAMES]
    for name in PERSONALITY_NAMES:
        if name.lower() == decided.lower():
            return name
    return "RBC Judge" 

# -------------------------------------------------
# Main Chat Loop
# -------------------------------------------------
async def chat_loop():
    chat_history = ChatMessageHistory()
    print("\n Chatbot is ready. Press Enter to speak. Type 'exit' to quit.")

    while True:
        input_trigger = input("\n Press Enter to speak or 'exit' to quit: ")
        if input_trigger.lower() in ["exit", "quit", "bye"]:
            print("Exiting chat. Goodbye!")
            # await generate_and_play_audio("Goodbye!", "JBFqnCBsd6RMkjVDRZzb")
            break

        audio_np = await asyncio.to_thread(record_audio)
        user_input = await transcribe_audio_async(audio_np)
        audio_length = len(audio_np) / 16000  # Assuming 16kHz
        if not user_input:
            continue
        num_words = len(user_input.split())
        wpm = num_words / audio_length * 60

        print(f"User: {user_input} [{wpm:.1f} wpm]")

        # Add user message to history
        chat_history.add_message(HumanMessage(content=user_input))

        # Format conversation so far for the chain
        formatted_history = ""
        for message in chat_history.messages:
            if isinstance(message, HumanMessage):
                formatted_history += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                formatted_history += f"Assistant: {message.content}\n"

        # Check if user explicitly mentions a personality by name
        chosen_personality = None
        for p in PERSONALITY_NAMES:
            if p.lower() in user_input.lower():
                chosen_personality = p
                break

        if not chosen_personality:
            # Use decider to figure out best initial personality
            chosen_personality = await decide_personality(user_input)

        print(f"\n[Routing to initial personality: {chosen_personality}]\n")

        # Now we handle the multi-step routing among personalities
        current_personality = chosen_personality
        current_input = user_input
        routing_iterations = 0
        max_routing = 2  # in case they bounce back forever

        while routing_iterations < max_routing:
            routing_iterations += 1

            print(f"\n{current_personality} responding...\n")
            # Get that personality's response
            route, target, message = await get_response(
                personality_name=current_personality,
                history=formatted_history,
                user_input=current_input
            )

            # Add the message to chat history
            chat_history.add_message(AIMessage(content=message))

            if route == 2:
                # The personality is speaking directly to the user
                print(f"\n{current_personality} => User: {message}\n")
                break
            else:
                # route == 1: pass the message to the target personality
                if target not in PERSONALITY_NAMES:
                    print(f"Unknown target personality '{target}'. Ending routing.")
                    break
                print(f"\n{current_personality} => {target}: {message}\n")

                # Update for next iteration
                current_personality = target
                current_input = message

if __name__ == "__main__":
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")