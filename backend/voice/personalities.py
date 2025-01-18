# personalities.py
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from operator import itemgetter
from langchain.schema.runnable import RunnablePassthrough

# Define the personalities with their voice IDs
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
    for personality in PERSONALITIES:
        prompt = PromptTemplate(
            input_variables=["history", "user_input"],
            template=(
                f"You are {personality['name']}, {personality['description']}. "
                f"You are one of three personalities: Alice, Bob, and Charlie.\n\n"
                
                "You can either respond directly to the user or speak among yourselves.\n"
                "If speaking to the user, respond naturally without any formatting or tags.\n"
                "If speaking among yourselves, simply start each line with the speaker's name followed by a colon.\n\n"
                
                "Current conversation:\n"
                "{history}\n"
                "User: {user_input}\n"
                f"{personality['name']}: "
            ),
        )
        
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