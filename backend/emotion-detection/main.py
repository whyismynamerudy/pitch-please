import cv2
from deepface import DeepFace

def run_emotion_detection():
    previous_emotion = None

    # Load face cascade classifier
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Start capturing video from the webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Unable to access the webcam.")
        return

    print("Press 'q' to exit the application.")

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
            # If a face is detected, use the first detected face for analysis
            x, y, w, h = faces[0]

            # Extract the face region of interest (ROI)
            face_roi = frame[y:y + h, x:x + w]

            try:
                # Perform emotion analysis on the face ROI
                result = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)

                # Get the dominant emotion
                dominant_emotion = max(result[0]['emotion'], key=result[0]['emotion'].get)

                # Print the dominant emotion only if it changes
                if dominant_emotion != previous_emotion:
                    previous_emotion = dominant_emotion
                    print(f"Detected Emotion: {dominant_emotion}")

                # Draw a rectangle around the detected face
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{dominant_emotion}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            except Exception as e:
                print(f"Error during emotion analysis: {e}")
        else:
            # If no face is detected
            if previous_emotion != "No Face Detected":
                previous_emotion = "No Face Detected"
                print("No Face Detected")

        # Display the frame with annotations
        cv2.imshow('Real-time Emotion Detection', frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture object and close all OpenCV windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_emotion_detection()
