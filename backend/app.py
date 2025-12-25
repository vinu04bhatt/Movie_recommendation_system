from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import numpy as np
import xgboost as xgb
import logging
import asyncio
import aiohttp
from contextlib import asynccontextmanager
import os

from rules import build_rule_preference_vector
from tmdb import TMDB_GENRE_MAP, FALLBACK_MOVIES, FALLBACK_TV, search_movie
from utils import rank_items

logging.basicConfig(level=logging.WARNING)  # Reduce verbosity
logger = logging.getLogger(__name__)

# Global model variable
ml_model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model once on startup"""
    global ml_model
    
    logger.info("Loading XGBoost model...")
    try:
        ml_model = xgb.XGBRegressor()
        ml_model.load_model("model/xgb_model.json")
        logger.info("✅ Model loaded")
    except Exception as e:
        logger.error(f"❌ Model load failed: {e}")
        ml_model = None
    
    yield
    logger.info("Shutting down")

app = FastAPI(title="CineMatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=3600,
)

GENRE_INDEX = {
    "Action": 0, "Adventure": 1, "Animation": 2, "Comedy": 3,
    "Crime": 4, "Drama": 5, "Fantasy": 6, "Horror": 7,
    "Mystery": 8, "Romance": 9, "Sci-Fi": 10, "Thriller": 11,
}

class RecommendRequest(BaseModel):
    favorite_movie: str
    favorite_genres: List[str]
    current_mood: str
    watching_context: str
    popularity_bias: str

class MediaItem(BaseModel):
    title: str
    year: str
    popularity: float

class RecommendResponse(BaseModel):
    movies: List[MediaItem]
    tv: List[MediaItem]

async def fetch_trending_async(session: aiohttp.ClientSession, media_type: str, api_key: str) -> List[dict]:
    """Async TMDB fetch with 3s timeout"""
    url = f"https://api.themoviedb.org/3/trending/{media_type}/week"
    
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with session.get(url, params={"api_key": api_key}, timeout=timeout) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("results", [])
    except Exception:
        return FALLBACK_MOVIES if media_type == "movie" else FALLBACK_TV

def build_genre_vector(item: dict, genre_index: dict) -> List[int]:
    """Convert item to genre vector"""
    vec = [0] * len(genre_index)
    for gid in item.get("genre_ids", []):
        genre = TMDB_GENRE_MAP.get(gid)
        if genre and genre in genre_index:
            vec[genre_index[genre]] = 1
    return vec

@app.get("/")
def read_root():
    return {"message": "CineMatch API"}

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """Get recommendations - optimized for speed"""
    global ml_model
    
    try:
        # Extract movie genres (with timeout)
        fav_movie_genres = []
        if request.favorite_movie:
            movie_data = search_movie(request.favorite_movie, timeout=2)  # Reduced timeout
            if movie_data and 'genres' in movie_data:
                fav_movie_genres = [g['name'] for g in movie_data['genres']]
        
        all_favorite_genres = list(set(fav_movie_genres + request.favorite_genres))
        
        # Build preference vector
        rule_vec = build_rule_preference_vector(
            favorite_movie_genres=fav_movie_genres if fav_movie_genres else all_favorite_genres,
            favorite_genres=all_favorite_genres,
            watching_context=request.watching_context,
            current_mood=request.current_mood,
        )
        
        rule_vec = np.array(rule_vec)
        
        # ML prediction
        if ml_model is not None:
            try:
                ml_vec = ml_model.predict(rule_vec.reshape(1, -1))[0]
            except:
                ml_vec = rule_vec
        else:
            ml_vec = rule_vec
        
        # Determine weights
        strong_contexts = {
            ("romantic", "partner"): True,
            ("scared", "alone"): True,
            ("excited", "friends"): True
        }
        
        normalized_context = request.watching_context.lower().strip()
        if "friend" in normalized_context:
            normalized_context = "friends"
        elif "partner" in normalized_context:
            normalized_context = "partner"
        elif "family" in normalized_context:
            normalized_context = "family"
        elif "alone" in normalized_context:
            normalized_context = "alone"
        
        context_key = (request.current_mood.lower().strip(), normalized_context)
        alpha, beta = (1.0, 0.0) if context_key in strong_contexts else (0.85, 0.15)
        
        final_pref = alpha * rule_vec + beta * ml_vec
        
        # CONCURRENT TMDB FETCH
        api_key = os.getenv("TMDB_API_KEY", "")
        async with aiohttp.ClientSession() as session:
            movies, tv_shows = await asyncio.gather(
                fetch_trending_async(session, "movie", api_key),
                fetch_trending_async(session, "tv", api_key)
            )
        
        # Rank and filter
        ranked_movies = rank_items(movies, final_pref, GENRE_INDEX, build_genre_vector)[:5]
        ranked_tv = rank_items(tv_shows, final_pref, GENRE_INDEX, build_genre_vector)[:5]
        
        # Format response
        movies_response = [
            MediaItem(
                title=m.get('title', 'Unknown'),
                year=m.get('release_date', '')[:4] if m.get('release_date') else 'N/A',
                popularity=m.get('popularity', 0)
            )
            for _, m in ranked_movies
        ]
        
        tv_response = [
            MediaItem(
                title=s.get('name', 'Unknown'),
                year=s.get('first_air_date', '')[:4] if s.get('first_air_date') else 'N/A',
                popularity=s.get('popularity', 0)
            )
            for _, s in ranked_tv
        ]
        
        return RecommendResponse(movies=movies_response, tv=tv_response)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return RecommendResponse(movies=[], tv=[])