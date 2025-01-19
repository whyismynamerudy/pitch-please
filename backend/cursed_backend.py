# backend.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
from deepface import DeepFace
from collections import defaultdict
import json
import asyncio

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# == EMOTION FEED ==
is_recording = False
video_capture = None
emotion_counts = defaultdict(int)
total_frames = 0
threshold = 5.0

# == CHATBOT GLOBALS ==
chat_history = ChatMessageHistory()
transcript_messages = []
chat_active = False     # True after /start_chat
qna_mode = False        # True after /begin_qna

@app.websocket("/ws")
async def webcam_feed(websocket: WebSocket):
    global is_recording, video_capture, emotion_counts, total_frames

    await websocket.accept()
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        await websocket.send_json({"error": "Unable to access webcam"})
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
                x,y,w,h = faces[0]
                roi = frame[y:y+h, x:x+w]
                try:
                    result = DeepFace.analyze(roi, actions=['emotion'], enforce_detection=False)
                    dom = max(result[0]['emotion'].items(), key=lambda x:x[1])[0]
                    emotion_counts[dom]+=1
                    total_frames+=1

                    cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
                    cv2.putText(frame,dom,(x,y-10),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,0),2)
                except Exception as e:
                    print("Emotion analysis error:", e)

            _, buf = cv2.imencode('.jpg', frame)
            await websocket.send_bytes(buf.tobytes())
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        print("Video feed disconnected.")
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
            await websocket.receive_text() # keep alive
    except WebSocketDisconnect:
        transcript_websockets.remove(websocket)
        print("Transcript WebSocket disconnected.")

def save_emotion_data():
    global total_frames, emotion_counts, threshold
    if total_frames>0:
        perc = {k:(v/total_frames*100) for k,v in emotion_counts.items()}
        filtered = {k:v for k,v in perc.items() if v>=threshold}
        sorted_e = dict(sorted(filtered.items(), key=lambda x:x[1], reverse=True))
        with open("emotion_data.json","w") as f:
            json.dump(sorted_e, f, indent=4)
        print("Saved emotion_data.json")

transcript_websockets=[]

@app.get("/stop")
def stop_all():
    """
    Called by "Stop" => ends chat & video feed
    """
    global is_recording, chat_active
    is_recording = False
    chat_active = False
    return JSONResponse({"message":"Session stopped."})

@app.get("/start_chat")
def start_chat(bg: BackgroundTasks):
    """
    1) Clears old transcript & history
    2) chat_active=True
    3) Immediately capture one chunk of pitch => store in transcript
    4) Then idle until /begin_qna is called
    """
    global chat_active, qna_mode
    chat_active = True
    qna_mode = False

    global chat_history, transcript_messages
    chat_history = ChatMessageHistory()
    transcript_messages=[]
    
    bg.add_task(pitch_capture_task)
    return {"message":"Chat session started (capturing pitch)."}

async def pitch_capture_task():
    """
    Runs once in background right after start_chat
    -> Captures pitch chunk with record_audio, transcribes, stores in transcript
    """
    global chat_history, transcript_messages, chat_active
    if not chat_active:
        return
    # 1) capture user chunk
    pitch_audio = await asyncio.to_thread(record_audio,16000,220,100,2)
    pitch_text = await transcribe_audio_async(pitch_audio)
    pitch_text = pitch_text.strip()
    if pitch_text:
        chat_history.add_message(HumanMessage(content=pitch_text))
        transcript_messages.append(("User", pitch_text))
        await broadcast_transcript(("User", pitch_text))
    else:
        await broadcast_transcript(("System","No pitch captured."))

@app.get("/begin_qna")
def begin_qna(bg: BackgroundTasks):
    """
    Once pitch is captured, user clicks "Begin Q&A" => indefinite user->judge
    loop until Stop is called.
    """
    global qna_mode
    qna_mode=True
    bg.add_task(qna_loop)
    return {"message":"Q&A mode started. Wait for user speech => 2s silence => judge => possibly route."}

async def qna_loop():
    """
    Indefinite user->judge loop, 2s silence for user speech.
    After each user chunk => up to 2 route passes among judges.
    Ends when chat_active=False
    """
    global chat_active, qna_mode, chat_history, transcript_messages

    while chat_active and qna_mode:
        # 1) Wait for user chunk
        audio_np = await asyncio.to_thread(record_audio,16000,220,100,2)
        user_text = await transcribe_audio_async(audio_np)
        user_text = user_text.strip()
        if not user_text:
            continue

        # Show user text
        chat_history.add_message(HumanMessage(content=user_text))
        transcript_messages.append(("User", user_text))
        await broadcast_transcript(("User", user_text))

        # Build history string
        formatted_history = ""
        for m in chat_history.messages:
            if isinstance(m, HumanMessage):
                formatted_history += f"User: {m.content}\n"
            else:
                formatted_history += f"Assistant: {m.content}\n"

        # 2) Decide which personality
        chosen_personality=None
        for p in PERSONALITY_NAMES:
            if p.lower() in user_text.lower():
                chosen_personality=p
                break
        if not chosen_personality:
            chosen_personality = await decide_personality(user_text)

        current_personality=chosen_personality
        current_input=user_text
        max_routes=2
        routing_count=0

        while routing_count<max_routes:
            routing_count+=1
            route, target, message = await get_response(
                personality_name=current_personality,
                history=formatted_history,
                user_input=current_input
            )
            chat_history.add_message(AIMessage(content=message))
            transcript_messages.append((current_personality,message))
            await broadcast_transcript((current_personality,message))

            if route==2:
                # done => speak to user
                break
            else:
                # route=1 => speak to another judge
                if target not in PERSONALITY_NAMES:
                    break
                # pass message => new personality
                current_personality=target
                current_input=message
                # loop continues one more pass
    print("Q&A loop ended or chat stopped.")

async def broadcast_transcript(msg: tuple):
    """
    Send one message to all /ws_transcript clients
    """
    data={"speaker":msg[0],"text":msg[1]}
    remove=[]
    for ws in transcript_websockets:
        try:
            await ws.send_json(data)
        except:
            remove.append(ws)
    for dead in remove:
        transcript_websockets.remove(dead)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
