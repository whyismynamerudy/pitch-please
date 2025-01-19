# backend.py
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
from deepface import DeepFace
from collections import defaultdict
import json
import asyncio
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
# Add this updated Pydantic model for request validation
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

# Modified endpoint with proper request body handling
@app.post("/generate_analysis")
async def generate_analysis(data: TimerData):
    """
    Generate analysis JSON using:
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
        
        # Read emotion data if exists
        emotion_data = None
        try:
            with open("emotion_data.json", "r") as f:
                emotion_data = json.load(f)
        except FileNotFoundError:
            print("No emotion data found")
        
        # Generate analysis
        result = create_transcript_json(
            transcript_data=data.transcript,
            wpm=wpm,
            time_spent=time_spent,
            emotion_data=emotion_data
        )
        
        if result:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                content={"error": "Failed to generate analysis"},
                status_code=500
            )
            
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
    Judge speaks first -> User responds -> Judge responds -> Repeat.
    Ensures routing up to two personalities.
    """
    global chat_active, qna_mode, chat_history, transcript_messages

    async with qna_lock:
        try:
            while chat_active and qna_mode:
                # Get current chat history length to check if it's the first interaction
                current_history_len = len(chat_history.messages)

                # Judge speaks first, either at start or after user response
                chosen_personality = None
                
                if current_history_len == 1:  # Only pitch is present - first judge interaction
                    # Initial judge selection for Q&A start
                    chosen_personality = await decide_personality("Start Q&A")
                else:
                    # Get the last user message for context
                    last_user_msg = ""
                    for msg in reversed(chat_history.messages):
                        if isinstance(msg, HumanMessage):
                            last_user_msg = msg.content
                            break
                    # Decide which personality should respond
                    for p in PERSONALITY_NAMES:
                        if p.lower() in last_user_msg.lower():
                            chosen_personality = p
                            break
                    if not chosen_personality:
                        chosen_personality = await decide_personality(last_user_msg)

                print(f"[Q&A] Chosen Personality: {chosen_personality}")

                # Get judge's response
                route, target, message = await get_response(
                    personality_name=chosen_personality,
                    history=formatted_history(chat_history),
                    user_input="Start Q&A" if current_history_len == 1 else last_user_msg
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

                # Now wait for user response
                user_audio = await asyncio.to_thread(record_audio, rate=16000, chunk=220, silence_threshold=100, silence_duration=2)
                user_text = await transcribe_audio_async(user_audio)
                user_text = user_text.strip()

                if not user_text:
                    continue  # Ignore empty inputs

                # Add user message to chat history and broadcast
                chat_history.add_message(HumanMessage(content=user_text))
                transcript_messages.append(("User", user_text))
                await broadcast_transcript(("User", user_text))

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
