from dataclasses import dataclass, asdict
import json
from typing import Dict, List, Any
import asyncio
from judges import JUDGE_PERSONAS, EVALUATION_RUBRIC
from judge_consensus import JudgePanelModerator
from judges import get_all_judge_chains

def clean_json_string(text: str) -> str:
    """Clean up a string that might contain JSON with markdown formatting."""
    # Remove markdown code block if present
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

@dataclass
class InitialEvaluation:
    judge_name: str
    company: str
    scores: Dict[str, float]
    feedback: Dict[str, str]
    overall_feedback: str
    key_points: List[str]

@dataclass
class ConsensusEvaluation:
    category_scores: Dict[str, float]
    category_discussions: Dict[str, Any]
    final_feedback: str
    panel_summary: str

class EnhancedEvaluator:
    def __init__(self, openai_api_key: str):
        print("\n🔧 Initializing EnhancedEvaluator...")
        self.openai_api_key = openai_api_key
        self.panel_moderator = JudgePanelModerator(openai_api_key)
        print("📚 Getting judge chains...")
        self.judge_chains = get_all_judge_chains(openai_api_key)
        print(f"✅ Successfully initialized {len(self.judge_chains)} judge chains")

    async def evaluate_project(
        self,
        pitch_details: str,
        rubric_categories: List[str]
    ) -> Dict[str, Any]:
        """Complete evaluation process including individual judgments and consensus building."""
        print("\n🔄 Starting project evaluation process...")
        
        # Get initial evaluations from each judge
        print("\n👥 Gathering initial evaluations from judges...")
        initial_evaluations = await self._gather_initial_evaluations(
            pitch_details,
            rubric_categories
        )
        
        if not initial_evaluations:
            print("❌ No valid evaluations received from any judge!")
            raise ValueError("No valid evaluations received from judges")
        
        print(f"✅ Received {len(initial_evaluations)} valid evaluations")
            
        # Build consensus through panel discussion
        print("\n🤝 Starting consensus building process...")
        consensus = await self.panel_moderator.moderate_panel_discussion(
            initial_evaluations,
            rubric_categories
        )
        print("✅ Consensus building completed")
        
        # Generate final report
        print("\n📊 Generating final report...")
        return self._generate_final_report(initial_evaluations, consensus)

    async def _gather_initial_evaluations(
        self,
        pitch_details: str,
        rubric_categories: List[str]
    ) -> List[InitialEvaluation]:
        """Gather initial evaluations from all judges."""
        evaluation_tasks = []
        
        # Format rubric as a detailed string with descriptions
        rubric_str = "Evaluation Criteria:\n" + "\n".join([
            f"{category}:\n"
            f"- Description: {EVALUATION_RUBRIC[category]['description']}\n"
            f"- Weight: {EVALUATION_RUBRIC[category]['weight']}"
            for category in rubric_categories
        ])
        
        print(f"\n📋 Formatted rubric for judges:\n{rubric_str}\n")
        
        for judge_name, chain in self.judge_chains.items():
            print(f"\n🧑‍⚖️ Creating evaluation task for {judge_name}...")
            task = asyncio.create_task(
                chain.ainvoke({
                    "pitch_details": pitch_details,
                    "rubric": rubric_str
                })
            )
            evaluation_tasks.append((judge_name, task))
        
        evaluations = []
        for judge_name, task in evaluation_tasks:
            try:
                print(f"\n⏳ Awaiting evaluation from {judge_name}...")
                result = await task
                print(f"✅ Received response from {judge_name}")
                
                # Extract content from the ChatMessage object
                if hasattr(result, 'content'):
                    result_text = result.content
                else:
                    result_text = str(result)
                
                print(f"\n📝 Raw response from {judge_name}:")
                print("-" * 40)
                print(result_text)
                print("-" * 40)
                
                # Clean and parse the JSON response
                print(f"\n🔍 Parsing response from {judge_name}...")
                cleaned_text = clean_json_string(result_text)
                print(f"\n🧹 Cleaned JSON text:")
                print(cleaned_text)
                parsed_result = json.loads(cleaned_text)
                
                # Verify required fields
                required_fields = {'scores', 'feedback', 'overall_feedback', 'key_points'}
                missing_fields = required_fields - set(parsed_result.keys())
                if missing_fields:
                    raise ValueError(f"Missing required fields: {missing_fields}")
                
                print(f"✅ Successfully parsed response from {judge_name}")
                
                # Create evaluation object
                evaluations.append(
                    InitialEvaluation(
                        judge_name=judge_name,
                        company=next(
                            j["company"] for j in JUDGE_PERSONAS
                            if j["name"] == judge_name
                        ),
                        scores=parsed_result['scores'],
                        feedback=parsed_result['feedback'],
                        overall_feedback=parsed_result['overall_feedback'],
                        key_points=parsed_result['key_points']
                    )
                )
                print(f"✅ Created evaluation object for {judge_name}")
                
            except Exception as e:
                print(f"\n❌ Error in evaluation from {judge_name}: {str(e)}")
                import traceback
                print("\nFull traceback:")
                traceback.print_exc()
                continue
        
        return evaluations

    def _generate_final_report(
        self,
        initial_evaluations: List[InitialEvaluation],
        consensus: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive final report including individual and consensus evaluations."""
        print("\n📊 Generating final report...")
        
        report = {
            "individual_evaluations": [
                asdict(eval) for eval in initial_evaluations
            ],
            "consensus_evaluation": {
                "final_scores": consensus["final_scores"],
                "discussion_summary": consensus["panel_summary"],
                "detailed_discussions": consensus["discussion_records"]
            },
            "meta_analysis": {
                "score_changes": self._analyze_score_changes(
                    initial_evaluations,
                    consensus["final_scores"]
                ),
                "discussion_highlights": self._extract_discussion_highlights(
                    consensus["discussion_records"]
                )
            }
        }
        
        print("✅ Final report generated")
        return report

    def _analyze_score_changes(
        self,
        initial_evaluations: List[InitialEvaluation],
        final_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze how scores changed during discussion."""
        print("\n📈 Analyzing score changes...")
        changes = {}
        for category, final_score in final_scores.items():
            initial_scores = [
                eval.scores[category] for eval in initial_evaluations
            ]
            avg_initial = sum(initial_scores) / len(initial_scores)
            changes[category] = {
                "initial_scores": initial_scores,
                "final_score": final_score,
                "average_change": abs(final_score - avg_initial),
                "score_range": max(initial_scores) - min(initial_scores),
                "consensus_delta": abs(final_score - avg_initial)
            }
            print(f"✅ Analyzed changes for {category}")
        return changes

    def _extract_discussion_highlights(
        self,
        discussions: Dict[str, Any]
    ) -> List[str]:
        """Extract key points from the discussion records."""
        print("\n💭 Extracting discussion highlights...")
        highlights = []
        for category, discussion in discussions.items():
            print(f"Processing highlights for {category}...")
            if isinstance(discussion, dict):
                if 'final_reasoning' in discussion:
                    highlights.append(
                        f"{category}: {discussion['final_reasoning']}"
                    )
                    print(f"✅ Added final reasoning for {category}")
                elif 'discussion_log' in discussion and discussion['discussion_log']:
                    highlights.append(
                        f"{category}: {discussion['discussion_log'][-1]}"
                    )
                    print(f"✅ Added last discussion point for {category}")
        return highlights