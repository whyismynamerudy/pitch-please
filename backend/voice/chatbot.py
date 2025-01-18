import os
import asyncio
import wave
import numpy as np
import collections
from dotenv import load_dotenv
from personalities import get_personality_chains
from langchain_openai import ChatOpenAI
from elevenlabs import ElevenLabs, stream

import pyaudio
from faster_whisper import WhisperModel
import concurrent.futures  
from langchain.schema import HumanMessage, AIMessage
from langchain.memory import ChatMessageHistory

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file.")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in .env file.")

whisper_model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8"
)

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

personalities = get_personality_chains(OPENAI_API_KEY)
PERSONALITY_NAMES = list(personalities.keys())  

decider_llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-4o-mini",  
    temperature=0.0,  
    streaming=False,
)

# A short system prompt for the decider
DECIDER_SYSTEM_PROMPT = """You are a router that chooses which personality (Alice, Bob, or Charlie) is best suited to respond based on the user's message. Reply with only one name: "Alice", "Bob", or "Charlie" (nothing else)."""

async def decide_personality(user_text: str) -> str:
    """
    Calls a small LLM chain to pick the best personality for the given user_text.
    Returns "Alice", "Bob", or "Charlie".
    """
    messages = [
        {"role": "system", "content": DECIDER_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    output = await decider_llm.agenerate([messages])
    text = output.generations[0][0].text.strip()

    # default to "Alice" if it doesn't produce a valid name
    if text not in PERSONALITY_NAMES:
        text = "Alice"
    return text

def record_audio(
    filename="voice_record.wav",
    rate=16000,
    chunk=220,
    silence_threshold=100,
    silence_duration=1
):
    audio = pyaudio.PyAudio()
    stream_audio = audio.open(
        rate=rate,
        format=pyaudio.paInt16,
        channels=1,
        input=True,
        frames_per_buffer=chunk
    )

    frames = []
    audio_buffer = collections.deque(
        maxlen=int((rate / chunk) * silence_duration)
    )
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

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))

    # length of audio file in seconds
    audio_length = len(frames) * chunk / rate
    
    return filename, audio_length

def transcribe_audio(filename):
    segments, info = whisper_model.transcribe(filename, beam_size=1)
    text = " ".join(segment.text for segment in segments).strip()
    return text

async def transcribe_audio_async(filename):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        text = await loop.run_in_executor(pool, transcribe_audio, filename)
    return text

async def get_response(personality_name, history, user_input):
    chain = personalities.get(personality_name)
    if not chain:
        return "Personality not found."
    response = await chain.arun(
        history=history,
        user_input=user_input
    )
    return response

def parse_speak_with_each_other(response_text):
    """
    Checks if the LLM wants to speak among personalities or to the user.
    Returns a dict of the form:
      {
        "speak_with_each_other": bool,
        "lines": [
           ("Alice", "some text"),
           ("Bob", "some text"),
           ("Charlie", "some text")
         ] or [("UserDirected", "some text")]
      }
    """
    parsed_output = {
        "speak_with_each_other": False,
        "lines": []
    }

    # Check for the SpeakWithEachOther flag
    if "SpeakWithEachOther: true" in response_text:
        parsed_output["speak_with_each_other"] = True

        try:
            lines = response_text.splitlines()
            flag_index = next(i for i, line in enumerate(lines) if "SpeakWithEachOther: true" in line)
            for line in lines[flag_index + 1:]:
                line = line.strip()
                if any(line.startswith(p + ":") for p in PERSONALITY_NAMES):
                    speaker, content = line.split(":", 1)
                    parsed_output["lines"].append((speaker.strip(), content.strip()))
        except StopIteration:
            parsed_output["speak_with_each_other"] = False
            parsed_output["lines"] = [("UserDirected", response_text)]

    elif "SpeakWithEachOther: false" in response_text:
        parsed_output["speak_with_each_other"] = False
        # Extract the user-directed response
        try:
            # Split the response into lines
            lines = response_text.splitlines()
            # Find the line with the flag
            flag_index = next(i for i, line in enumerate(lines) if "SpeakWithEachOther: false" in line)
            user_response = lines[flag_index + 1].strip()
            parsed_output["lines"] = [("UserDirected", user_response)]
        except (StopIteration, IndexError):
            parsed_output["lines"] = [("UserDirected", response_text)]
    else:
        # If no flag is present, treat the entire response as user-directed
        parsed_output["lines"] = [("UserDirected", response_text)]

    return parsed_output

async def chat_loop():
    chat_history = ChatMessageHistory()

    print("Chatbot is ready. Press Enter to speak. Type 'exit' to quit.")

    while True:
        input_trigger = input("Press Enter to speak or 'exit' to quit: ")
        if input_trigger.lower() in ["exit", "quit", "bye"]:
            print("Exiting chat. Goodbye!")
            audio_stream = elevenlabs_client.text_to_speech.convert_as_stream(
                text="Goodbye!",
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                model_id="eleven_monolingual_v1"
            )
            stream(audio_stream)
            break

        # 1) Record from microphone, then transcribe
        audio_file, audio_length = record_audio()
        user_input = await transcribe_audio_async(audio_file)
        if not user_input:
            continue
        num_words = len(user_input.split())
        wpm = num_words / audio_length * 60

        print(f"User: {user_input} [{wpm} wpm]")

        # 2) Add user message to history
        chat_history.add_message(HumanMessage(content=user_input))

        # 3) Format history for the prompt
        formatted_history = ""
        for message in chat_history.messages:
            if isinstance(message, HumanMessage):
                formatted_history += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                formatted_history += f"{message.content}\n"

        chosen_personality = None
        for p in PERSONALITY_NAMES:
            if p.lower() in user_input.lower():
                chosen_personality = p
                break

        if not chosen_personality:
            chosen_personality = await decide_personality(user_input)

        print(f"Selected personality: {chosen_personality}")

        response = await get_response(chosen_personality, formatted_history, user_input)

        chat_history.add_message(AIMessage(content=response))

        parsed = parse_speak_with_each_other(response)

        if parsed["speak_with_each_other"]:
            print(f"{chosen_personality} decided to speak with the others.")
            for (speaker, text) in parsed["lines"]:
                print(f"{speaker}: {text}")
                chat_history.add_message(AIMessage(content=text))
                # TTS
                audio_stream = elevenlabs_client.text_to_speech.convert_as_stream(
                    text=text,
                    voice_id="JBFqnCBsd6RMkjVDRZzb",
                    model_id="eleven_monolingual_v1"
                )
                stream(audio_stream)
        else:
            text = parsed["lines"][0][1]
            print(f"{chosen_personality}: {text}")
            chat_history.add_message(AIMessage(content=text))
            # TTS
            audio_stream = elevenlabs_client.text_to_speech.convert_as_stream(
                text=text,
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                model_id="eleven_monolingual_v1"
            )
            stream(audio_stream)

if __name__ == "__main__":
    asyncio.run(chat_loop())
