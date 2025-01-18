from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field  
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define Pydantic schema for speaking feedback
class SpeakingFeedback(BaseModel):
    pace_assessment: str = Field(description="Evaluation of speaking pace.")
    duration_assessment: str = Field(description="Evaluation of presentation duration.")
    emotion_analysis: str = Field(description="Analysis of emotional distribution.")
    speaking_style: str = Field(description="Assessment of speaking style.")
    improvement_suggestions: list[str] = Field(description="Actionable suggestions for delivery.")

def analyze_presentation(data: Dict[str, Any], openai_api_key: str) -> Dict[str, Any]:
    """Analyzes presentation data and provides structured feedback using an LLM."""
    
    llm = ChatOpenAI(
        api_key=openai_api_key,
        model_name="gpt-4o-mini",
        temperature=0.7
    )

    # Create parser
    speaking_parser = JsonOutputParser(pydantic_object=SpeakingFeedback)

    # Create prompt template with format instructions
    speaking_prompt = PromptTemplate(
        template="""Analyze the speaking metrics of this presentation:
        - WPM (Words per minute): {wpm}
        - Duration: {time}
        - Emotions detected: {emotions}

        Given that:
        - The ideal WPM range is 100-150
        - The total duration should be 5 minutes.

        {format_instructions}
        """,
        input_variables=["wpm", "time", "emotions"],
        partial_variables={"format_instructions": speaking_parser.get_format_instructions()}
    )

    # Create chain
    speaking_chain = speaking_prompt | llm | speaking_parser

    try:
        # Get structured response
        speaking_feedback = speaking_chain.invoke({
            "wpm": data['wpm'],
            "time": data['time'],
            "emotions": json.dumps(data['emotions'], indent=2)
        })

        return speaking_feedback
    
    except Exception as e:
        print(f"Error during analysis: {e}")
        return None
    
def grade_presentation(json_file_path: str, openai_api_key: str) -> None:
    """Main function to grade a presentation from a JSON file."""
    try:
        with open(json_file_path, 'r') as f:
            presentation_data = json.load(f)
        
        analysis = analyze_presentation(presentation_data, openai_api_key)
        
        if analysis:
            output_file = os.path.join("analyses", os.path.basename(json_file_path).replace('.json', '_analysis.json'))
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=4)
            print(f"Analysis saved to: {output_file}")
            print("\nAnalysis Results:")
            print(json.dumps(analysis, indent=4))
        else:
            print("Error: Could not generate analysis")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    input_file = "backend/rubric/transcripts/transcript-bad_analysis.json"
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in .env file.")
    else:
        grade_presentation(input_file, OPENAI_API_KEY)
