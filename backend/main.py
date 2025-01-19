from fastapi import FastAPI, UploadFile
from rubric.rubric_to_json import rubric_to_json
from voice.chatbot import chat_loop
import json
from judges.evaluation import EnhancedEvaluator
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# upload rubric and sponsor list
@app.post("/upload_info", status_code=201)
async def upload_info(rubric: UploadFile, sponsor_list: list[str]):
    """
    upload_info: upload rubric and sponsor list for the pitch evaluation

    must be done before the feedback can be generated.

    rubric: an image file of the rubric
    sponsor_list: a list of sponsors you wish to be considered for
    """
    # save rubric as png
    with open("rubric.png", "wb") as f:
        f.write(rubric.file.read())

    # convert rubric to json
    json_rubric = rubric_to_json("rubric.png")

    # save information for pitch eval later
    with open("rubric.json", "w") as f:
        f.write(json_rubric)
    with open("sponsor_list.json", "w") as f:
        f.write(json.dumps(sponsor_list))

# # upload pitch video
# @app.post("/upload_pitch")
# async def upload_pitch(pitch: UploadFile):
#     # TODO: process video for transcript and stats
#     transcript = None
#     stats = None
#     return {
#         "transcript": transcript,
#         "stats": stats
#     }

# start live pitch
@app.get("/live_pitch")
async def live_pitch():
    """
    live_pitch: start a live pitch session

    this starts a chatbot session meant to simulate a live pitch session. judges may interrupt if there is a long enough pause.
    this is async - the function will return when the pitch is over.
    """
    # TODO: transcript and pitch stats have not been implemented yet
    transcript = await chat_loop()
    
    with open("transcript.txt", "w") as f:
        f.write(transcript)

# get pitch feedback: aggregated data based on the pitch and q&a
@app.get("/feedback")
async def feedback():
    """
    feedback: get feedback for the pitch

    returns feedback from the pitch. return type and structure defined in evaluation.py

    requires:
    - upload_info has been called
    - live_pitch has been called and completed
    """
    evaluator = EnhancedEvaluator(openai_api_key=OPENAI_API_KEY)

    # load rubric
    with open("rubric.json", "r") as f:
        rubric = json.load(f)
        # just taking criterion for now, but the rubric has other info (eg. description of criterion, and the weight)
        rubric_categories = [x["criterion"] for x in rubric]

    # take transcript as pitch details
    with open("transcript.txt", "r") as f:
        pitch_details = f.read()

    feedback = evaluator.evaluate_project(pitch_details, rubric_categories)

    return feedback
