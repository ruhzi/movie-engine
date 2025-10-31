# backend/main.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict

# Import your REAL recommender
# FIX: Corrected import path to include 'backend.'
from backend.core.recommender import Recommender

# Initialize FastAPI
app = FastAPI(title="Movie Recommendation API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Use FastAPI Lifespan for connections ---
# This dict will hold our shared recommender instance
app_state = {}

@app.on_event("startup")
def startup_event():
    """On API startup, initialize the recommender."""
    print("Initializing recommender...")
    # Simplified: No args needed, it reads from config
    recommender = Recommender()
    app_state["recommender"] = recommender
    print("Recommender initialized.")

@app.on_event("shutdown")
def shutdown_event():
    """On API shutdown, close the Neo4j connection."""
    print("Closing connections...")
    if "recommender" in app_state:
        app_state["recommender"].close() # Call the close() method
    print("Connections closed.")
# --- End Lifespan ---


@app.get("/")
async def root():
    """Root endpoint for health checks."""
    return {"message": "Movie Recommendation API is running!"}


# --- THIS IS THE NEW ENDPOINT YOU'RE ADDING ---
@app.get("/trending", response_model=List[Dict])
async def get_trending_movies():
    """
    Get daily trending movies, pre-enriched with TMDB data.
    """
    recommender = app_state.get("recommender")
    if not recommender:
        raise HTTPException(status_code=503, detail="Recommender is not initialized")
    
    # We re-use the tmdb_service from our recommender
    # (The Recommender class initializes tmdb_service as self.tmdb)
    results = recommender.tmdb.get_trending_movies(limit=6)
    return results
# --- END OF NEW ENDPOINT ---


@app.get("/recommend", response_model=List[Dict])
async def recommend_movies(
    query: str = Query(..., description="Describe the movie or theme"),
    # FIX: Synced default limit to 4
    vector_limit: int = Query(4, description="Num vector results"),
    graph_limit: int = Query(4, description="Num graph expansion results")
):
    """
    Example: /recommend?query=sci-fi+movie+about+AI+rebellion
    """
    recommender = app_state.get("recommender")
    if not recommender:
        # Service Unavailable
        raise HTTPException(status_code=503, detail="Recommender is not initialized")

    results = recommender.recommend(
        query=query, 
        vector_limit=vector_limit, 
        graph_limit=graph_limit
    )
    return results