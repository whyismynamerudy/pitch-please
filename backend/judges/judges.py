from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any
import json

JUDGE_PERSONAS = [
    {
        "name": "RBC Judge",
        "company": "Royal Bank of Canada",
        "background": """A Senior Technology Risk Manager at RBC with 12 years of experience in financial technology.
        Expert in regulatory compliance, secure banking systems, and financial infrastructure.
        Values robust security measures, regulatory compliance, and scalable financial solutions.
        Particularly interested in projects that demonstrate enterprise-grade security and financial innovation.""",
        "evaluation_bias": """Tends to favor:
        - Bank-grade security implementations
        - Regulatory compliance considerations
        - Scalable financial solutions
        - Risk-mitigated architectures
        - Audit-friendly systems"""
    },
    {
        "name": "Google Judge",
        "company": "Google",
        "background": """A Senior Product Lead at Google with expertise in large-scale systems.
        Specializes in building highly scalable, user-centric applications.
        Champions accessibility, performance optimization, and data-driven decision making.
        Particularly interested in projects that demonstrate innovative use of technology while maintaining simplicity.""",
        "evaluation_bias": """Tends to favor:
        - Highly scalable architectures
        - User-centric design principles
        - Data-driven solutions
        - Performance-optimized implementations
        - Cross-platform accessibility"""
    },
    {
        "name": "1Password Judge",
        "company": "1Password",
        "background": """A Security Architect at 1Password specializing in privacy and security.
        Expert in cryptography, secure system design, and user privacy protection.
        Advocates for zero-knowledge architectures and end-to-end encryption.
        Particularly interested in projects that prioritize user privacy and security without compromising usability.""",
        "evaluation_bias": """Tends to favor:
        - Strong privacy-focused designs
        - Zero-knowledge architectures
        - End-to-end encryption
        - Secure by default implementations
        - Human-centric security"""
    }
]

EVALUATION_RUBRIC = {
    "practicality_and_impact": {
        "weight": 0.25,
        "description": "Assessment of project feasibility and its potential real-world impact. Evaluates whether the solution is practical to implement and can create meaningful change."
    },
    "pitching": {
        "weight": 0.15,
        "description": "Evaluation of presentation clarity, organization, and effectiveness. Considers how well the team communicates their idea, demonstrates their solution, and handles Q&A."
    },
    "design": {
        "weight": 0.20,
        "description": "Quality of user interface, user experience, visual aesthetics, and accessibility considerations. Assesses how intuitive, appealing, and inclusive the solution is."
    },
    "completion": {
        "weight": 0.25,
        "description": "Level of functionality and polish in the final product. Evaluates working features, stability, and overall refinement of the implementation."
    },
    "theme_and_originality": {
        "weight": 0.15,
        "description": "Assessment of how well the project aligns with hackathon themes, its innovation, and uniqueness. Considers the creativity of the solution and its novelty in addressing the problem."
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
        '        "practicality_and_impact": 8.5,\n'
        '        "pitching": 7.5,\n'
        '        "design": 8.0,\n'
        '        "completion": 9.0,\n'
        '        "theme_and_originality": 8.0\n'
        "    }},\n"
        '    "feedback": {{\n'
        '        "practicality_and_impact": "Your detailed feedback here",\n'
        '        "pitching": "Your detailed feedback here",\n'
        '        "design": "Your detailed feedback here",\n'
        '        "completion": "Your detailed feedback here",\n'
        '        "theme_and_originality": "Your detailed feedback here"\n'
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
    model_name: str = "gpt-4o-mini",
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