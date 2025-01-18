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

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Load personalities first so we can use them throughout the code
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
        print(token, end="", flush=True)

    async def on_llm_end(self, *args, **kwargs):
        pass

    def get_complete_response(self):
        full_response = ''.join(self.complete_response)
        clean_response = full_response.replace('```', '').replace('SpeakWithEachOther: false', '').replace('SpeakWithEachOther: true', '').strip()
        return clean_response

# -------------------------------------------------
# Audio Generation
# -------------------------------------------------
async def generate_and_play_audio(text: str, voice_id: str):
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_monolingual_v1"
        )
        await asyncio.to_thread(play, audio)
    except Exception as e:
        print(f"\nTTS Error: {e}")

# -------------------------------------------------
# Response Generation
# -------------------------------------------------
async def get_response(personality_name, history, user_input):
    personality_data = personalities.get(personality_name)
    if not personality_data:
        return "Personality not found."
    
    chain = personality_data["chain"]
    voice_id = personality_data["voice_id"]
    
    handler = NonStreamingCallbackHandler()
    
    try:
        # Get the complete response first
        await chain.ainvoke(
            {
                "history": history,
                "user_input": user_input
            },
            config={"callbacks": [handler]}
        )
        
        response = handler.get_complete_response()
        
        # Then generate and play the audio
        await generate_and_play_audio(response, voice_id)
        
        return response
    except Exception as e:
        print(f"Error in get_response: {e}")
        return f"I apologize, but I encountered an error: {str(e)}"

# -------------------------------------------------
# Audio Recording and Transcription
# -------------------------------------------------
def record_audio(rate=16000, chunk=220, silence_threshold=100, silence_duration=1):
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
# Decider Chain
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
# Main Chat Loop
# -------------------------------------------------
async def chat_loop():
    chat_history = ChatMessageHistory()
    print("\n Chatbot is ready. Press Enter to speak. Type 'exit' to quit.")

    while True:
        input_trigger = input("Press Enter to speak or 'exit' to quit: ")
        if input_trigger.lower() in ["exit", "quit", "bye"]:
            print("Exiting chat. Goodbye!")
            await generate_and_play_audio("Goodbye!", "JBFqnCBsd6RMkjVDRZzb")
            break

        audio_np = await asyncio.to_thread(record_audio)
        user_input = await transcribe_audio_async(audio_np)
        if not user_input:
            continue

        print(f"You said: {user_input}")
        chat_history.add_message(HumanMessage(content=user_input))

        formatted_history = ""
        for message in chat_history.messages:
            if isinstance(message, HumanMessage):
                formatted_history += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                formatted_history += f"Assistant: {message.content}\n"

        chosen_personality = None
        for p in PERSONALITY_NAMES:
            if p.lower() in user_input.lower():
                chosen_personality = p
                break

        if not chosen_personality:
            chosen_personality = await decide_personality(user_input)

        print(f"\n{chosen_personality}: ", end="", flush=True)
        response = await get_response(chosen_personality, formatted_history, user_input)
        chat_history.add_message(AIMessage(content=response))

if __name__ == "__main__":
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")