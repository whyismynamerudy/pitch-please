# backend.py

import io
import sys
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

# Import chatbot components
from voice.chatbot import (
    decide_personality,
    get_response,
    record_audio,
    transcribe_audio_async,
    PERSONALITY_NAMES
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

# Enable CORS for all origins (adjust as needed for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# == EMOTION RECOGNITION ==
is_recording = False
video_capture = None
emotion_counts = defaultdict(int)
total_frames = 0
threshold = 5.0  # Percentage threshold to record emotion data

# == CHATBOT STATE ==
chat_history = ChatMessageHistory()
transcript_messages = []
chat_active = False      # Indicates if chat is active
qna_mode = False         # Indicates if Q&A mode is active

# == Q&A Lock to Prevent Multiple Q&A Loops ==
qna_lock = asyncio.Lock()

# == Pitch Capture Synchronization ==
pitch_captured_event = asyncio.Event()

# == WebSockets for transcript streaming ==
transcript_websockets = []

@app.websocket("/ws")
async def webcam_feed(websocket: WebSocket):
    """
    WebSocket endpoint for streaming webcam feed with emotion detection.
    """
    global is_recording, video_capture, emotion_counts, total_frames

    await websocket.accept()
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
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
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

            if len(faces) > 0:
                x, y, w, h = faces[0]
                roi = frame[y:y+h, x:x+w]
                try:
                    result = DeepFace.analyze(roi, actions=['emotion'], enforce_detection=False)
                    emotions = result[0]['emotion']
                    dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
                    emotion_counts[dominant_emotion] += 1
                    total_frames += 1

                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, dominant_emotion, (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                except Exception as e:
                    print(f"Emotion analysis error: {e}")

            _, buf = cv2.imencode(".jpg", frame)
            await websocket.send_bytes(buf.tobytes())
            await asyncio.sleep(0.03)  # Approximately 30 FPS

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
    WebSocket endpoint for streaming transcript messages to the frontend.
    """
    await websocket.accept()
    transcript_websockets.append(websocket)
    print("Transcript WebSocket connected.")

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        transcript_websockets.remove(websocket)
        print("Transcript WebSocket disconnected.")

def save_emotion_data():
    """
    Saves the aggregated emotion data to a JSON file.
    """
    global total_frames, emotion_counts, threshold
    if total_frames > 0:
        percentages = {em: (cnt / total_frames) * 100 for em, cnt in emotion_counts.items()}
        filtered = {em: pct for em, pct in percentages.items() if pct >= threshold}
        sorted_emotions = dict(sorted(filtered.items(), key=lambda x: x[1], reverse=True))
        with open("emotion_data.json", "w") as f:
            json.dump(sorted_emotions, f, indent=4)
        print("Saved emotion_data.json")

# ================================
# Chatbot Endpoints
# ================================
# Add this Pydantic model for request validation
class TimerData(BaseModel):
    time_left: int
    transcript: list[dict[str, str]]  # List of transcript entries with speaker and text

def calculate_time_spent(time_left: int) -> str:
    """
    Convert time left (in seconds) to time spent format (MM:SS)
    Total time is 5 minutes (300 seconds)
    """
    total_seconds = 300  # 5 minutes
    time_spent = total_seconds - time_left
    minutes = time_spent // 60
    seconds = time_spent % 60
    return f"{minutes}:{str(seconds).zfill(2)}"

def create_transcript_json(transcript_data: list, wpm: float, time_spent: str, emotion_data: dict = None) -> dict:
    """
    Create analysis JSON combining transcript, WPM, time spent, and emotion data
    """
    # Format transcript data into a single string
    transcript_text = "\n".join([f"{entry['speaker']}: {entry['text']}" for entry in transcript_data])
    
    data = {
        "transcript": transcript_text,
        "wpm": float(wpm),
        "time": time_spent
    }
    
    if emotion_data:
        data["emotions"] = emotion_data
    
    # Save to file
    try:
        with open("transcript_analysis.json", 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Analysis saved to: transcript_analysis.json")
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return None
        
    return data

@app.post("/generate_analysis")
async def generate_analysis(data: TimerData):
    """
    Generate pitch evaluation using:
    - Transcript from frontend
    - Emotions from emotion_data.json
    - Time spent calculated from frontend timer
    - Hardcoded WPM of 150
    """
    try:
        # Calculate time spent from time left
        time_spent = calculate_time_spent(data.time_left)
        
        # Hardcoded WPM
        wpm = 150.0

        # Read emotion data if it exists
        emotion_data = None
        try:
            with open("emotion_data.json", "r") as f:
                emotion_data = json.load(f)
        except FileNotFoundError:
            print("No emotion data found, proceeding with empty emotions.")

        # Format transcript into a single string
        transcript_text = "\n".join([f"{entry['speaker']}: {entry['text']}" for entry in data.transcript])

        # Create PitchEvaluation object
        pitch_evaluation = PitchEvaluation(
            transcript=transcript_text,
            wpm=wpm,
            time=time_spent,
            emotions=emotion_data or {}
        )

        # Evaluate the pitch
        evaluation_response = await evaluate_pitch(pitch_evaluation)

        # Print the evaluation results in the terminal
        print("Evaluation Response:", evaluation_response.json(indent=4))

        # Return the evaluation results to the frontend
        return evaluation_response

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

    
@app.get("/stop")
async def stop_all():
    """
    Endpoint to stop the chat session and emotion detection.
    """
    global is_recording, chat_active, qna_mode
    is_recording = False
    chat_active = False
    qna_mode = False

    # Set the event to unblock any waiting coroutines
    pitch_captured_event.set()

    return JSONResponse({"message": "Session stopped."})

@app.get("/start_chat")
async def start_chat(bg: BackgroundTasks):
    """
    Starts the chat session by:
    1. Clearing old transcript and chat history.
    2. Setting chat_active to True.
    3. Capturing the user's pitch before Q&A begins.
    """
    global chat_active, qna_mode
    chat_active = True
    qna_mode = False

    global chat_history, transcript_messages
    chat_history = ChatMessageHistory()
    transcript_messages = []

    # Reset the pitch captured event
    pitch_captured_event.clear()

    # Start capturing the pitch
    bg.add_task(pitch_capture_task)
    return {"message": "Chat session started (capturing pitch)."}

async def pitch_capture_task():
    """
    Captures the user's pitch and sends it to the frontend.
    """
    global chat_history, transcript_messages, chat_active
    if not chat_active:
        return

    # Capture the pitch with silence-based recording
    pitch_audio = await asyncio.to_thread(record_audio, rate=16000, chunk=220, silence_threshold=100, silence_duration=2)
    pitch_text = await transcribe_audio_async(pitch_audio)
    pitch_text = pitch_text.strip()

    if pitch_text:
        # Add pitch to chat history and transcript
        chat_history.add_message(HumanMessage(content=pitch_text))
        transcript_messages.append(("User", pitch_text))
        await broadcast_transcript(("User", pitch_text))
    else:
        # Inform frontend that no pitch was captured
        await broadcast_transcript(("System", "No pitch captured."))

    # Set the event to indicate that pitch has been captured
    pitch_captured_event.set()

@app.get("/begin_qna")
async def begin_qna(bg: BackgroundTasks):
    """
    Initiates the Q&A session by:
    1. Setting qna_mode to True.
    2. Starting the Q&A loop.
    """
    global qna_mode

    # Attempt to acquire the Q&A lock to prevent multiple loops
    if qna_lock.locked():
        return JSONResponse({"message": "Q&A session is already active."}, status_code=400)

    qna_mode = True
    bg.add_task(qna_loop)
    return {"message": "Q&A mode started. Judge will speak first."}

async def qna_loop():
    """
    Handles the Q&A session with strict turn-taking:
    User speaks first -> Judge responds -> User responds -> Judge responds -> Repeat.
    Ensures routing up to two personalities.
    """
    global chat_active, qna_mode, chat_history, transcript_messages

    async with qna_lock:
        try:
            # Wait until the pitch has been captured
            await pitch_captured_event.wait()

            while chat_active and qna_mode:
                # Determine if it's the first interaction after the pitch
                if len(chat_history.messages) == 1:  # Only pitch is present
                    # Decide which personality should speak first
                    chosen_personality = await decide_personality("Start Q&A")
                    print(f"[Q&A] Chosen Personality: {chosen_personality}")

                    # Get judge's response
                    route, target, message = await get_response(
                        personality_name=chosen_personality,
                        history=formatted_history(chat_history),
                        user_input="Start Q&A"
                    )

                    # Add judge's response to chat history and broadcast
                    chat_history.add_message(AIMessage(content=message))
                    transcript_messages.append((chosen_personality, message))
                    await broadcast_transcript((chosen_personality, message))

                    # Handle routing if Route=1
                    if route == 1 and target in PERSONALITY_NAMES:
                        # Get response from the target personality
                        route2, target2, message2 = await get_response(
                            personality_name=target,
                            history=formatted_history(chat_history),
                            user_input=message
                        )

                        # Add the second judge's response to chat history and broadcast
                        chat_history.add_message(AIMessage(content=message2))
                        transcript_messages.append((target, message2))
                        await broadcast_transcript((target, message2))

                # Wait for user to respond (2 seconds of silence)
                user_audio = await asyncio.to_thread(record_audio, rate=16000, chunk=220, silence_threshold=100, silence_duration=2)
                user_text = await transcribe_audio_async(user_audio)
                user_text = user_text.strip()

                if not user_text:
                    continue  # Ignore empty inputs

                # Add user message to chat history and broadcast
                chat_history.add_message(HumanMessage(content=user_text))
                transcript_messages.append(("User", user_text))
                await broadcast_transcript(("User", user_text))

                # Decide which personality should respond based on user input
                chosen_personality = None
                for p in PERSONALITY_NAMES:
                    if p.lower() in user_text.lower():
                        chosen_personality = p
                        break

                if not chosen_personality:
                    chosen_personality = await decide_personality(user_text)

                print(f"[Q&A] Chosen Personality: {chosen_personality}")

                # Get judge's response
                route, target, message = await get_response(
                    personality_name=chosen_personality,
                    history=formatted_history(chat_history),
                    user_input=user_text
                )

                # Add judge's response to chat history and broadcast
                chat_history.add_message(AIMessage(content=message))
                transcript_messages.append((chosen_personality, message))
                await broadcast_transcript((chosen_personality, message))

                # Handle routing if Route=1 (up to two personalities)
                if route == 1 and target in PERSONALITY_NAMES:
                    # Get response from the target personality
                    route2, target2, message2 = await get_response(
                        personality_name=target,
                        history=formatted_history(chat_history),
                        user_input=message
                    )

                    # Add the second judge's response to chat history and broadcast
                    chat_history.add_message(AIMessage(content=message2))
                    transcript_messages.append((target, message2))
                    await broadcast_transcript((target, message2))

        except Exception as e:
            print(f"Error during Q&A loop: {e}")
            await broadcast_transcript(("System", "An error occurred during the Q&A session."))
        finally:
            qna_mode = False  # Reset Q&A mode upon completion

async def broadcast_transcript(msg: tuple):
    """
    Sends a single transcript message to all connected frontend WebSocket clients.
    """
    data = {"speaker": msg[0], "text": msg[1]}
    remove_list = []
    for ws in transcript_websockets:
        try:
            await ws.send_json(data)
        except:
            remove_list.append(ws)
    for ws in remove_list:
        transcript_websockets.remove(ws)

def formatted_history(chat_history: ChatMessageHistory) -> str:
    """
    Formats the chat history into a string suitable for the LLM.
    """
    history_str = ""
    for message in chat_history.messages:
        if isinstance(message, HumanMessage):
            history_str += f"User: {message.content}\n"
        elif isinstance(message, AIMessage):
            history_str += f"Assistant: {message.content}\n"
    return history_str



# @app.post("/evaluate_pitch")
async def evaluate_pitch(data: PitchEvaluation):
    """
    Evaluates a pitch using AI judges and returns both results and captured output.
    """
    try:
        # Create a string buffer to capture output
        output_buffer = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_buffer

        # Initialize evaluator
        evaluator = EnhancedEvaluator(OPENAI_API_KEY)
        
        # Get rubric categories from the hardcoded rubric
        from judges.judges import EVALUATION_RUBRIC
        rubric_categories = list(EVALUATION_RUBRIC.keys())
        
        # Run evaluation
        evaluation_results = await evaluator.evaluate_project(data.transcript, rubric_categories)
        
        # Restore original stdout and get captured output
        sys.stdout = original_stdout
        captured_output = output_buffer.getvalue()
        output_buffer.close()
        
        # Return both results and captured output
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
        # Restore stdout in case of error
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
