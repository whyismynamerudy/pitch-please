import cv2
from deepface import DeepFace
from collections import defaultdict
import json
import os
from grader.json_converter import create_transcript_json

def run_emotion_detection(threshold=5.0, transcript_file=None, wpm=None, time=None):
    previous_emotion = None
    emotion_counts = defaultdict(int)
    total_frames = 0
    saved_flag = False

    # Load face cascade classifier
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Start capturing video from the webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Unable to access the webcam.")
        return None

    print("Press 'q' to exit the application.")
    print("Press SPACEBAR to save current emotion data and exit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Unable to capture video frame.")
            break

        # Convert the frame to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces in the frame
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            x, y, w, h = faces[0]
            face_roi = frame[y:y + h, x:x + w]

            try:
                result = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)
                emotions = result[0]['emotion']
                dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
                emotion_counts[dominant_emotion] += 1
                total_frames += 1

                if dominant_emotion != previous_emotion:
                    previous_emotion = dominant_emotion
                    print(f"Detected Emotion: {dominant_emotion}")

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{dominant_emotion}", (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            except Exception as e:
                print(f"Error during emotion analysis: {e}")
        else:
            if previous_emotion != "No Face Detected":
                previous_emotion = "No Face Detected"
                print("No Face Detected")

        cv2.imshow('Real-time Emotion Detection', frame)

        # Check for key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == 32:  # Spacebar (using keycode 32 for cross-platform compatibility)
            # Calculate and save current emotions
            if total_frames > 0:
                emotion_percentages = {
                    emotion: (count / total_frames) * 100 
                    for emotion, count in emotion_counts.items()
                }
                
                filtered_emotions = {
                    emotion: percentage 
                    for emotion, percentage in emotion_percentages.items() 
                    if percentage >= threshold
                }
                
                sorted_emotions = dict(sorted(filtered_emotions.items(), 
                                            key=lambda x: x[1], 
                                            reverse=True))
                
                # Save to file
                with open('emotion_data.json', 'w') as f:
                    json.dump(sorted_emotions, f, indent=4)
                print("\nEmotion data saved to emotion_data.json")
                saved_flag = True

                # Call create_transcript_json if transcript_file, wpm, and time are provided
                if transcript_file and wpm and time:
                    create_transcript_json(transcript_file, wpm, time, 'emotion_data.json')

            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

    # Only return data if it wasn't already saved by spacebar
    if total_frames > 0 and not saved_flag:
        emotion_percentages = {
            emotion: (count / total_frames) * 100 
            for emotion, count in emotion_counts.items()
        }
        
        filtered_emotions = {
            emotion: percentage 
            for emotion, percentage in emotion_percentages.items() 
            if percentage >= threshold
        }
        
        sorted_emotions = dict(sorted(filtered_emotions.items(), 
                                    key=lambda x: x[1], 
                                    reverse=True))
        
        print("\nEmotion Summary (emotions >= {}%):".format(threshold))
        for emotion, percentage in sorted_emotions.items():
            print(f"{emotion}: {percentage:.1f}%")
            
        return sorted_emotions
    
    return None

if __name__ == "__main__":
    transcript_file = "backend/rubric/transcripts/transcript-bad.txt"
    wpm = 150.5
    time = "2:30"

    emotion_results = run_emotion_detection(threshold=5.0, transcript_file=transcript_file, wpm=wpm, time=time)
