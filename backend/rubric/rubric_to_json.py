from PIL import Image
import pytesseract
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import sys

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

gpt_prompt = """Your task is to interpret the following text and convert it into JSON format. The format should be as follows:
{
    "criterion 1": {
        "weight": 10,
        "description": "Description of Criterion 1"
    },
    "criterion 2": {
        "weight": 4,
        "description": "Description of Criterion 2"
    },
    ...
}

Each criterion will be marked from 1 to the maximum score specified. Note that each criterion should be a distinct category
from each of the other ones. If multiple criterion appear to be judging the same thing, please combine them into a single
criterion.
Do not output any additional information or explanations. Only raw JSON data should be returned.
"""

def rubric_to_json(filename):
    rubric_image = None
    # Read the rubric file
    try:
        rubric_image = Image.open(filename)
    except FileNotFoundError:
        print(f"Error: Could not find rubric file at {filename}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    text = pytesseract.image_to_string(rubric_image)

    print(f"got text from image: {text}")
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": gpt_prompt},
            {
                "role": "user",
                "content": text
            }
        ]
    ).choices[0].message.content

    # print(json.loads(response))

    return response

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rubric_to_json.py <rubric_image_path>")
        sys.exit(1)
    
    rubric_image = sys.argv[1]

    rubric_to_json(rubric_image)
