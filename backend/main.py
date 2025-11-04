# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.semantic_search import SemanticSearch
from core.config import DATA_DIR

app = FastAPI(
    title="Movie Recommendation API",
    description="Backend API for the Movie Engine project",
    version="1.0.0"
)

# --- CORS CONFIG ---
# Only allow your deployed frontend domain to make API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://movie-engine-klnvsj1hw-ruhzis-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---
@app.get("/")
def root():
    return {"message": "Movie Engine backend is running!"}


@app.get("/recommend")
def recommend(query: str):
    ss = SemanticSearch()
    results = ss.search(query)
    return {"query": query, "results": results}


# --- LOCAL TEST ENTRYPOINT ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
