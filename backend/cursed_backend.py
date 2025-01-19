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
    Record a chunk as the pitch, place it in chat_history.
    """
    global chat_active, chat_history, transcript_messages
    if not chat_active:
        return

    pitch_audio = await asyncio.to_thread(record_audio, 16000,220,100,2)
    pitch_text = await transcribe_audio_async(pitch_audio)
    pitch_text = pitch_text.strip()
    if pitch_text:
        chat_history.add_message(HumanMessage(content=pitch_text))
        transcript_messages.append(("User", pitch_text))
        await broadcast_transcript(("User", pitch_text))
    else:
        await broadcast_transcript(("System","No pitch captured."))

    pitch_captured_event.set()

# ------------------------------------------------
# Q&A
# ------------------------------------------------
@app.get("/begin_qna")
async def begin_qna(bg: BackgroundTasks):
    """
    Start Q&A once pitch is captured.
    """
    global qna_mode
    if qna_lock.locked():
        return JSONResponse({"message":"Q&A session already active"}, status_code=400)

    qna_mode = True
    bg.add_task(qna_loop)
    return {"message":"Q&A mode started. Judges can respond."}

async def qna_loop():
    """
    Multi-route Q&A:
      user => judge => possible route => user => judge => route ...
      up to 2 times per turn.
    """
    global chat_active, qna_mode, chat_history, transcript_messages
    async with qna_lock:
        try:
            # Wait for pitch
            await pitch_captured_event.wait()

            while chat_active and qna_mode:
                # If only 1 message => first Q
                if len(chat_history.messages) == 1:
                    # Decide which judge starts
                    init_judge = await decide_personality("Start Q&A - please choose a diverse judge.")
                    r1, t1, msg1 = await get_response(
                        personality_name=init_judge,
                        history=formatted_history(chat_history),
                        user_input="Start Q&A"
                    )
                    chat_history.add_message(AIMessage(content=msg1))
                    transcript_messages.append((init_judge, msg1))
                    await broadcast_transcript((init_judge, msg1))

                    # If route=1 => pass once
                    if r1 == 1 and t1 in PERSONALITY_NAMES:
                        r2, t2, msg2 = await get_response(
                            personality_name=t1,
                            history=formatted_history(chat_history),
                            user_input=msg1
                        )
                        chat_history.add_message(AIMessage(content=msg2))
                        transcript_messages.append((t1, msg2))
                        await broadcast_transcript((t1, msg2))

                # user speaks
                user_audio = await asyncio.to_thread(record_audio,16000,220,100,2)
                user_text = await transcribe_audio_async(user_audio)
                user_text = user_text.strip()
                if not user_text:
                    continue

                chat_history.add_message(HumanMessage(content=user_text))
                transcript_messages.append(("User", user_text))
                await broadcast_transcript(("User", user_text))

                # see if they mention a personality by name
                chosen_p = None
                for p in PERSONALITY_NAMES:
                    if p.lower() in user_text.lower():
                        chosen_p = p
                        break
                if not chosen_p:
                    # decider chooses from the full conversation
                    chosen_p = await decide_personality(user_text + " Encourage a different judge if possible.")

                # get judge response
                r_main, t_main, msg_main = await get_response(
                    personality_name=chosen_p,
                    history=formatted_history(chat_history),
                    user_input=user_text
                )
                chat_history.add_message(AIMessage(content=msg_main))
                transcript_messages.append((chosen_p, msg_main))
                await broadcast_transcript((chosen_p, msg_main))

                # if route=1 => pass to another judge
                if r_main == 1 and t_main in PERSONALITY_NAMES:
                    r_alt, t_alt, msg_alt = await get_response(
                        personality_name=t_main,
                        history=formatted_history(chat_history),
                        user_input=msg_main
                    )
                    chat_history.add_message(AIMessage(content=msg_alt))
                    transcript_messages.append((t_main, msg_alt))
                    await broadcast_transcript((t_main, msg_alt))

        except Exception as e:
            print(f"Error in Q&A loop: {e}")
            await broadcast_transcript(("System","An error occurred during Q&A."))
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
    Transform chat_history into a user/assistant conversation string.
    """
    out = ""
    for m in chat_history.messages:
        if isinstance(m, HumanMessage):
            out += f"User: {m.content}\n"
        else:
            out += f"Assistant: {m.content}\n"
    return out

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
        # time
        t_spent = calculate_time_spent(data.time_left)
        wpm=150.0
        # read emotion
        emotion_data=None
        try:
            with open("emotion_data.json","r") as f:
                emotion_data=json.load(f)
        except FileNotFoundError:
            print("No emotion data found.")

        res = create_transcript_json(data.transcript, wpm, t_spent, emotion_data)
        # build pitch eval
        combined = "\n".join([f"{x['speaker']}: {x['text']}" for x in data.transcript])
        pitch_eval = PitchEvaluation(
            transcript=combined,
            wpm=wpm,
            time=t_spent,
            emotions=emotion_data or {}
        )
        # call evaluate
        url="http://127.0.0.1:8000/evaluate_pitch"
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=pitch_eval.dict()) as resp:
                eval_res = await resp.json()

        print("Pitch Evaluation Response:")
        print(json.dumps(eval_res, indent=4))

        if res:
            return JSONResponse({
                "analysis_result": res,
                "evaluation_response": eval_res
            })
        else:
            return JSONResponse({
                "error":"Failed to generate analysis"
            }, status_code=500)

    except Exception as e:
        return JSONResponse({"error":str(e)}, status_code=500)

@app.post("/evaluate_pitch")
async def evaluate_pitch(data: PitchEvaluation):
    """
    Evaluate with EnhancedEvaluator -> returns evaluation + logs
    """
    try:
        out_buf=io.StringIO()
        orig_stdout=sys.stdout
        sys.stdout=out_buf

        evaluator=EnhancedEvaluator(OPENAI_API_KEY)
        from judges.judges import EVALUATION_RUBRIC
        rub_keys=list(EVALUATION_RUBRIC.keys())

        eval_results=await evaluator.evaluate_project(data.transcript,rub_keys)

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

# ------------------------------------------------
# MAIN DEBUG
# ------------------------------------------------
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
