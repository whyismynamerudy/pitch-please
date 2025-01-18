import json
import os

def create_transcript_json(transcript_file, wpm, time, emotion_json=None):
    # Read the transcript file
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find transcript file at {transcript_file}")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    # Create the JSON data structure
    data = {
        "transcript": transcript_text,
        "wpm": float(wpm),
        "time": time
    }

    # Add emotion data if provided
    if emotion_json:
        try:
            # If emotion_json is a file path, load it
            if isinstance(emotion_json, str):
                if os.path.exists(emotion_json):
                    with open(emotion_json, 'r') as f:
                        emotion_data = json.load(f)
                    data["emotions"] = emotion_data
                else:
                    print(f"Warning: Emotion JSON file not found at {emotion_json}")
            # If emotion_json is already a dictionary
            elif isinstance(emotion_json, dict):
                data["emotions"] = emotion_json
            else:
                print("Warning: Invalid emotion_json format")
        except Exception as e:
            print(f"Error processing emotion data: {e}")

    # Save the combined JSON to a file
    output_filename = os.path.splitext(transcript_file)[0] + '_analysis.json'
    try:
        with open(output_filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"\nAnalysis saved to: {output_filename}")
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return None

    # Also print the JSON
    print("\nJSON Output:")
    print(json.dumps(data, indent=4))
    
    return data

def process_transcript(transcript_path, wpm, time, emotion_path=None):
    """Wrapper function to process transcript with optional emotion data"""
    return create_transcript_json(transcript_path, wpm, time, emotion_path)

if __name__ == "__main__":
    # Example usage
    transcript_file = "backend/rubric/transcripts/transcript-bad.txt"
    wpm = 150.5
    time = "2:30"
    
    print("Example 1: Basic transcript analysis")
    result1 = process_transcript(transcript_file, wpm, time)
    
    print("\nExample 2: Analysis with emotion data")
    result2 = process_transcript(
        transcript_file,
        wpm,
        time,
        "emotion_data.json"  
    )