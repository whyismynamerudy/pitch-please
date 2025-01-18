
import sys
import select
import termios
import tty
import os
import asyncio
import numpy as np
import collections
from dotenv import load_dotenv
from personalities import get_personality_chains
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
# Initialize Models
# -------------------------------------------------
whisper_model = WhisperModel(
    "small.en",
    device="cpu",
    compute_type="int8"
)

# elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Load personalities first
personalities = get_personality_chains(OPENAI_API_KEY)
PERSONALITY_NAMES = list(personalities.keys())

# -------------------------------------------------
# Custom Non-Streaming Handler
# -------------------------------------------------
class NonStreamingCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.complete_response = []
        
    async def on_llm_start(self, *args, **kwargs):
        pass

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.complete_response.append(token)
        print(token, end="", flush=True)  # Keep printing as it streams

    async def on_llm_end(self, *args, **kwargs):
        pass

    def get_complete_response(self):
        full_response = ''.join(self.complete_response)
        # Clean up any extraneous tokens
        clean_response = full_response.replace('```', '').strip()
        return clean_response

# # -------------------------------------------------
# # Audio Generation
# # -------------------------------------------------
# async def generate_and_play_audio(text: str, voice_id: str):
#     try:
#         audio = elevenlabs_client.text_to_speech.convert(
#             text=text,
#             voice_id=voice_id,
#             model_id="eleven_flash_v2"
#         )
#         await asyncio.to_thread(play, audio)
#     except Exception as e:
#         print(f"\nTTS Error: {e}")

# -------------------------------------------------
# Response Generation
async def get_response(personality_name, history, user_input):
    """
    Calls the personality's chain with (history, user_input).
    Plays audio for each response immediately after generating it.
    """
    personality_data = personalities.get(personality_name)
    if not personality_data:
        return 2, None, "Personality not found."
    
    chain = personality_data["chain"]
    voice_id = personality_data["voice_id"]
    
    handler = NonStreamingCallbackHandler()
    
    try:
        # Generate the full response text
        await chain.ainvoke(
            {
                "history": history,
                "user_input": user_input
            },
            config={"callbacks": [handler]}
        )
        
        full_response = handler.get_complete_response()

        # Parse the response to extract Route, Target, and Message
        route, target, message = parse_personality_response(full_response)

        # Play the message audio immediately
        # await generate_and_play_audio(message, voice_id)

        return route, target, message
    except Exception as e:
        print(f"Error in get_response: {e}")
        return 2, None, f"I apologize, but I encountered an error: {str(e)}"

# -------------------------------------------------
# Audio Recording and Transcription
# -------------------------------------------------
first_run = True  # Global flag for first run

def record_audio(rate=16000, chunk=220, silence_threshold=100, silence_duration=1):
    global first_run  # Access the global flag
    audio = pyaudio.PyAudio()
    stream_audio = audio.open(
        rate=rate,
        format=pyaudio.paInt16,
        channels=1,
        input=True,
        frames_per_buffer=chunk
    )

    frames = []
    audio_buffer = collections.deque(maxlen=int((rate / chunk) * silence_duration))
    long_term_noise_level = 0.0
    current_noise_level = 0.0
    voice_activity_detected = False
    silence_timer = 0.0

    print("Start speaking...")

    if first_run:
        print("Press any key to end your speech.")
        # Set terminal to raw mode to detect a single key press
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)  # Switch to raw mode
            while True:
                data = stream_audio.read(chunk, exception_on_overflow=False)
                frames.append(data)
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    print("Speech ended by key press.")
                    sys.stdin.read(1)  # Consume the key press
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # Restore terminal settings
   
    else:
        while True:
            data = stream_audio.read(chunk, exception_on_overflow=False)
            pegel = np.abs(np.frombuffer(data, dtype=np.int16)).mean()

            long_term_noise_level = long_term_noise_level * 0.99 + pegel * (1.0 - 0.99)
            current_noise_level = current_noise_level * 0.90 + pegel * (1.0 - 0.90)

            if voice_activity_detected:
                frames.append(data)
                if current_noise_level < long_term_noise_level + silence_threshold:
                    silence_timer += chunk / rate
                    if silence_timer >= silence_duration:
                        break
                else:
                    silence_timer = 0.0
            else:
                if current_noise_level > long_term_noise_level + silence_threshold:
                    voice_activity_detected = True
                    frames.extend(audio_buffer)
                    audio_buffer.clear()
                    silence_timer = 0.0
                else:
                    audio_buffer.append(data)

    stream_audio.stop_stream()
    stream_audio.close()
    audio.terminate()

    # Update the global flag after the first run
    # global first_run
    first_run = False

    audio_bytes = b''.join(frames)
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    return audio_np

async def transcribe_audio_async(audio_np):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        text = await loop.run_in_executor(pool, transcribe_audio, audio_np)
    return text

def transcribe_audio(audio_np):
    segments, info = whisper_model.transcribe(audio_np, beam_size=1)
    return " ".join(segment.text for segment in segments).strip()

# -------------------------------------------------
# Decider Chain (for initial choice)
# -------------------------------------------------
decider_llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-4o-mini",
    temperature=0.0,
    streaming=False,
)

DECIDER_SYSTEM_PROMPT = """You are a router that chooses which personality (Alice, Bob, or Charlie) is best suited to respond based on the user's message. Reply with only one name: "Alice", "Bob", or "Charlie" (nothing else)."""

async def decide_personality(user_text: str) -> str:
    messages = [
        {"role": "system", "content": DECIDER_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    output = await decider_llm.agenerate([messages])
    text = output.generations[0][0].text.strip()
    return text if text in PERSONALITY_NAMES else "Alice"

# -------------------------------------------------
# NEW / UPDATED CODE
# -------------------------------------------------
def parse_personality_response(full_response: str):
    """
    Given a personality's full response text, 
    parse out:
      Route: (1 or 2)
      Target: (only valid if Route=1)
      Message: (actual text)

    If parse fails, default to Route=2 (speak to user) 
    and entire text as the message.
    """
    route = None
    target = None
    message = None

    lines = [line.strip() for line in full_response.splitlines() if line.strip()]

    # Simple approach: look for lines starting with "Route:", "Target:", "Message:"
    for line in lines:
        if line.lower().startswith("route:"):
            # e.g. "Route: 1"
            route_value = line.split(":", 1)[1].strip()
            if route_value in ["1", "2"]:
                route = int(route_value)
        elif line.lower().startswith("target:"):
            # e.g. "Target: Bob"
            target = line.split(":", 1)[1].strip()
        elif line.lower().startswith("message:"):
            # everything after 'Message:' is the content
            message = line.split(":", 1)[1].strip()
    
    # If we can't parse anything, fallback
    if route not in [1, 2]:
        route = 2  # default speak to user
        message = full_response  # entire text
    if route == 1 and not target:
        # If it said route=1 but no target, fallback
        route = 2
    if not message:
        # fallback to entire text
        message = full_response
    
    return route, target, message

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
