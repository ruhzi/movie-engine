# test_recommender.py
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).resolve().parents[0]
sys.path.append(str(project_root))

# Load .env automatically (must be in project root)
load_dotenv()  # <-- This reads your .env file

# --- We only need to import the final Recommender ---
from backend.core.recommender import Recommender


def test_hybrid_recommender(query: str):
    """
    Tests the full hybrid recommendation pipeline.
    """
    print(f"\n{'*'*60}")
    print(f"HYBRID RECOMMENDER QUERY: '{query}'")
    print(f"{'*'*60}")

    # We can just call Recommender() now, thanks to our fix.
    # It will automatically pick up .env credentials.
    recommender = Recommender() 
    
    results = recommender.recommend(
        query=query, 
        vector_limit=3,  # Get top 3 semantic matches
        graph_limit=5    # Expand with 5 graph connections
    )
    recommender.close()

    if not results:
        print("No recommendations found.")
        return

    print(f"--- Found {len(results)} total recommendations ---")
    for i, rec in enumerate(results, 1):
        # Format the score string only if it exists (i.e., from vector search)
        score_str = f" | Score: {rec['score']:.3f}" if rec.get('score') is not None else ""
        
        print(f"{i}. {rec['title']} "
              f"| {rec.get('genre', 'N/A')} "
              f"| Year: {rec.get('year', 'N/A')}"
              f"{score_str} [Source: {rec['source']}]")


if __name__ == "__main__":
    queries_to_test = [
        "an action flick set in bombay",
        "period film set in world war 1",
        "a fun sci-fi movie about aliens visiting earth"
    ]

    for q in queries_to_test:
        test_hybrid_recommender(q)