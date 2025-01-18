import json
import os

def create_transcript_json(transcript_file, wpm, time):
    # Read the transcript file
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find transcript file at {transcript_file}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Create the JSON data structure
    data = {
        "transcript": transcript_text,
        "wpm": float(wpm),
        "time": time
    }

    # Print the JSON
    print(json.dumps(data, indent=4))

# Example usage
if __name__ == "__main__":
    transcript_file = "backend/rubric/transcripts/transcript-bad.txt"
    wpm = 150.5
    time = "2:30"
    
    create_transcript_json(transcript_file, wpm, time)