import numpy as np

GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Drama", "Fantasy", "Horror", "Mystery", "Romance",
    "Sci-Fi", "Thriller"
]

GENRE_INDEX = {g: i for i, g in enumerate(GENRES)}

def _normalize(v):
    return v / v.sum() if v.sum() > 0 else v

def build_rule_preference_vector(
    favorite_movie_genres,
    favorite_genres,
    watching_context,
    current_mood
):
    vec = np.zeros(len(GENRES), dtype=float)

    # 1. Favorite movie (strong signal)
    for g in favorite_movie_genres:
        if g in GENRE_INDEX:
            vec[GENRE_INDEX[g]] += 0.50

    # 2. Favorite genres (strong signal)
    for g in favorite_genres:
        if g in GENRE_INDEX:
            vec[GENRE_INDEX[g]] += 0.50

    # 3. Watching context (BOOSTED - this is important!)
    context_map = {
        "friends": {
            "Comedy": 0.40,
            "Action": 0.35,
            "Adventure": 0.25
        },
        "partner": {
            "Romance": 0.60,  # INCREASED from 0.15
            "Drama": 0.40     # INCREASED from 0.15
        },
        "family": {
            "Animation": 0.45,
            "Comedy": 0.35,
            "Adventure": 0.25
        },
        "alone": {
            "Drama": 0.30,
            "Thriller": 0.25,
            "Mystery": 0.20
        }
    }
    
    context_boosts = context_map.get(watching_context, {})
    for g, weight in context_boosts.items():
        vec[GENRE_INDEX[g]] += weight

    # 4. Mood (BOOSTED - mood is critical!)
    mood_map = {
        "happy": {
            "Comedy": 0.50,
            "Romance": 0.30,
            "Adventure": 0.20
        },
        "excited": {
            "Action": 0.50,
            "Thriller": 0.40,
            "Adventure": 0.30
        },
        "romantic": {
            "Romance": 0.70,  # INCREASED from 0.10
            "Drama": 0.40     # Added Drama for romantic mood
        },
        "sad": {
            "Drama": 0.50,
            "Romance": 0.30
        },
        "scared": {
            "Horror": 0.60,
            "Thriller": 0.40
        },
        "relaxed": {
            "Drama": 0.40,
            "Comedy": 0.30
        }
    }
    
    mood_boosts = mood_map.get(current_mood, {})
    for g, weight in mood_boosts.items():
        vec[GENRE_INDEX[g]] += weight

    # 5. PENALTY for mismatched genres (NEW!)
    # If watching with partner in romantic mood, penalize action/horror/thriller
    if watching_context == "partner" and current_mood == "romantic":
        penalty_genres = ["Action", "Horror", "Thriller", "Sci-Fi"]
        for g in penalty_genres:
            vec[GENRE_INDEX[g]] *= 0.2  # Reduce by 80%
    
    # If scared/alone, penalize light content
    if current_mood == "scared" and watching_context == "alone":
        penalty_genres = ["Comedy", "Romance", "Animation"]
        for g in penalty_genres:
            vec[GENRE_INDEX[g]] *= 0.2
    
    # If with friends and excited, penalize slow/dramatic content
    if watching_context == "friends" and current_mood == "excited":
        penalty_genres = ["Drama", "Romance"]
        for g in penalty_genres:
            vec[GENRE_INDEX[g]] *= 0.3

    return _normalize(vec)