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
from judges.evaluation import EnhancedEvaluator
import os

# Import chatbot pieces
from voice.chatbot import (
    decide_personality,
    get_response,
    record_audio,
    transcribe_audio_async,
    PERSONALITY_NAMES,
    set_last_judge  # We'll use this to track the last judge
)
from langchain.schema import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class PitchEvaluation(BaseModel):
    transcript: str
    wpm: float
    time: str
    emotions: Dict[str, float]

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for security
    allow_methods=["*"],
    allow_headers=["*"]
)

# == EMOTION RECOGNITION GLOBALS ==
is_recording = False
video_capture = None
emotion_counts = defaultdict(int)
total_frames = 0
threshold = 5.0  # threshold for including emotions

# == CHATBOT / Q&A GLOBALS ==
chat_history = ChatMessageHistory()
transcript_messages = []
chat_active = False
qna_mode = False

# Lock to prevent multiple Q&A loops
qna_lock = asyncio.Lock()

# Pitch capture event to ensure Q&A doesn't start prematurely
pitch_captured_event = asyncio.Event()

# WebSockets that receive transcript updates
transcript_websockets = []

@app.websocket("/ws")
async def webcam_feed(websocket: WebSocket):
    """
    Streams webcam feed + emotion detection over WebSocket.
    """
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
                    emotion_counts[dom_emotion] += 1
                    total_frames += 1

                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
                    cv2.putText(frame, dom_emotion, (x,y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
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
        if total_frames > 0:
            save_emotion_data()

@app.websocket("/ws_transcript")
async def transcript_feed(websocket: WebSocket):
    """
    WebSocket for sending transcript messages to the frontend in real-time.
    """
    await websocket.accept()
    transcript_websockets.append(websocket)
    print("Transcript WebSocket connected.")

    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        transcript_websockets.remove(websocket)
        print("Transcript WebSocket disconnected.")

def save_emotion_data():
    """
    Saves aggregated emotion data to 'emotion_data.json'.
    """
    global total_frames, emotion_counts, threshold
    if total_frames > 0:
        percentages = {em: (cnt / total_frames)*100 for em,cnt in emotion_counts.items()}
        filtered = {k:v for k,v in percentages.items() if v >= threshold}
        sorted_emotions = dict(sorted(filtered.items(), key=lambda x:x[1], reverse=True))
        with open("emotion_data.json","w") as f:
            json.dump(sorted_emotions, f, indent=4)
        print("Saved emotion_data.json")

# ---------------------------
# ANALYSIS + TIMER ENDPOINTS
# ---------------------------
class TimerData(BaseModel):
    time_left: int
    transcript: list[dict[str, str]]

def calculate_time_spent(time_left: int) -> str:
    total = 300
    spent = total - time_left
    mm = spent // 60
    ss = spent % 60
    return f"{mm}:{str(ss).zfill(2)}"

def create_transcript_json(transcript_data, wpm, time_spent, emotion_data=None):
    txt = "\n".join([f"{x['speaker']}: {x['text']}" for x in transcript_data])
    data = {
        "transcript": txt,
        "wpm": wpm,
        "time": time_spent
    }
    if emotion_data:
        data["emotions"] = emotion_data

    try:
        with open("transcript_analysis.json","w") as f:
            json.dump(data, f, indent=4)
        print("Analysis saved to transcript_analysis.json")
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return None
    return data

@app.post("/generate_analysis")
async def generate_analysis(data: TimerData):
    """
    Summarize the entire transcript, WPM, timeSpent, plus optional emotion data.
    Then send pitch to /evaluate_pitch for further analysis.
    """
    try:
        time_spent = calculate_time_spent(data.time_left)
        wpm = 150.0  # fixed
        # read emotion data if present
        emotion_data = None
        try:
            with open("emotion_data.json","r") as f:
                emotion_data = json.load(f)
        except FileNotFoundError:
            print("No emotion data found")

        # local analysis
        result = create_transcript_json(data.transcript, wpm, time_spent, emotion_data)
        # build pitch eval
        combined_txt = "\n".join([f"{x['speaker']}: {x['text']}" for x in data.transcript])
        pitch_eval = PitchEvaluation(
            transcript=combined_txt,
            wpm=wpm,
            time=time_spent,
            emotions=emotion_data or {}
        )
        # send to /evaluate_pitch
        eval_url = "http://127.0.0.1:8000/evaluate_pitch"
        async with aiohttp.ClientSession() as session:
            async with session.post(eval_url, json=pitch_eval.dict()) as resp:
                evaluation_response = await resp.json()

        print("Pitch Evaluation Response:")
        print(json.dumps(evaluation_response, indent=4))

        if result:
            return JSONResponse({
                "analysis_result": result,
                "evaluation_response": evaluation_response
            })
        else:
            return JSONResponse(
                {"error":"Failed to generate analysis"},
                status_code=500
            )
    except Exception as e:
        return JSONResponse({"error":str(e)}, status_code=500)

# ---------------------------
# STOP / START
# ---------------------------
@app.get("/stop")
async def stop_all():
    global is_recording, chat_active, qna_mode
    is_recording = False
    chat_active = False
    qna_mode = False

    pitch_captured_event.set()  # unlock any waiting tasks
    return JSONResponse({"message":"Session stopped."})

@app.get("/start_chat")
async def start_chat(bg: BackgroundTasks):
    global chat_active, qna_mode, chat_history, transcript_messages
    chat_active = True
    qna_mode = False
    chat_history = ChatMessageHistory()
    transcript_messages = []

    pitch_captured_event.clear()
    bg.add_task(pitch_capture_task)
    return {"message":"Chat session started (capturing pitch)."}

async def pitch_capture_task():
    global chat_active, chat_history, transcript_messages
    if not chat_active:
        return
    audio_np = await asyncio.to_thread(record_audio,16000,220,100,2)
    pitch_text = await transcribe_audio_async(audio_np)
    pitch_text = pitch_text.strip()
    if pitch_text:
        chat_history.add_message(HumanMessage(content=pitch_text))
        transcript_messages.append(("User", pitch_text))
        await broadcast_transcript(("User",pitch_text))
    else:
        await broadcast_transcript(("System","No pitch captured."))
    pitch_captured_event.set()

# ---------------------------
# BEGIN Q&A
# ---------------------------
@app.get("/begin_qna")
async def begin_qna(bg: BackgroundTasks):
    global qna_mode
    if qna_lock.locked():
        return JSONResponse({"message":"Q&A session already active"}, status_code=400)
    qna_mode = True
    bg.add_task(qna_loop)
    return {"message":"Q&A mode started. Judge will speak first."}

async def qna_loop():
    global chat_active, qna_mode, chat_history, transcript_messages
    async with qna_lock:
        try:
            # wait for pitch
            await pitch_captured_event.wait()

            while chat_active and qna_mode:
                # If we only have 1 message => it's just user pitch => judge starts
                if len(chat_history.messages) == 1:
                    # decide personality
                    chosen = await decide_personality("Start Q&A")
                    route, target, msg = await get_response(
                        personality_name=chosen,
                        history=formatted_history(chat_history),
                        user_input="Start Q&A"
                    )
                    chat_history.add_message(AIMessage(content=msg))
                    transcript_messages.append((chosen,msg))
                    await broadcast_transcript((chosen,msg))

                    if route == 1 and target in PERSONALITY_NAMES:
                        route2, tgt2, msg2 = await get_response(
                            personality_name=target,
                            history=formatted_history(chat_history),
                            user_input=msg
                        )
                        chat_history.add_message(AIMessage(content=msg2))
                        transcript_messages.append((target,msg2))
                        await broadcast_transcript((target,msg2))

                # user speaks
                user_audio = await asyncio.to_thread(record_audio,16000,220,100,2)
                user_text = await transcribe_audio_async(user_audio)
                user_text = user_text.strip()
                if not user_text:
                    continue

                chat_history.add_message(HumanMessage(content=user_text))
                transcript_messages.append(("User",user_text))
                await broadcast_transcript(("User",user_text))

                # which personality?
                chosen_personality = None
                # if user references a specific name
                for p in PERSONALITY_NAMES:
                    if p.lower() in user_text.lower():
                        chosen_personality = p
                        break
                if not chosen_personality:
                    chosen_personality = await decide_personality(user_text)

                route, target, msg = await get_response(
                    personality_name=chosen_personality,
                    history=formatted_history(chat_history),
                    user_input=user_text
                )
                chat_history.add_message(AIMessage(content=msg))
                transcript_messages.append((chosen_personality,msg))
                await broadcast_transcript((chosen_personality,msg))

                if route == 1 and target in PERSONALITY_NAMES:
                    route2, tgt2, msg2 = await get_response(
                        personality_name=target,
                        history=formatted_history(chat_history),
                        user_input=msg
                    )
                    chat_history.add_message(AIMessage(content=msg2))
                    transcript_messages.append((target,msg2))
                    await broadcast_transcript((target,msg2))

        except Exception as e:
            print(f"Error in Q&A loop: {e}")
            await broadcast_transcript(("System","An error occurred during Q&A."))
        finally:
            qna_mode = False

# ---------------------------
# Utility: broadcast_transcript
# ---------------------------
async def broadcast_transcript(msg: tuple):
    data = {"speaker": msg[0], "text": msg[1]}
    remove = []
    for ws in transcript_websockets:
        try:
            await ws.send_json(data)
        except:
            remove.append(ws)
    for dead in remove:
        transcript_websockets.remove(dead)

def formatted_history(chat_history: ChatMessageHistory) -> str:
    txt = ""
    for m in chat_history.messages:
        if isinstance(m, HumanMessage):
            txt += f"User: {m.content}\n"
        else:
            txt += f"Assistant: {m.content}\n"
    return txt

# ---------------------------
# EVALUATE PITCH
# ---------------------------
@app.post("/evaluate_pitch")
async def evaluate_pitch(data: PitchEvaluation):
    """
    Evaluate pitch => returns results + captured logs
    """
    try:
        output_buffer = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_buffer

        evaluator = EnhancedEvaluator(OPENAI_API_KEY)
        from judges.judges import EVALUATION_RUBRIC
        rubric_categories = list(EVALUATION_RUBRIC.keys())

        evaluation_results = await evaluator.evaluate_project(data.transcript, rubric_categories)

        sys.stdout = original_stdout
        captured_output = output_buffer.getvalue()
        output_buffer.close()

        return JSONResponse({
            "success": True,
            "evaluation_results": evaluation_results,
            "captured_output": captured_output,
            "input_data": {
                "wpm": data.wpm,
                "time": data.time,
                "emotions": data.emotions
            }
        })

    except Exception as e:
        sys.stdout = original_stdout
        if 'output_buffer' in locals():
            output_buffer.close()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
