# personalities.py
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

PERSONALITIES = [
    {
        "name": "Alice",
        "description": "A cheerful and optimistic AI assistant who loves helping users.",
        "voice_id": "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    },
    {
        "name": "Bob",
        "description": "A logical and analytical AI who enjoys solving complex problems.",
        "voice_id": "TxGEqnHWrfWFTfGW9XjX"  # Josh voice
    },
    {
        "name": "Charlie",
        "description": "A creative and artistic AI with a flair for storytelling.",
        "voice_id": "VR6AewLTigWG4xSOukaG"  # Arnold voice
    },
]
def get_personality_chains(openai_api_key):
    chains = {}
    
    # Dynamically generate the list of personality descriptions for the prompt
    personality_descriptions = "\n".join(
        [f"- {p['name']}: {p['description']}" for p in PERSONALITIES]
    )
    
    for personality in PERSONALITIES:
        # Create a dynamic prompt template
        prompt = PromptTemplate(
            input_variables=["user_input"],
            template=(
                f"You are {personality['name']}, {personality['description']}.\n\n"
                "The following are the personalities you can interact with:\n"
                f"{personality_descriptions}\n\n"
                "You can speak to the user (Route=2) OR you can speak to another AI personality (Route=1).\n"
                "If you choose Route=1, also specify which personality you want to speak to in 'Target'.\n"
                "If you choose Route=2, you are speaking directly to the user (this ends your chain of passing).\n\n"
                "Your response MUST follow this exact format (no extra text):\n"
                "Route: X\n"
                "Target: (only needed if X=1)\n"
                "Message: <your text here>\n\n"
                "User: {user_input}\n\n"
                f"{personality['name']}: "
            ),
        )

        # Create an LLM chain for each personality
        llm = ChatOpenAI(
            api_key=openai_api_key,
            model_name="gpt-4o-mini",
            temperature=0.7,
            streaming=True
        )
        
        chain = prompt | llm
        chains[personality['name']] = {
            "chain": chain,
            "voice_id": personality["voice_id"]
        }
    
    return chains

