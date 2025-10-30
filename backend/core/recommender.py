from neo4j import GraphDatabase
# FIX: Use relative import '.'
from .config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
)
# 1. IMPORT YOUR SEMANTIC SEARCH CLASS
# FIX: Use relative import '.'
from .semantic_search import SemanticSearch
# --- 1. IMPORT THE NEW TMDB SERVICE ---
from .tmdb_service import TMDBService
from typing import List, Dict, Set
import logging

# Optional: Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Recommender:
    def __init__(self):
        """
        Hybrid Recommender:
        1. Semantic search via SemanticSearch class (Qdrant)
        2. Knowledge graph expansion via Neo4j
        3. Real-time enrichment via TMDBService
        """
        # This one class handles all Qdrant/model logic
        self.semantic_search = SemanticSearch() 
        
        # This class handles all Neo4j logic
        self.neo4j = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        # --- 2. INITIALIZE THE TMDB SERVICE ---
        self.tmdb = TMDBService()

    def close(self):
        """Close Neo4j driver."""
        if self.neo4j:
            self.neo4j.close()

    def _search_qdrant(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Perform vector search by delegating to the SemanticSearch class.
        """
        search_results = self.semantic_search.search(query, top_k=limit)
        
        # Re-format the results slightly for the recommender
        return [
            {
                "title": hit.get("title"),
                "genre": hit.get("genre"),
                "director": hit.get("director"),
                "year": hit.get("year"),
                "score": round(float(hit["score"]), 4),
                "source": "vector"
            }
            for hit in search_results
        ]

    def _expand_via_neo4j(self, movie_title: str, limit: int = 5) -> List[Dict]:
        """
        Expand using Neo4j knowledge graph.
        """
        query = """
        MATCH (m:Movie {title: $title})
        
        CALL {
            WITH m
            OPTIONAL MATCH (m)-[:DIRECTED_BY]->(dir:Director)<-[:DIRECTED_BY]-(r:Movie)
            WHERE r <> m
            RETURN r
        }
        UNION
        CALL {
            WITH m
            OPTIONAL MATCH (m)<-[:ACTED_IN]-(actor:Actor)-[:ACTED_IN]->(r:Movie)
            WHERE r <> m
            RETURN r
        }
        UNION
        CALL {
            WITH m
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(genre:Genre)<-[:HAS_GENRE]-(r:Movie)
            WHERE r <> m
            RETURN r
        }

        WITH r WHERE r IS NOT NULL
        RETURN DISTINCT
            r.title AS title,
            r.genre AS genre,
            r.release_year AS year
        LIMIT $limit
        """

        try:
            with self.neo4j.session() as session:
                result = session.run(query, title=movie_title, limit=limit)
                return [
                    {
                        "title": rec["title"],
                        "genre": rec["genre"],
                        "year": rec["year"],
                        "score": None,
                        "source": "graph"
                    }
                    for rec in result
                ]
        except Exception as e:
            logger.warning(f"Neo4j expansion failed for '{movie_title}': {e}")
            return []

    def recommend(self, query: str, vector_limit: int = 4, graph_limit: int = 4) -> List[Dict]:
        """
        Hybrid recommendation pipeline:
        1. Get top `vector_limit` semantically similar movies.
        2. For EACH of those movies, find `graph_limit` related movies.
        3. Deduplicate the combined list.
        4. Enrich the final list with TMDB data (posters, IMDB links).
        """
        
        # Step 1: Vector search (Get the initial 4 movies)
        vector_results = self._search_qdrant(query, limit=vector_limit)
        if not vector_results:
            logger.info("No vector results found.")
            return []

        # Step 2: Deduplicate and prepare for expansion
        seen_titles: Set[str] = set()
        combined: List[Dict] = []

        # Add the initial vector results to the list
        for movie in vector_results:
            # Make sure title is not None before adding
            if movie.get("title") and movie["title"] not in seen_titles:
                seen_titles.add(movie["title"])
                combined.append(movie)

        # Step 3: Expand EACH vector result via the knowledge graph
        for vector_movie in vector_results:
            primary_title = vector_movie.get("title")
            if not primary_title:
                continue

            logger.info(f"Expanding recommendations for: {primary_title}")
            
            graph_results = self._expand_via_neo4j(primary_title, limit=graph_limit)

            # Append new graph results (avoiding duplicates)
            for movie in graph_results:
                if movie.get("title") and movie["title"] not in seen_titles:
                    seen_titles.add(movie["title"])
                    combined.append(movie)

        # --- 3. ADD THE FINAL ENRICHMENT STEP ---
        logger.info(f"Enriching {len(combined)} recommendations with TMDB data...")
        enriched_results = self.tmdb.enrich_movies(combined)
        
        logger.info(f"Returning {len(enriched_results)} enriched recommendations.")
        return enriched_results
