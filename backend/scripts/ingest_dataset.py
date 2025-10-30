# backend/scripts/ingest_dataset.py
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd
from neo4j import GraphDatabase

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# --- Import SemanticSearch ---
from backend.core.semantic_search import SemanticSearch
from backend.core.config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    DATA_DIR,
)
from kaggle.api.kaggle_api_extended import KaggleApi

# ==============================
# CONFIG
# ==============================
KAGGLE_DATASET = "jrobischon/wikipedia-movie-plots"
WIKI_CSV_PATH = DATA_DIR / "wiki_movie_plots_deduped.csv"
BATCH_SIZE = 50  # This is now only for Neo4j
MOVIE_LIMIT = 15000 # Make sure this is 3000 or more


# ==============================
# 1. FETCH DATASET FROM KAGGLE
# ==============================
def fetch_dataset(limit: int = None) -> List[Dict]:
    print("Fetching dataset from Kaggle...")

    api = KaggleApi()
    api.authenticate()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not WIKI_CSV_PATH.exists():
        print("Downloading dataset...")
        api.dataset_download_files(KAGGLE_DATASET, path=str(DATA_DIR), unzip=True)
    else:
        print("Dataset already downloaded.")

    print("Loading CSV...")
    df = pd.read_csv(WIKI_CSV_PATH)
    df = df.dropna(subset=["Title", "Plot"])
    df = df.rename(columns=lambda x: x.strip().lower())

    movies = []
    
    # --- Use .sample() for better variety ---
    # (random_state=42 ensures you get the same "random" sample every time)
    sample_df = df.sample(n=min(limit, len(df)), random_state=42)
    
    for idx, row in sample_df.iterrows():
        movies.append({
            "id": int(idx),
            "title": str(row["title"]).strip(),
            "plot": str(row["plot"]).strip(),
            "genre": str(row.get("genre", "Unknown")).strip(),
            "director": str(row.get("director", "Unknown")).strip(),
            "cast": [a.strip() for a in str(row.get("cast", "")).split(",") if a.strip()],
            "release_year": row.get("release year"),
        })

    print(f"Loaded {len(movies)} movies.")
    return movies


# ==============================
# 2. SETUP QDRANT (Simplified)
# ==============================
def setup_qdrant(movies: List[Dict]):
    print("Setting up Qdrant Cloud via SemanticSearch class...")
    
    # --- DELEGATE TO SemanticSearch ---
    # It handles connection, collection creation, and batching
    ss = SemanticSearch()
    ss.index_movies(movies)
    # --- That's it! ---

    print("Qdrant indexing complete.")


# ==============================
# 3. SETUP NEO4J (No changes needed)
# ==============================
def setup_neo4j(movies: List[Dict]):
    print("Setting up Neo4j Aura knowledge graph...")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def tx_func(tx, batch):
        tx.run("""
            UNWIND $batch AS m
            MERGE (mov:Movie {id: m.id})
            SET mov.title = m.title,
                mov.release_year = m.release_year,
                mov.genre = m.genre  // <-- Store genre on the movie node

            // Director
            MERGE (dir:Director {name: m.director})
            MERGE (mov)-[:DIRECTED_BY]->(dir)

            // Actors
            FOREACH (actorName IN m.cast |
                MERGE (act:Actor {name: actorName})
                MERGE (act)-[:ACTED_IN]->(mov)
            )

            // Genres (split by comma or known delimiters)
            FOREACH (g IN [g IN split(m.genre, ',') WHERE g <> ''] +
                       [g IN split(m.genre, ';') WHERE g <> ''] +
                       CASE WHEN m.genre IN ['unknown', 'Unknown', ''] THEN [] ELSE [m.genre] END |
                MERGE (gen:Genre {name: trim(g)})
                MERGE (mov)-[:HAS_GENRE]->(gen)
            )
        """, batch=batch)

    with driver.session() as session:
        # Optional: Clear previous data
        print("Clearing existing graph...")
        session.run("MATCH (n) DETACH DELETE n")

        # Batch insert
        for i in range(0, len(movies), BATCH_SIZE):
            batch = movies[i:i + BATCH_SIZE]
            session.execute_write(tx_func, batch)
            print(f"  Neo4j batch {i//BATCH_SIZE + 1}/{(len(movies)-1)//BATCH_SIZE + 1}")

    driver.close()
    print("Neo4j setup complete.")


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    print("Starting Movie Engine data ingestion pipeline...\n")

    # 1. Load data
    movies = fetch_dataset(limit=MOVIE_LIMIT)

    # 2. Index into Qdrant
    # (The model is loaded inside the SemanticSearch class now)
    setup_qdrant(movies)

    # 3. Build Neo4j KG
    setup_neo4j(movies)

    print("\nAll done! Dataset fully ingested into Qdrant + Neo4j.")