from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from .config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, EMBEDDING_MODEL
from typing import List, Dict, Union
from pathlib import Path
import json
import time


class SemanticSearch:
    """
    Cloud-based semantic search service.
    Uses Qdrant Cloud for vector storage + retrieval and SentenceTransformers for embeddings.
    """

    def __init__(self):
        # Connect to Qdrant Cloud
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=60.0  # longer timeout for large uploads
        )

        # Load embedding model (cached automatically)
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # --- FIX 1: DYNAMIC EMBEDDING SIZE ---
        try:
            embedding_size = self.model.get_sentence_embedding_dimension()
            if not embedding_size:
                raise ValueError("Could not determine embedding model dimension.")
        except Exception as e:
            print(f"Error getting embedding dimension, defaulting to 384: {e}")
            embedding_size = 384
        # --- END FIX 1 ---

        # Ensure collection exists
        collections = [c.name for c in self.client.get_collections().collections]
        if QDRANT_COLLECTION not in collections:
            print(f"Creating Qdrant collection '{QDRANT_COLLECTION}'...")
            self.client.recreate_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=embedding_size,  # <-- Use dynamic size
                    distance=Distance.COSINE
                ),
            )
            print("Collection created successfully.")
        else:
            print(f"Using existing Qdrant collection: {QDRANT_COLLECTION}")

        self.collection_name = QDRANT_COLLECTION

    def index_movies(self, movies: Union[List[Dict], Path]):
        """
        Upload movie embeddings to Qdrant Cloud in batches (to avoid timeouts).
        Accepts either a list of dicts or a JSON file path.
        """
        if isinstance(movies, Path):
            if not movies.exists():
                raise FileNotFoundError(f"Movie data file not found: {movies}")
            with open(movies, "r", encoding="utf-8") as f:
                movies = json.load(f)

        print(f"Indexing {len(movies)} movies to Qdrant Cloud...")

        points = []
        for m in movies:
            if not m.get("plot"):
                continue
            vector = self.model.encode(m["plot"]).tolist()
            points.append(
                PointStruct(
                    id=m.get("id"),
                    vector=vector,
                    # This payload is perfect, no changes needed
                    payload={
                        "title": m.get("title"),
                        "genre": m.get("genre"),
                        "director": m.get("director"),
                        "year": m.get("release_year"),
                    },
                )
            )

        # Batch upload
        batch_size = 50
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            attempt = 0
            while attempt < 3:  # retry up to 3 times
                try:
                    self.client.upsert(collection_name=self.collection_name, points=batch)
                    print(f"Indexed batch {i // batch_size + 1}/{(len(points) - 1) // batch_size + 1}")
                    break
                except Exception as e:
                    attempt += 1
                    print(f"Batch {i // batch_size + 1} failed (attempt {attempt}/3): {e}")
                    time.sleep(3)
            else:
                print(f"Skipping batch {i // batch_size + 1} after 3 failed attempts.")

        print(f"Finished indexing {len(points)} movies successfully to Qdrant Cloud.")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform semantic search on Qdrant Cloud for a given query string.
        Returns a list of payload dicts.
        """
        query_vec = self.model.encode(query).tolist()
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vec,
            limit=top_k,
        )

        # --- FIX 2: RETURN FULL PAYLOAD ---
        return [
            {
                "title": r.payload.get("title"),
                "genre": r.payload.get("genre"),
                "director": r.payload.get("director"), # <-- Add this
                "year": r.payload.get("year"),         # <-- Add this
                "score": float(r.score),
            }
            for r in results
        ]
        # --- END FIX 2 ---