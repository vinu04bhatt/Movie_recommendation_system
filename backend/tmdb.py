import os
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

if not TMDB_API_KEY:
    logger.warning("TMDB_API_KEY not found in .env - TMDB features will be disabled")

# TMDB genre mapping (Movies + TV Shows)
TMDB_GENRE_MAP = {
    # Movie genres
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    18: "Drama",
    14: "Fantasy",
    27: "Horror",
    9648: "Mystery",
    10749: "Romance",
    878: "Sci-Fi",
    53: "Thriller",
    # TV-specific genres
    10759: "Action",
    10762: "Animation",
    10763: "Drama",
    10764: "Drama",
    10765: "Sci-Fi",
    10766: "Drama",
    10767: "Comedy",
    10768: "Drama",
    37: "Drama",
}

# Fallback data for when TMDB is unavailable
FALLBACK_MOVIES = [
    {"title": "The Shawshank Redemption", "release_date": "1994-09-23", "popularity": 89.5, "genre_ids": [18, 80]},
    {"title": "The Godfather", "release_date": "1972-03-14", "popularity": 92.3, "genre_ids": [18, 80]},
    {"title": "The Dark Knight", "release_date": "2008-07-18", "popularity": 95.1, "genre_ids": [28, 80, 18]},
    {"title": "Inception", "release_date": "2010-07-16", "popularity": 88.7, "genre_ids": [28, 878, 53]},
    {"title": "Pulp Fiction", "release_date": "1994-10-14", "popularity": 87.2, "genre_ids": [80, 53]},
    {"title": "Forrest Gump", "release_date": "1994-07-06", "popularity": 86.1, "genre_ids": [35, 18, 10749]},
    {"title": "The Matrix", "release_date": "1999-03-31", "popularity": 90.3, "genre_ids": [28, 878]},
    {"title": "Interstellar", "release_date": "2014-11-07", "popularity": 91.8, "genre_ids": [12, 18, 878]},
    {"title": "Parasite", "release_date": "2019-05-30", "popularity": 88.9, "genre_ids": [35, 53, 18]},
    {"title": "Spirited Away", "release_date": "2001-07-20", "popularity": 87.5, "genre_ids": [16, 14]},
]

FALLBACK_TV = [
    {"name": "Breaking Bad", "first_air_date": "2008-01-20", "popularity": 91.4, "genre_ids": [18, 80]},
    {"name": "Game of Thrones", "first_air_date": "2011-04-17", "popularity": 89.8, "genre_ids": [10765, 18, 10759]},
    {"name": "Stranger Things", "first_air_date": "2016-07-15", "popularity": 93.2, "genre_ids": [10765, 9648, 18]},
    {"name": "The Office", "first_air_date": "2005-03-24", "popularity": 86.5, "genre_ids": [35]},
    {"name": "The Crown", "first_air_date": "2016-11-04", "popularity": 84.3, "genre_ids": [18]},
    {"name": "Friends", "first_air_date": "1994-09-22", "popularity": 92.7, "genre_ids": [35]},
    {"name": "Sherlock", "first_air_date": "2010-07-25", "popularity": 88.2, "genre_ids": [80, 18, 9648]},
    {"name": "The Mandalorian", "first_air_date": "2019-11-12", "popularity": 90.5, "genre_ids": [10765, 10759]},
    {"name": "Ted Lasso", "first_air_date": "2020-08-14", "popularity": 87.9, "genre_ids": [35, 18]},
    {"name": "Dark", "first_air_date": "2017-12-01", "popularity": 85.6, "genre_ids": [18, 9648, 10765]},
]

# Configure session with retry strategy
def create_session() -> requests.Session:
    """Create a requests session with retry logic and timeouts"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=1,  # Reduced from 2 to 1 for faster failure
        backoff_factor=0.3,  # Reduced from 0.5 to 0.3
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

# Global session instance (singleton pattern)
_session = None

def get_session() -> requests.Session:
    """Get or create global session (singleton)"""
    global _session
    if _session is None:
        _session = create_session()
    return _session

def fetch_trending(media_type: str, timeout: int = 3) -> List[Dict]:
    """
    Fetch trending movies or TV shows from TMDB.
    
    Args:
        media_type: 'movie' or 'tv'
        timeout: Request timeout in seconds (reduced from 5 to 3)
    
    Returns:
        List of trending items, or fallback data if TMDB fails
    """
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY missing - returning fallback data")
        return FALLBACK_MOVIES if media_type == "movie" else FALLBACK_TV
    
    url = f"{BASE_URL}/trending/{media_type}/week"
    session = get_session()  # Use singleton session
    
    try:
        response = session.get(
            url,
            params={"api_key": TMDB_API_KEY},
            timeout=timeout
        )
        response.raise_for_status()
        
        results = response.json().get("results", [])
        logger.info(f"Successfully fetched {len(results)} trending {media_type}s from TMDB")
        return results
        
    except requests.exceptions.Timeout:
        logger.error(f"TMDB API timeout for {media_type} - using fallback data")
        return FALLBACK_MOVIES if media_type == "movie" else FALLBACK_TV
        
    except requests.exceptions.RequestException as e:
        logger.error(f"TMDB API error for {media_type}: {e} - using fallback data")
        return FALLBACK_MOVIES if media_type == "movie" else FALLBACK_TV
        
    except Exception as e:
        logger.error(f"Unexpected error fetching {media_type}: {e} - using fallback data")
        return FALLBACK_MOVIES if media_type == "movie" else FALLBACK_TV

def search_movie(movie_title: str, timeout: int = 3) -> Optional[Dict]:
    """
    Search for a movie by title and return its details.
    
    Args:
        movie_title: Movie title to search
        timeout: Request timeout in seconds (reduced from 5 to 3)
    
    Returns:
        Movie details dict or None if not found/error
    """
    if not TMDB_API_KEY or not movie_title:
        return None
    
    search_url = f"{BASE_URL}/search/movie"
    session = get_session()  # Use singleton session
    
    try:
        response = session.get(
            search_url,
            params={'api_key': TMDB_API_KEY, 'query': movie_title},
            timeout=timeout
        )
        response.raise_for_status()
        
        results = response.json().get('results', [])
        if not results:
            logger.info(f"No results found for movie: {movie_title}")
            return None
        
        # Get detailed info for first result
        movie_id = results[0]['id']
        detail_url = f"{BASE_URL}/movie/{movie_id}"
        
        detail_response = session.get(
            detail_url,
            params={'api_key': TMDB_API_KEY},
            timeout=timeout
        )
        detail_response.raise_for_status()
        
        logger.info(f"Successfully found movie: {movie_title}")
        return detail_response.json()
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout searching for movie: {movie_title}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error searching for movie '{movie_title}': {e}")
        return None
        
    except Exception as e:
        logger.warning(f"Unexpected error searching for movie '{movie_title}': {e}")
        return None

def build_genre_vector(item: Dict, genre_index: Dict) -> List[int]:
    """
    Convert TMDB item to genre vector.
    
    Args:
        item: TMDB movie/tv item
        genre_index: Genre name to index mapping
    
    Returns:
        Binary genre vector
    """
    vec = [0] * len(genre_index)
    
    for gid in item.get("genre_ids", []):
        genre = TMDB_GENRE_MAP.get(gid)
        if genre and genre in genre_index:
            vec[genre_index[genre]] = 1
    
    return vec