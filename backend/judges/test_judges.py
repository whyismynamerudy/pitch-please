import asyncio
import os
from dotenv import load_dotenv
from evaluation import EnhancedEvaluator
from judges import EVALUATION_RUBRIC

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

# Sample project pitch for testing
SAMPLE_PITCH = """
Project Name: EcoTracker - AI-Powered Sustainability Assistant

Our team has developed EcoTracker, an innovative mobile application that helps individuals and businesses track and reduce their carbon footprint using AI technology. Key features include:

1. Real-time Carbon Footprint Monitoring:
   - Uses computer vision to analyze photos of receipts and automatically calculate carbon impact
   - Integrates with smart home devices to track energy usage
   - ML models predict and suggest optimal energy usage patterns

2. Technical Implementation:
   - Built using React Native for cross-platform compatibility
   - TensorFlow Lite for on-device ML processing
   - Cloud-based analytics using AWS
   - Blockchain integration for carbon credit trading

3. Innovation:
   - First app to use AI for receipt-based carbon tracking
   - Novel approach to gamification of sustainability
   - Unique social features for community engagement

4. Market Impact:
   - Target market: Environmentally conscious consumers and businesses
   - Already has 1000+ beta users
   - Potential to reduce individual carbon footprint by 20%

5. Future Plans:
   - Expanding ML capabilities
   - Adding business-specific features
   - Integration with smart city infrastructure
"""

# Get rubric categories
RUBRIC_CATEGORIES = list(EVALUATION_RUBRIC.keys())

async def run_test():
    print("Starting evaluation test...")
    
    # Initialize the evaluator
    evaluator = EnhancedEvaluator(OPENAI_API_KEY)
    
    try:
        # Run the evaluation
        print("\nRunning project evaluation...")
        results = await evaluator.evaluate_project(SAMPLE_PITCH, RUBRIC_CATEGORIES)
        
        # Print individual evaluations
        print("\n=== Individual Judge Evaluations ===")
        for eval in results["individual_evaluations"]:
            print(f"\nJudge: {eval['judge_name']} ({eval['company']})")
            print("Scores:")
            for category, score in eval["scores"].items():
                print(f"  {category}: {score}")
            print("\nKey Points:")
            for point in eval["key_points"]:
                print(f"  - {point}")
            print("\nOverall Feedback:")
            print(f"  {eval['overall_feedback']}")
        
        # Print consensus evaluation
        print("\n=== Consensus Evaluation ===")
        consensus = results["consensus_evaluation"]
        print("\nFinal Scores:")
        for category, score in consensus["final_scores"].items():
            print(f"  {category}: {score}")
        
        print("\nDiscussion Summary:")
        print(consensus["discussion_summary"])
        
        # Print meta-analysis
        print("\n=== Meta Analysis ===")
        meta = results["meta_analysis"]
        print("\nScore Changes:")
        for category, changes in meta["score_changes"].items():
            print(f"\n{category}:")
            print(f"  Initial scores: {changes['initial_scores']}")
            print(f"  Final score: {changes['final_score']}")
            print(f"  Average change: {changes['average_change']:.2f}")
        
        print("\nDiscussion Highlights:")
        for highlight in meta["discussion_highlights"]:
            print(f"  - {highlight}")
            
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_test())