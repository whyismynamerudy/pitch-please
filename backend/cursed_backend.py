# backend.py

import io
import sys
import aiohttp
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
from deepface import DeepFace
from typing import Dict, Any
from collections import defaultdict
import json
import asyncio
import os

# ========== Import from chatbot pieces ==========
from judges.evaluation import EnhancedEvaluator
from voice.chatbot import (
    decide_personality,  # Our decider that picks which judge
    get_response,        # The function that fetches LLM responses from the judge
    record_audio,        # Silence-based recording
    transcribe_audio_async,
    PERSONALITY_NAMES    # List of all personalities
)
from langchain.schema import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory

# Load environment variables (for the AI API keys, etc.)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class PitchEvaluation(BaseModel):
    transcript: str
    wpm: float
    time: str
    emotions: Dict[str, float]

app = FastAPI()

# ------------------------------------------------
# CORS Setup
# ------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed
    allow_methods=["*"],
    allow_headers=["*"]
)

# ------------------------------------------------
# EMOTION Detection Globals
# ------------------------------------------------
is_recording = False
video_capture = None
emotion_counts = defaultdict(int)
total_frames = 0
threshold = 5.0  # minimum % threshold for listing an emotion

# ------------------------------------------------
# CHATBOT / Q&A Globals
# ------------------------------------------------
chat_history = ChatMessageHistory()
transcript_messages = []
chat_active = False
qna_mode = False

# We use a lock to prevent launching multiple Q&A loops
qna_lock = asyncio.Lock()

# We also have an event to ensure pitch is captured before Q&A
pitch_captured_event = asyncio.Event()

# For sending transcript updates to multiple front-end clients
transcript_websockets = []

# ------------------------------------------------
# WEBCAM + EMOTION DETECTION
# ------------------------------------------------
@app.websocket("/ws")
async def webcam_feed(websocket: WebSocket):
    """
    Streams the webcam feed with emotion detection.
    """
    global is_recording, video_capture, emotion_counts, total_frames

    await websocket.accept()
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        await websocket.send_json({"error": "Unable to access the webcam."})
        await websocket.close()
        return

    is_recording = True
    emotion_counts.clear()
    total_frames = 0

    try:
        while is_recording:
            ret, frame = video_capture.read()
            if not ret:
                break

            # Face + emotion detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30,30))
            if len(faces) > 0:
                x, y, w, h = faces[0]
                roi = frame[y:y+h, x:x+w]
                try:
                    result = DeepFace.analyze(roi, actions=["emotion"], enforce_detection=False)
                    dom_emotion = max(result[0]["emotion"].items(), key=lambda x: x[1])[0]
                    emotion_counts[dom_emotion] += 1
                    total_frames += 1

                    # Draw bounding box
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
                    cv2.putText(frame, dom_emotion, (x,y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
                except Exception as e:
                    print(f"Emotion analysis error: {e}")

            # Send frame to front-end
            _, buf = cv2.imencode(".jpg", frame)
            await websocket.send_bytes(buf.tobytes())
            await asyncio.sleep(0.03)

    except WebSocketDisconnect:
        print("WebSocket (video) disconnected.")
    finally:
        video_capture.release()
        cv2.destroyAllWindows()
        if total_frames > 0:
            save_emotion_data()

@app.websocket("/ws_transcript")
async def transcript_feed(websocket: WebSocket):
    """
    Streams real-time transcript updates to the frontend.
    """
    await websocket.accept()
    transcript_websockets.append(websocket)
    print("Transcript WebSocket connected.")

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        transcript_websockets.remove(websocket)
        print("Transcript WebSocket disconnected.")

def save_emotion_data():
    """
    Summarize emotions into a .json for further analysis.
    """
    global total_frames, emotion_counts, threshold
    if total_frames > 0:
        percentages = {
            em: (count/total_frames)*100 for em, count in emotion_counts.items()
        }
        filtered = {
            em: pct for em, pct in percentages.items() if pct >= threshold
        }
        sorted_emotions = dict(sorted(filtered.items(), key=lambda x: x[1], reverse=True))
        with open("emotion_data.json","w") as f:
            json.dump(sorted_emotions, f, indent=4)
        print("Saved emotion_data.json")

# ------------------------------------------------
# STOP
# ------------------------------------------------
@app.get("/stop")
async def stop_all():
    """
    Stops the chat session (camera + Q&A).
    """
    global is_recording, chat_active, qna_mode
    is_recording = False
    chat_active = False
    qna_mode = False
    pitch_captured_event.set()  # ensure any waiting tasks are unblocked
    return JSONResponse({"message": "Session stopped."})

# ------------------------------------------------
# START CHAT (PITCH)
# ------------------------------------------------
@app.get("/start_chat")
async def start_chat(bg: BackgroundTasks):
    """
    Clears old data + captures pitch before Q&A.
    """
    global chat_active, qna_mode, chat_history, transcript_messages
    chat_active = True
    qna_mode = False
    chat_history = ChatMessageHistory()
    transcript_messages = []

    # Reset pitch capture
    pitch_captured_event.clear()
    bg.add_task(pitch_capture_task)
    return {"message":"Chat session started (capturing pitch)."}

async def pitch_capture_task():
    """
    Record a pitch and add it as the first user message in chat_history.
    """
    global chat_active, chat_history, transcript_messages
    if not chat_active:
        return

    pitch_audio = await asyncio.to_thread(record_audio, 16000, 220, 100, 2)
    pitch_text = await transcribe_audio_async(pitch_audio)
    pitch_text = pitch_text.strip()

    if pitch_text:
        # Add pitch as the first message
        chat_history.add_message(HumanMessage(content=pitch_text))
        transcript_messages.append(("User (Pitch)", pitch_text))
        await broadcast_transcript(("User (Pitch)", pitch_text))
    else:
        await broadcast_transcript(("System", "No pitch captured."))

    pitch_captured_event.set()  # Signal that the pitch has been captured


# ------------------------------------------------
# Q&A
# ------------------------------------------------
@app.get("/begin_qna")
async def begin_qna(bg: BackgroundTasks):
    """
    Start Q&A once the pitch is captured.
    """
    global qna_mode
    if qna_lock.locked():
        return JSONResponse({"message": "Q&A session already active"}, status_code=400)

    qna_mode = True
    bg.add_task(qna_loop)
    return {"message": "Q&A mode started. Judges can respond."}


async def qna_loop():
    """
    Multi-route Q&A:
      user => judge => possible route => user => judge => route ...
    """
    global chat_active, qna_mode, chat_history, transcript_messages
    async with qna_lock:
        try:
            # Wait for the pitch to be captured
            await pitch_captured_event.wait()

            while chat_active and qna_mode:
                # If only the pitch exists in chat history, start Q&A
                if len(chat_history.messages) == 1:
                    # Choose the initial judge
                    initial_judge = await decide_personality("Start Q&A based on the pitch.")
                    route, target, message = await get_response(
                        personality_name=initial_judge,
                        history=formatted_history(chat_history),
                        user_input="Start Q&A"
                    )
                    chat_history.add_message(AIMessage(content=message))
                    transcript_messages.append((initial_judge, message))
                    await broadcast_transcript((initial_judge, message))

                    # If the judge routes to another judge
                    if route == 1 and target in PERSONALITY_NAMES:
                        route2, target2, message2 = await get_response(
                            personality_name=target,
                            history=formatted_history(chat_history),
                            user_input=message
                        )
                        chat_history.add_message(AIMessage(content=message2))
                        transcript_messages.append((target, message2))
                        await broadcast_transcript((target, message2))

                        # --- ADDED CODE BELOW ---
                        if target in judge_voices:
                            await generate_and_play_audio_streaming(message2, judge_voices[target])
                        # --- END ADDED CODE ---

                # Handle user input after the pitch
                user_audio = await asyncio.to_thread(record_audio, 16000, 220, 100, 2)
                user_text = await transcribe_audio_async(user_audio)
                user_text = user_text.strip()
                if not user_text:
                    continue

                # Add user message to history
                chat_history.add_message(HumanMessage(content=user_text))
                transcript_messages.append(("User", user_text))
                await broadcast_transcript(("User", user_text))

                # Determine which judge responds
                chosen_judge = None
                for personality in PERSONALITY_NAMES:
                    if personality.lower() in user_text.lower():
                        chosen_judge = personality
                        break

                if not chosen_judge:
                    # Decide based on conversation context
                    chosen_judge = await decide_personality(user_text)

                # Get the judge's response
                route, target, message = await get_response(
                    personality_name=chosen_judge,
                    history=formatted_history(chat_history),
                    user_input=user_text
                )
                chat_history.add_message(AIMessage(content=message))
                transcript_messages.append((chosen_judge, message))
                await broadcast_transcript((chosen_judge, message))

                # --- ADDED CODE BELOW ---
                # Whenever it's a known judge, stream TTS in the backend
                if chosen_judge in judge_voices:
                    await generate_and_play_audio_streaming(message, judge_voices[chosen_judge])
                # --- END ADDED CODE ---

                # If the response routes to another judge
                if route == 1 and target in PERSONALITY_NAMES:
                    route2, target2, message2 = await get_response(
                        personality_name=target,
                        history=formatted_history(chat_history),
                        user_input=message
                    )
                    chat_history.add_message(AIMessage(content=message2))
                    transcript_messages.append((target, message2))
                    await broadcast_transcript((target, message2))

                    # --- ADDED CODE BELOW ---
                    if target in judge_voices:
                        await generate_and_play_audio_streaming(message2, judge_voices[target])
                    # --- END ADDED CODE ---

        except Exception as e:
            print(f"Error in Q&A loop: {e}")
            await broadcast_transcript(("System", "An error occurred during Q&A."))
        finally:
            qna_mode = False

# ------------------------------------------------
# HELPER: broadcast transcript
# ------------------------------------------------
async def broadcast_transcript(msg: tuple):
    """
    Send a single transcript message to all connected front-ends.
    """
    data = {"speaker": msg[0], "text": msg[1]}
    to_remove = []
    for ws in transcript_websockets:
        try:
            await ws.send_json(data)
        except:
            to_remove.append(ws)
    for dead_ws in to_remove:
        transcript_websockets.remove(dead_ws)

def formatted_history(chat_history: ChatMessageHistory) -> str:
    """
    Formats the chat history for LLM consumption, clearly labeling the pitch.
    """
    history = ""
    for i, message in enumerate(chat_history.messages):
        if i == 0:
            history += f"User (Pitch): {message.content}\n"
        elif isinstance(message, HumanMessage):
            history += f"User: {message.content}\n"
        elif isinstance(message, AIMessage):
            history += f"Assistant: {message.content}\n"
    return history

# ------------------------------------------------
# ANALYSIS + PITCH EVAL
# ------------------------------------------------
class TimerData(BaseModel):
    time_left: int
    transcript: list[dict[str, str]]

def calculate_time_spent(time_left: int) -> str:
    total=300
    spent=total-time_left
    mm=spent//60
    ss=spent%60
    return f"{mm}:{str(ss).zfill(2)}"

def create_transcript_json(transcript_data, wpm, time_spent, emotion_data=None):
    txt = "\n".join([f"{d['speaker']}: {d['text']}" for d in transcript_data])
    data = {
        "transcript": txt,
        "wpm": wpm,
        "time": time_spent
    }
    if emotion_data:
        data["emotions"] = emotion_data

    try:
        with open("transcript_analysis.json","w") as f:
            json.dump(data,f,indent=4)
        print("Analysis saved to transcript_analysis.json")
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return None
    return data


@app.post("/generate_analysis")
async def generate_analysis(data: TimerData):
    """
    Generate transcript analysis -> pass to evaluate_pitch.
    """
    try:
        # Calculate time
        t_spent = calculate_time_spent(data.time_left)
        print("calculate time spent done")

        # Calculate WPM
        total_words = sum(len(msg['text'].split()) for msg in data.transcript)
        time_in_minutes = (300 - data.time_left) / 60  # Convert seconds to minutes
        wpm = total_words / time_in_minutes if time_in_minutes > 0 else 0
        print("calcualted wpm done")
        
        # Read emotion data
        emotion_data = {}
        try:
            with open("emotion_data.json", "r") as f:
                emotion_data = json.load(f)
        except FileNotFoundError:
            print("No emotion data found - continuing without emotion data")
        except json.JSONDecodeError:
            print("Invalid emotion data format - continuing without emotion data")

        print("read emotion data")
            
        # Create transcript JSON
        transcript_data = create_transcript_json(data.transcript, wpm, t_spent, emotion_data)
        if not transcript_data:
            return JSONResponse({
                "error": "Failed to create transcript analysis"
            }, status_code=500)
        
        print("transcript data done")
            
        # Build pitch evaluation object
        combined = "\n".join([f"{x['speaker']}: {x['text']}" for x in data.transcript])
        pitch_eval = PitchEvaluation(
            transcript=combined,
            wpm=wpm,
            time=t_spent,
            emotions=emotion_data
        )
        
        # Call evaluate_pitch
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                    "http://127.0.0.1:8000/evaluate_pitch",
                    json=pitch_eval.dict()
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return JSONResponse({
                            "error": f"Evaluation failed with status {resp.status}: {error_text}"
                        }, status_code=500)
                    eval_res = await resp.json()
        except aiohttp.ClientError as e:
            return JSONResponse({
                "error": f"Failed to connect to evaluation service: {str(e)}"
            }, status_code=500)
        
        print("called eval pitch")
        
        # Return successful response
        return JSONResponse({
            "analysis_result": transcript_data,
            "evaluation_response": eval_res
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in generate_analysis: {error_trace}")
        return JSONResponse({
            "error": str(e),
            "trace": error_trace
        }, status_code=500)

@app.post("/evaluate_pitch")
async def evaluate_pitch(data: PitchEvaluation):
    """
    Evaluate with EnhancedEvaluator -> returns evaluation + logs
    """
    try:
        out_buf = io.StringIO()
        orig_stdout = sys.stdout
        sys.stdout = out_buf

        evaluator = EnhancedEvaluator(OPENAI_API_KEY)
        from judges.judges import EVALUATION_RUBRIC
        rub_keys = list(EVALUATION_RUBRIC.keys())

        eval_results = await evaluator.evaluate_project(data.transcript, rub_keys)

        sys.stdout = orig_stdout
        captured = out_buf.getvalue()
        out_buf.close()

        return JSONResponse({
            "success": True,
            "evaluation_results": eval_results,
            "captured_output": captured,
            "input_data": {
                "wpm": data.wpm,
                "time": data.time,
                "emotions": data.emotions
            }
        })
    except Exception as e:
        sys.stdout = orig_stdout
        if 'out_buf' in locals():
            out_buf.close()
        return JSONResponse(
            status_code=500,
            content={
                "success":False,
                "error":str(e),
                "error_type":type(e).__name__
            }
        )

# ------------------------------------------------
# MAIN DEBUG
# ------------------------------------------------
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


# --- ADDED CODE BELOW (TTS STREAMING SETUP FOR JUDGES) ---
import pyaudio
from elevenlabs import ElevenLabs, play

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in .env file.")

elevenlabs_streaming_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

judge_voices = {
   "RBC Judge": "21m00Tcm4TlvDq8ikWAM",
   "Google Judge": "TxGEqnHWrfWFTfGW9XjX",
   "1Password Judge": "VR6AewLTigWG4xSOukaG"
}

async def generate_and_play_audio_streaming(text: str, voice_id: str):
    """
    Uses ElevenLabs streaming TTS to play audio in real-time.
    """
    try:
        audio_stream = elevenlabs_streaming_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_monolingual_v1",
            stream=True
        )
        for chunk in audio_stream:
            await asyncio.to_thread(play, chunk)
    except Exception as e:
        print(f"TTS Streaming Error: {e}")
