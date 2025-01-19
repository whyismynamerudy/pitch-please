import asyncio
import os
from dotenv import load_dotenv
from evaluation import EnhancedEvaluator
from judges import EVALUATION_RUBRIC, SPONSOR_RUBRICS

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

# Sample project pitch for testing
SAMPLE_PITCH = """
Project Name: SecureSpend - AI-Powered Student Financial Security

Our team has developed SecureSpend, an innovative banking security solution specifically designed for students. Key features include:

1. AI-Powered Fraud Detection:
   - Uses machine learning to detect unusual spending patterns
   - Real-time transaction monitoring
   - Behavioral analysis to identify potential threats

2. Student-Focused Security Features:
   - Customizable spending limits and categories
   - Location-based transaction verification
   - Peer-to-peer payment protection

3. Technical Implementation:
   - Built using React Native and Node.js
   - AWS Lambda for serverless processing
   - Blockchain for transaction verification
   - End-to-end encryption for all data

4. Education Component:
   - Interactive tutorials on financial security
   - Gamified learning modules
   - Real-world case studies of cyber threats

5. Future Plans:
   - Integration with major banking systems
   - Expansion to international student markets
   - Advanced biometric authentication
"""

async def run_test():
    print("Starting enhanced evaluation test...")
    
    # Initialize the evaluator
    evaluator = EnhancedEvaluator(OPENAI_API_KEY)
    
    try:
        # Get main rubric categories
        main_categories = list(EVALUATION_RUBRIC.keys())
        
        # Run the evaluation
        print("\nRunning project evaluation...")
        results = await evaluator.evaluate_project(SAMPLE_PITCH, main_categories)
        
        # Print main evaluation results
        print("\n=== Main Hackathon Evaluation ===")
        print("\nIndividual Judge Evaluations:")
        for eval in results["main_evaluation"]["individual_evaluations"]:
            print(f"\nJudge: {eval['judge_name']} ({eval['company']})")
            print("Scores:")
            for category, score in eval["scores"].items():
                print(f"  {category}: {score}")
            print("\nKey Points:")
            for point in eval["key_points"]:
                print(f"  - {point}")
        
        # Print consensus results
        print("\n=== Consensus Evaluation ===")
        consensus = results["main_evaluation"]["consensus_evaluation"]
        print("\nFinal Scores:")
        for category, score in consensus["final_scores"].items():
            print(f"  {category}: {score}")
        
        print("\nDiscussion Summary:")
        print(consensus["discussion_summary"])
        
        # Print sponsor challenge results
        print("\n=== Sponsor Challenge Results ===")
        for challenge_name, challenge_data in results["sponsor_challenges"].items():
            print(f"\n{challenge_name} Challenge")
            print(f"Evaluated by: {challenge_data['evaluator']} ({challenge_data['company']})")
            
            eval_data = challenge_data["evaluation"]
            print("\nScores:")
            for criterion, score in eval_data["scores"].items():
                print(f"  {criterion}: {score}")
            
            print("\nKey Strengths:")
            for strength in eval_data["key_strengths"]:
                print(f"  - {strength}")
            
            print("\nAreas for Improvement:")
            for area in eval_data["areas_for_improvement"]:
                print(f"  - {area}")
            
            print("\nChallenge-Specific Feedback:")
            print(eval_data["challenge_specific_feedback"])
        
        # Print meta-analysis
        print("\n=== Meta Analysis ===")
        meta = results["main_evaluation"]["meta_analysis"]
        print("\nScore Changes:")
        for category, changes in meta["score_changes"].items():
            print(f"\n{category}:")
            print(f"  Initial scores: {changes['initial_scores']}")
            print(f"  Final score: {changes['final_score']}")
            print(f"  Average change: {changes['average_change']:.2f}")
        
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())