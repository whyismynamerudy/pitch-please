import io
import sys
import aiohttp
import base64
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

import pyaudio
from pydub import AudioSegment
from elevenlabs import ElevenLabs, play

# ========== Import from chatbot pieces ==========
from judges.evaluation import EnhancedEvaluator
from voice.chatbot import (
    decide_personality,  
    get_response,        
    record_audio,        
    transcribe_audio_async,
    PERSONALITY_NAMES    
)
from langchain.schema import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from voice.personalities import PERSONALITIES

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file.")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in .env file.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"]
)

# -------------------------------
# EMOTION DETECTION GLOBALS
# -------------------------------
is_recording = False
video_capture = None
emotion_counts = defaultdict(int)
total_frames = 0
threshold = 5.0

# -------------------------------
# CHAT / Q&A
# -------------------------------
chat_history = ChatMessageHistory()
transcript_messages = []
chat_active = False
qna_mode = False
qna_lock = asyncio.Lock()
pitch_captured_event = asyncio.Event()

transcript_websockets = []

# Convert personalities list → dict for easy lookup
personalities_dict = {p["name"]: p for p in PERSONALITIES}

# Example voice ID mapping
judge_voices = {
    "RBC Judge": "21m00Tcm4TlvDq8ikWAM",
    "Google Judge": "TxGEqnHWrfWFTfGW9XjX",
    "1Password Judge": "VR6AewLTigWG4xSOukaG"
}

# ElevenLabs streaming client
elevenlabs_streaming_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# -------------------------------
# FORCE AUDIO STOP FLAG
# -------------------------------
force_audio_stop = False

# -------------------------------
# HELPER: Play TTS in memory
# -------------------------------
def play_audio_in_memory(mp3_data: bytes):
    segment = AudioSegment.from_file(io.BytesIO(mp3_data), format="mp3")
    p = pyaudio.PyAudio()
    stream = p.open(
        format=p.get_format_from_width(segment.sample_width),
        channels=segment.channels,
        rate=segment.frame_rate,
        output=True
    )
    stream.write(segment.raw_data)
    stream.stop_stream()
    stream.close()
    p.terminate()

async def generate_and_play_audio_streaming(text: str, voice_id: str):
    """
    Uses ElevenLabs streaming TTS to play audio in real-time
    *without* blocking transcript updates.
    This checks force_audio_stop to immediately break if /stop was called.
    """
    global force_audio_stop
    try:
        audio_stream = elevenlabs_streaming_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_monolingual_v1",
            stream=True
        )
        for chunk in audio_stream:
            # If forced stop, break immediately (no further audio).
            if force_audio_stop:
                break
            await asyncio.to_thread(play, chunk)
    except Exception as e:
        if not force_audio_stop:  # Only log if it's not due to forced stop
            print(f"TTS Streaming Error: {e}")

# -------------------------------
# WEBCAM / EMOTION
# -------------------------------
@app.websocket("/ws")
async def webcam_feed(websocket: WebSocket):
    global is_recording, video_capture, emotion_counts, total_frames
    await websocket.accept()

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
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

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30,30))
            if len(faces) > 0:
                x, y, w, h = faces[0]
                roi = frame[y:y+h, x:x+w]
                try:
                    result = DeepFace.analyze(roi, actions=["emotion"], enforce_detection=False)
                    dom_emotion = max(result[0]["emotion"].items(), key=lambda x: x[1])[0]
                    emotion_counts[dom_emotion]+=1
                    total_frames+=1

                    cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0),2)
                    cv2.putText(frame, dom_emotion, (x,y-10),
                                cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,0),2)
                except Exception as e:
                    print(f"Emotion analysis error: {e}")

            _, buf = cv2.imencode(".jpg", frame)
            await websocket.send_bytes(buf.tobytes())
            await asyncio.sleep(0.03)

    except WebSocketDisconnect:
        print("Video WebSocket disconnected.")
    finally:
        video_capture.release()
        cv2.destroyAllWindows()
        if total_frames>0:
            save_emotion_data()

@app.websocket("/ws_transcript")
async def transcript_feed(websocket: WebSocket):
    await websocket.accept()
    transcript_websockets.append(websocket)
    print("Transcript WebSocket connected.")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        transcript_websockets.remove(websocket)
        print("Transcript WebSocket disconnected.")

def save_emotion_data():
    global total_frames, emotion_counts, threshold
    if total_frames>0:
        perc = {k:(v/total_frames*100) for k,v in emotion_counts.items()}
        fil = {k:v for k,v in perc.items() if v>=threshold}
        sorted_e = dict(sorted(fil.items(), key=lambda x:x[1], reverse=True))
        with open("emotion_data.json","w") as f:
            json.dump(sorted_e,f,indent=4)
        print("Saved emotion_data.json")

# -------------------------------
# STOP
# -------------------------------
@app.get("/stop")
async def stop_all():
    """
    Called when the user clicks Stop. Immediately halts:
    - Audio playback (through force_audio_stop)
    - Q&A loops (chat_active / qna_mode = False)
    - Webcam feed
    """
    global is_recording, chat_active, qna_mode, force_audio_stop
    force_audio_stop = True      # Stop ongoing TTS
    is_recording = False
    chat_active = False
    qna_mode = False
    pitch_captured_event.set()

    return JSONResponse({"message":"Session stopped."})

# -------------------------------
# START CHAT
# -------------------------------
@app.get("/start_chat")
async def start_chat(bg: BackgroundTasks):
    global chat_active, qna_mode, chat_history, transcript_messages, force_audio_stop
    chat_active = True
    qna_mode = False
    chat_history = ChatMessageHistory()
    transcript_messages = []

    # Reset the forced stop so new TTS can happen
    force_audio_stop = False

    pitch_captured_event.clear()
    bg.add_task(pitch_capture_task)
    return {"message":"Chat session started (capturing pitch)."}

async def pitch_capture_task():
    global chat_active, chat_history, transcript_messages
    if not chat_active:
        return

    pitch_audio = await asyncio.to_thread(record_audio,16000,220,100,2)
    pitch_text = await transcribe_audio_async(pitch_audio)
    pitch_text = pitch_text.strip()

    if pitch_text:
        chat_history.add_message(HumanMessage(content=pitch_text))
        transcript_messages.append(("User (Pitch)", pitch_text))
        await broadcast_transcript(("User (Pitch)", pitch_text))
    else:
        await broadcast_transcript(("System","No pitch captured."))

    pitch_captured_event.set()

# -------------------------------
# Q&A
# -------------------------------
@app.get("/begin_qna")
async def begin_qna(bg: BackgroundTasks):
    global qna_mode
    if qna_lock.locked():
        return JSONResponse({"message":"Q&A session already active"}, status_code=400)

    qna_mode = True
    bg.add_task(qna_loop)
    return {"message":"Q&A mode started. Judges can respond."}

async def qna_loop():
    global chat_active, qna_mode, chat_history, transcript_messages, force_audio_stop
    async with qna_lock:
        try:
            await pitch_captured_event.wait()

            while chat_active and qna_mode:
                # If only pitch is present => first judge
                if len(chat_history.messages) == 1:
                    initial_judge = await decide_personality("Start Q&A based on the pitch.")
                    route, target, message = await get_response(
                        personality_name=initial_judge,
                        history=formatted_history(chat_history),
                        user_input="Start Q&A"
                    )
                    chat_history.add_message(AIMessage(content=message))
                    transcript_messages.append((initial_judge, message))
                    # 1) Broadcast text
                    await broadcast_transcript((initial_judge, message))
                    # 2) If we want TTS, do it concurrently
                    if initial_judge in judge_voices and not force_audio_stop:
                        asyncio.create_task(generate_and_play_audio_streaming(message, judge_voices[initial_judge]))

                    # If route=1 => pass
                    if route == 1 and target in PERSONALITY_NAMES:
                        r2, t2, msg2 = await get_response(
                            personality_name=target,
                            history=formatted_history(chat_history),
                            user_input=message
                        )
                        chat_history.add_message(AIMessage(content=msg2))
                        transcript_messages.append((target, msg2))
                        await broadcast_transcript((target, msg2))
                        if target in judge_voices and not force_audio_stop:
                            asyncio.create_task(generate_and_play_audio_streaming(msg2, judge_voices[target]))

                user_audio = await asyncio.to_thread(record_audio,16000,220,100,2)
                user_text = await transcribe_audio_async(user_audio)
                user_text = user_text.strip()
                if not user_text:
                    continue

                chat_history.add_message(HumanMessage(content=user_text))
                transcript_messages.append(("User", user_text))
                await broadcast_transcript(("User", user_text))
                # User => no TTS for user

                chosen_judge = None
                for p in PERSONALITY_NAMES:
                    if p.lower() in user_text.lower():
                        chosen_judge = p
                        break
                if not chosen_judge:
                    chosen_judge = await decide_personality(user_text)

                route, target, message = await get_response(
                    personality_name=chosen_judge,
                    history=formatted_history(chat_history),
                    user_input=user_text
                )
                chat_history.add_message(AIMessage(content=message))
                transcript_messages.append((chosen_judge, message))
                # 1) broadcast text first
                await broadcast_transcript((chosen_judge, message))
                # 2) TTS concurrently
                if chosen_judge in judge_voices and not force_audio_stop:
                    asyncio.create_task(generate_and_play_audio_streaming(message, judge_voices[chosen_judge]))

                if route == 1 and target in PERSONALITY_NAMES:
                    r2, t2, msg2 = await get_response(
                        personality_name=target,
                        history=formatted_history(chat_history),
                        user_input=message
                    )
                    chat_history.add_message(AIMessage(content=msg2))
                    transcript_messages.append((target, msg2))
                    await broadcast_transcript((target, msg2))
                    if target in judge_voices and not force_audio_stop:
                        asyncio.create_task(generate_and_play_audio_streaming(msg2, judge_voices[target]))

        except Exception as e:
            print(f"Error in Q&A loop: {e}")
            await broadcast_transcript(("System","An error occurred during Q&A."))
        finally:
            qna_mode = False

# -------------------------------
# broadcast_transcript
# -------------------------------
async def broadcast_transcript(msg: tuple):
    # Just send the text out *immediately*
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
    out = ""
    for i, m in enumerate(chat_history.messages):
        if i==0:
            out += f"User (Pitch): {m.content}\n"
        elif isinstance(m, HumanMessage):
            out += f"User: {m.content}\n"
        else:
            out += f"Assistant: {m.content}\n"
    return out

# ------------------------------------------------
# Transcript + Pitch Evaluate
# ------------------------------------------------
class TimerData(BaseModel):
    time_left: int
    transcript: list[dict[str, str]]

def calculate_time_spent(time_left: int) -> str:
    total = 300
    spent = total - time_left
    mm = spent//60
    ss = spent%60
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
    try:
        t_spent = calculate_time_spent(data.time_left)
        # example: compute real WPM
        total_words = sum(len(m["text"].split()) for m in data.transcript)
        time_in_minutes = (300 - data.time_left)/60
        wpm = (total_words/time_in_minutes) if time_in_minutes>0 else 0

        emotion_data = None
        try:
            with open("emotion_data.json","r") as f:
                emotion_data = json.load(f)
        except:
            print("No valid emotion_data.json found.")

        res = create_transcript_json(data.transcript, wpm, t_spent, emotion_data)
        if not res:
            return JSONResponse({"error":"Failed creating transcript JSON"}, status_code=500)

        combined = "\n".join([f"{x['speaker']}: {x['text']}" for x in data.transcript])
        pitch_eval = PitchEvaluation(
            transcript=combined,
            wpm=wpm,
            time=t_spent,
            emotions=emotion_data or {}
        )

        # Evaluate pitch
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post("http://127.0.0.1:8000/evaluate_pitch",
                                     json=pitch_eval.dict()) as resp:
                    if resp.status != 200:
                        errtxt = await resp.text()
                        return JSONResponse({"error":f"Eval failed {resp.status}: {errtxt}"}, status_code=500)
                    eval_res = await resp.json()
        except aiohttp.ClientError as e:
            return JSONResponse({"error":f"Evaluation service unreachable: {str(e)}"}, status_code=500)

        return JSONResponse({
            "analysis_result":res,
            "evaluation_response":eval_res
        })
    except Exception as e:
        return JSONResponse({"error":str(e)},status_code=500)


class PitchEvaluation(BaseModel):
    transcript: str
    wpm: float
    time: str
    emotions: Dict[str, float]

@app.post("/evaluate_pitch")
async def evaluate_pitch(data: PitchEvaluation):
    orig_stdout = sys.stdout
    try:
        out_buf = io.StringIO()
        sys.stdout=out_buf

        evaluator = EnhancedEvaluator(OPENAI_API_KEY)
        from judges.judges import EVALUATION_RUBRIC
        rub_keys = list(EVALUATION_RUBRIC.keys())

        eval_results = await evaluator.evaluate_project(data.transcript, rub_keys)

        sys.stdout=orig_stdout
        captured=out_buf.getvalue()
        out_buf.close()

        return JSONResponse({
            "success":True,
            "evaluation_results":eval_results,
            "captured_output":captured,
            "input_data":{
                "wpm":data.wpm,
                "time":data.time,
                "emotions":data.emotions
            }
        })
    except Exception as e:
        sys.stdout=orig_stdout
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

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
