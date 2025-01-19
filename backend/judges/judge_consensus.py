from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any
import json
from dataclasses import asdict
from judges.judges import EVALUATION_RUBRIC, SPONSOR_RUBRICS

def clean_json_string(text: str) -> str:
    """Clean up a string that might contain JSON with markdown formatting."""
    if "```" in text:
        # Extract content between ```json and ```
        lines = text.split('\n')
        cleaned_lines = []
        is_json_block = False
        
        for line in lines:
            if line.strip().startswith("```"):
                is_json_block = not is_json_block
                continue
            if is_json_block:
                cleaned_lines.append(line)
                
        if cleaned_lines:
            return '\n'.join(cleaned_lines)
    
    # If no markdown blocks found, return original text
    return text

class ConsensusBuilder:
    def __init__(self, openai_api_key: str):
        print("\n🔧 Initializing ConsensusBuilder...")
        self.discussion_template = PromptTemplate(
            input_variables=["initial_scores", "current_category", "previous_discussion"],
            template="""You are facilitating a discussion between judges about a hackathon project.
Note: This discussion is ONLY about the main hackathon rubric, not any sponsor challenges.

Initial Scores for {current_category}:
{initial_scores}

Previous Discussion (if any):
{previous_discussion}

As judges, discuss the scores for this category. Each judge should:
1. Explain their reasoning for their score
2. Listen to other perspectives
3. Consider adjusting their score based on other judges' input
4. Work towards a consensus score

Format your response as a JSON string with this exact structure:
{{
    "discussion": ["Judge A: point...", "Judge B: response...", ...],
    "consensus_score": number,
    "reasoning": "explanation for final consensus"
}}"""
        )
        
        print("🤖 Initializing ChatOpenAI for consensus...")
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model_name="gpt-4o-mini",
            temperature=0.7
        )
        
        print("🔄 Creating consensus chain...")
        self.consensus_chain = self.discussion_template | self.llm
        print("✅ ConsensusBuilder initialized successfully")

    async def build_consensus(
        self,
        category: str,
        initial_evaluations: List[Any]
    ) -> Dict[str, Any]:
        """Build consensus among judges for a specific category (main rubric only)."""
        print(f"\n🎯 Building consensus for category: {category}")
        
        # Filter out any sponsor challenge evaluations
        main_evaluations = [
            eval for eval in initial_evaluations
            if category in eval.scores  # Only include if category exists in main rubric
        ]
        
        print("📊 Formatting initial scores...")
        initial_scores = "\n".join([
            f"{eval.judge_name}: {eval.scores[category]} - {eval.feedback[category]}"
            for eval in main_evaluations
        ])
        
        print("\n📝 Initial scores and feedback:")
        print(initial_scores)

        previous_discussion = ""
        round_count = 0
        max_rounds = 3
        final_consensus = None

        while round_count < max_rounds:
            print(f"\n🔄 Starting discussion round {round_count + 1}/{max_rounds}")
            try:
                print("⏳ Awaiting consensus chain response...")
                response = await self.consensus_chain.ainvoke({
                    "initial_scores": initial_scores,
                    "current_category": category,
                    "previous_discussion": previous_discussion
                })
                
                print("\n📝 Raw consensus response:")
                print("-" * 40)
                print(response.content)
                print("-" * 40)
                
                try:
                    # Clean the response text before parsing
                    print("\n🧹 Cleaning consensus response...")
                    cleaned_text = clean_json_string(response.content)
                    print(f"\nCleaned text:\n{cleaned_text}")
                    
                    result = json.loads(cleaned_text)
                    print("✅ Successfully parsed consensus response")
                    
                    if 'consensus_score' in result:
                        print(f"🎉 Consensus reached! Score: {result['consensus_score']}")
                        final_consensus = result
                        break
                    
                    print("⏳ No consensus yet, continuing discussion...")
                    previous_discussion += "\n" + "\n".join(result['discussion'])
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing consensus discussion: {str(e)}")
                    print("Original text causing error:", cleaned_text)
                    break
                    
            except Exception as e:
                print(f"❌ Error in consensus round: {str(e)}")
                import traceback
                print("\nFull traceback:")
                traceback.print_exc()
                break
                
            round_count += 1
            print(f"✅ Completed round {round_count}")

        if not final_consensus:
            print("⚠️ No consensus reached, calculating average score...")
            avg_score = sum(
                eval.scores[category] for eval in main_evaluations
            ) / len(main_evaluations)
            
            final_consensus = {
                "discussion": [previous_discussion] if previous_discussion else ["No detailed discussion available"],
                "consensus_score": avg_score,
                "reasoning": "Consensus not reached, using average score"
            }
            print(f"📊 Used average score: {avg_score}")

        print("✅ Consensus building completed")
        return final_consensus

class JudgePanelModerator:
    def __init__(self, openai_api_key: str):
        print("\n🎭 Initializing JudgePanelModerator...")
        self.consensus_builder = ConsensusBuilder(openai_api_key)
        print("✅ JudgePanelModerator initialized")
        
    async def moderate_panel_discussion(
        self,
        evaluations: List[Dict[str, Any]],
        rubric_categories: List[str]
    ) -> Dict[str, Any]:
        """Moderate a full panel discussion for main rubric categories only."""
        print("\n🎯 Starting panel discussion moderation...")
        
        final_scores = {}
        discussions = {}
        
        # Get main rubric categories (excluding sponsor categories)
        main_categories = [
            category for category in rubric_categories
            if category in EVALUATION_RUBRIC
        ]
        
        for category in main_categories:
            print(f"\n📋 Processing category: {category}")
            consensus = await self.consensus_builder.build_consensus(
                category, evaluations
            )
            
            final_scores[category] = consensus["consensus_score"]
            discussions[category] = {
                "discussion_log": consensus["discussion"],
                "final_reasoning": consensus["reasoning"]
            }
            print(f"✅ Completed consensus for {category}")
        
        print("\n📝 Generating panel summary...")
        panel_summary = self._generate_panel_summary(discussions)
        
        return {
            "final_scores": final_scores,
            "discussion_records": discussions,
            "panel_summary": panel_summary
        }
    
    def _generate_panel_summary(self, discussions: Dict[str, Any]) -> str:
        """Generate a summary of the panel's overall discussion process."""
        print("\n📊 Generating summary of panel discussions...")
        summary_parts = []
        
        for category, discussion in discussions.items():
            print(f"Processing summary for {category}...")
            summary_parts.append(f"\n## {category} Discussion Summary:")
            if "final_reasoning" in discussion:
                summary_parts.append(discussion["final_reasoning"])
            elif "discussion_log" in discussion and discussion["discussion_log"]:
                summary_parts.append("Key discussion points:")
                for point in discussion["discussion_log"]:
                    summary_parts.append(f"- {point}")
        
        full_summary = "\n".join(summary_parts)
        print("✅ Panel summary generated")
        return full_summary