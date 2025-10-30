import requests
import logging
from typing import List, Dict, Optional
from backend.core.config import TMDB_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

class TMDBService:
    def __init__(self):
        self.api_key = TMDB_API_KEY
        self.base_url = "https://api.themoviedb.org/3"
        self.poster_base_url = "https://image.tmdb.org/t/p/w500"
        self.imdb_base_url = "https://www.imdb.com/title/"

        if not self.api_key:
            logger.warning("TMDB_API_KEY is not set. Movie details will not be enriched.")

    def _search_movie(self, title: str, year: Optional[str]) -> Optional[Dict]:
        """Search TMDB for a movie and return the best match."""
        if not self.api_key:
            return None
        
        try:
            search_url = f"{self.base_url}/search/movie"
            params = {
                "api_key": self.api_key,
                "query": title,
            }
            # Use the year to find a better match, if we have it
            if year:
                params["year"] = str(year).split(".")[0] # Handle floats like 2005.0

            response = requests.get(search_url, params=params)
            response.raise_for_status() # Raise an error for bad responses
            
            data = response.json()
            if data.get("results"):
                # The first result is usually the best match
                return data["results"][0]
        except Exception as e:
            logger.error(f"Error searching TMDB for '{title}': {e}")
        
        return None

    def _get_imdb_id(self, tmdb_id: int) -> Optional[str]:
        """Get the IMDB ID from the TMDB 'details' endpoint."""
        if not self.api_key or not tmdb_id:
            return None
        
        try:
            details_url = f"{self.base_url}/movie/{tmdb_id}"
            params = {"api_key": self.api_key}
            response = requests.get(details_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("imdb_id")
        except Exception as e:
            logger.error(f"Error getting IMDB ID for TMDB ID {tmdb_id}: {e}")
        
        return None

    def enrich_movies(self, movies: List[Dict]) -> List[Dict]:
        """
        Takes a list of movie dicts and adds poster_url and imdb_url.
        """
        if not self.api_key:
            return movies

        enriched_movies = []
        for movie in movies:
            tmdb_data = self._search_movie(movie.get("title"), movie.get("year"))
            
            if tmdb_data:
                # 1. Add Poster URL
                poster_path = tmdb_data.get("poster_path")
                if poster_path:
                    movie["poster_url"] = f"{self.poster_base_url}{poster_path}"
                else:
                    movie["poster_url"] = None # No poster found
                
                # 2. Get and Add IMDB URL
                tmdb_id = tmdb_data.get("id")
                imdb_id = self._get_imdb_id(tmdb_id)
                if imdb_id:
                    movie["imdb_url"] = f"{self.imdb_base_url}{imdb_id}"
                else:
                    movie["imdb_url"] = None # No IMDB ID found
            else:
                # If no TMDB match, set keys to None
                movie["poster_url"] = None
                movie["imdb_url"] = None

            enriched_movies.append(movie)
            
        return enriched_movies