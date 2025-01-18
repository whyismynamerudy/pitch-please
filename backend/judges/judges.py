from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any
import json

JUDGE_PERSONAS = [
    {
        "name": "TechCorp Judge",
        "company": "TechCorp",
        "background": """A Senior Engineering Manager at TechCorp with 10 years of experience in cloud infrastructure. 
        Values scalable architecture, clean code, and innovative solutions to enterprise problems. 
        Has a strong focus on security and performance optimization.
        Particularly interested in projects that could benefit large-scale enterprise systems.""",
        "evaluation_bias": """Tends to favor:
        - Enterprise-ready solutions
        - Scalable architectures
        - Security-first approaches
        - Performance optimized solutions
        - Clear documentation and clean code"""
    },
    {
        "name": "StartupInc Judge",
        "company": "StartupInc",
        "background": """A Product Manager at StartupInc, a fast-growing startup unicorn.
        Expert in rapid prototyping and MVP development.
        Strongly believes in user-centric design and rapid iteration.
        Looking for projects that solve real user problems in creative ways.""",
        "evaluation_bias": """Tends to favor:
        - User-focused solutions
        - Quick MVP implementations
        - Creative problem-solving
        - Market potential
        - Growth potential"""
    },
    {
        "name": "DataAI Judge",
        "company": "DataAI",
        "background": """A Data Scientist at DataAI, specializing in machine learning and AI solutions.
        Passionate about innovative applications of AI/ML.
        Focuses on data-driven decision making and algorithmic efficiency.
        Interested in projects that leverage AI/ML in novel ways.""",
        "evaluation_bias": """Tends to favor:
        - AI/ML applications
        - Data-driven approaches
        - Algorithm efficiency
        - Novel use of technology
        - Ethical AI considerations"""
    }
]

EVALUATION_RUBRIC = {
    "technical_complexity": {
        "weight": 0.25,
        "description": "Assessment of the technical sophistication and implementation quality"
    },
    "innovation": {
        "weight": 0.25,
        "description": "Evaluation of the uniqueness and creativity of the solution"
    },
    "practicality": {
        "weight": 0.20,
        "description": "Assessment of real-world applicability and feasibility"
    },
    "presentation": {
        "weight": 0.15,
        "description": "Quality of pitch presentation and demo"
    },
    "impact": {
        "weight": 0.15,
        "description": "Potential social or business impact of the solution"
    }
}

def get_judge_prompt_template(persona: Dict[str, str]) -> PromptTemplate:
    """Creates a prompt template for a specific judge persona."""
    print(f"\n📝 Creating prompt template for {persona['name']}...")
    template = (
        f"You are a judge from {persona['company']} evaluating hackathon projects.\n"
        f"Background: {persona['background']}\n"
        f"Evaluation Style: {persona['evaluation_bias']}\n\n"
        "Project Pitch Details:\n{pitch_details}\n\n"
        "Evaluation Rubric:\n{rubric}\n\n"
        "Please provide your evaluation in JSON format with this exact structure:\n"
        "{{\n"
        '    "scores": {{\n'
        '        "technical_complexity": 8.5,\n'
        '        "innovation": 7.5,\n'
        '        "practicality": 8.0,\n'
        '        "presentation": 9.0,\n'
        '        "impact": 8.0\n'
        "    }},\n"
        '    "feedback": {{\n'
        '        "technical_complexity": "Your detailed feedback here",\n'
        '        "innovation": "Your detailed feedback here",\n'
        '        "practicality": "Your detailed feedback here",\n'
        '        "presentation": "Your detailed feedback here",\n'
        '        "impact": "Your detailed feedback here"\n'
        "    }},\n"
        '    "overall_feedback": "Your overall perspective of the project",\n'
        '    "key_points": [\n'
        '        "Key strength or weakness 1",\n'
        '        "Key strength or weakness 2",\n'
        '        "Key strength or weakness 3"\n'
        "    ]\n"
        "}}\n"
    )
    
    prompt = PromptTemplate(
        input_variables=["pitch_details", "rubric"],
        template=template
    )
    print(f"✅ Created prompt template for {persona['name']}")
    return prompt

def create_judge_chain(
    persona: Dict[str, str],
    openai_api_key: str,
    model_name: str = "gpt-4",
    temperature: float = 0.5
):
    """Creates a runnable sequence for a judge persona."""
    print(f"\n🔄 Creating chain for {persona['name']}...")
    
    print(f"🤖 Initializing ChatOpenAI for {persona['name']}...")
    llm = ChatOpenAI(
        api_key=openai_api_key,
        model_name=model_name,
        temperature=temperature
    )
    
    print(f"📋 Getting prompt template for {persona['name']}...")
    prompt = get_judge_prompt_template(persona)
    
    print(f"🔗 Creating runnable chain for {persona['name']}...")
    chain = prompt | llm
    
    print(f"✅ Successfully created chain for {persona['name']}")
    return chain

def get_all_judge_chains(openai_api_key: str) -> Dict[str, Any]:
    """Creates runnable sequences for all judge personas."""
    print("\n👥 Creating chains for all judges...")
    chains = {}
    
    for persona in JUDGE_PERSONAS:
        print(f"\n🧑‍⚖️ Processing {persona['name']}...")
        chains[persona["name"]] = create_judge_chain(persona, openai_api_key)
        print(f"✅ Added chain for {persona['name']}")
    
    print(f"\n✨ Successfully created {len(chains)} judge chains")
    return chains