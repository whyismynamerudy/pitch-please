
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

PERSONALITIES = [
    {
        "name": "Alice",
        "description": "A cheerful and optimistic AI assistant who loves helping users.",
    },
    {
        "name": "Bob",
        "description": "A logical and analytical AI who enjoys solving complex problems.",
    },
    {
        "name": "Charlie",
        "description": "A creative and artistic AI with a flair for storytelling.",
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
                
                "You can either:\n"
                "1) Directly respond to the user, OR\n"
                "2) Speak among yourselves (Alice, Bob, Charlie). If you choose to speak among yourselves, please set a flag in your output as follows:\n"
                "```\n"
                "SpeakWithEachOther: true\n"
                "Alice: <some message>\n"
                "Bob: <some message>\n"
                "Charlie: <some message>\n"
                "```\n"
                "If you choose to speak only to the user, please set:\n"
                "```\n"
                "SpeakWithEachOther: false\n"
                "<your single response to the user>\n"
                "```\n"
                "You may decide at any time to invite another personality's perspective by naming them explicitly.\n\n"
                
                "Conversation so far:\n"
                "{history}\n"
                "User: {user_input}\n"
                f"{personality['name']}:\n```"
            ),
        )
        llm = ChatOpenAI(
            api_key=openai_api_key,
            model_name="gpt-4o-mini",
            temperature=0.7,
            streaming=True,
        )
        chains[personality['name']] = LLMChain(llm=llm, prompt=prompt)
    return chains
