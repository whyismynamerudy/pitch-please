from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any
import json

# Sponsor-specific rubrics
SPONSOR_RUBRICS = {
    "rbc_challenge": {
        "cyber_security": {
            "weight": 4,
            "description": "Effectiveness of cyber threat prevention measures for young banking customers. Evaluates the robustness of security features and protection against common cyber threats."
        },
        "student_focus": {
            "weight": 3,
            "description": "Relevance and appeal to student banking needs. Assesses how well the solution addresses specific financial challenges faced by students."
        },
        "implementation_feasibility": {
            "weight": 3,
            "description": "Technical feasibility of integration with banking systems. Evaluates the practicality of implementing the solution within existing banking infrastructure."
        },
        "regulatory_compliance": {
            "weight": 2,
            "description": "Adherence to banking regulations and security standards. Assesses compliance with financial regulations and data protection requirements."
        }
    }
}

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
        - Audit-friendly systems""",
        "sponsor_challenge": {
            "name": "Young, Smart, & Financially Savvy",
            "description": "Focus on enhancing RBC's student banking offerings to limit cyber threats as youth engage in online shopping and finances.",
            "criteria": SPONSOR_RUBRICS["rbc_challenge"]
        }
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

# Main hackathon rubric
EVALUATION_RUBRIC = {
    "practicality_and_impact": {
        "weight": 5,
        "description": "Assessment of project feasibility and its potential real-world impact. Evaluates whether the solution is practical to implement and can create meaningful change."
    },
    "pitching": {
        "weight": 2,
        "description": "Evaluation of presentation clarity, organization, and effectiveness. Considers how well the team communicates their idea, demonstrates their solution, and handles Q&A."
    },
    "design": {
        "weight": 4,
        "description": "Quality of user interface, user experience, visual aesthetics, and accessibility considerations. Assesses how intuitive, appealing, and inclusive the solution is."
    },
    "completion": {
        "weight": 5,
        "description": "Level of functionality and polish in the final product. Evaluates working features, stability, and overall refinement of the implementation."
    },
    "theme_and_originality": {
        "weight": 3,
        "description": "Assessment of how well the project aligns with hackathon themes, its innovation, and uniqueness. Considers the creativity of the solution and its novelty in addressing the problem."
    }
}

def get_judge_prompt_template(persona: Dict[str, str]) -> PromptTemplate:
    """Creates a prompt template for a specific judge persona."""
    
    # Base evaluation template
    base_template = (
        f"You are a judge from {persona['company']} evaluating hackathon projects.\n"
        f"Background: {persona['background']}\n"
        f"Evaluation Style: {persona['evaluation_bias']}\n\n"
        "Project Pitch Details:\n{pitch_details}\n\n"
    )
    
    # Add sponsor challenge context if applicable
    if "sponsor_challenge" in persona:
        base_template += (
            f"You are also evaluating for the {persona['sponsor_challenge']['name']} sponsor challenge.\n"
            f"Challenge Focus: {persona['sponsor_challenge']['description']}\n\n"
        )
    
    base_template += (
        "Evaluation Rubric:\n{rubric}\n\n"
        "Please provide your evaluation in JSON format with this exact structure:\n"
        "{{\n"  # Note the double braces for escaping
        '    "main_evaluation": {{\n'  # Double braces here too
        '        "scores": {{\n'
        '            "practicality_and_impact": 8.5,\n'
        '            "pitching": 7.5,\n'
        '            "design": 8.0,\n'
        '            "completion": 9.0,\n'
        '            "theme_and_originality": 8.0\n'
        "        }},\n"
        '        "feedback": {{\n'
        '            "practicality_and_impact": "Your detailed feedback here",\n'
        '            "pitching": "Your detailed feedback here",\n'
        '            "design": "Your detailed feedback here",\n'
        '            "completion": "Your detailed feedback here",\n'
        '            "theme_and_originality": "Your detailed feedback here"\n'
        "        }},\n"
        '        "overall_feedback": "Your overall perspective of the project",\n'
        '        "key_points": [\n'
        '            "Key strength or weakness 1",\n'
        '            "Key strength or weakness 2",\n'
        '            "Key strength or weakness 3"\n'
        "        ]\n"
        "    }}"
    )
    
    # Add sponsor challenge evaluation if applicable
    if "sponsor_challenge" in persona:
        base_template += ',\n'
        base_template += (
            '    "sponsor_challenge_evaluation": {{\n'
            f'        "challenge_name": "{persona["sponsor_challenge"]["name"]}",\n'
            '        "scores": {{\n'
            '            "cyber_security": 0.0,\n'
            '            "student_focus": 0.0,\n'
            '            "implementation_feasibility": 0.0,\n'
            '            "regulatory_compliance": 0.0\n'
            "        }},\n"
            '        "feedback": {{\n'
            '            "cyber_security": "Your detailed feedback here",\n'
            '            "student_focus": "Your detailed feedback here",\n'
            '            "implementation_feasibility": "Your detailed feedback here",\n'
            '            "regulatory_compliance": "Your detailed feedback here"\n'
            "        }},\n"
            '        "challenge_specific_feedback": "Your overall assessment for the sponsor challenge",\n'
            '        "key_strengths": [\n'
            '            "Strength 1",\n'
            '            "Strength 2",\n'
            '            "Strength 3"\n'
            "        ],\n"
            '        "areas_for_improvement": [\n'
            '            "Area 1",\n'
            '            "Area 2",\n'
            '            "Area 3"\n'
            "        ]\n"
            "    }}"
        )
    
    base_template += "\n}}"  # Close the main JSON object
    
    return PromptTemplate(
        input_variables=["pitch_details", "rubric"],
        template=base_template
    )

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