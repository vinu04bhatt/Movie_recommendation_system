import numpy as np
import xgboost as xgb

from rules import build_rule_preference_vector
from tmdb import fetch_trending, build_genre_vector

# Try to import search_movie, but make it optional
try:
    from tmdb import search_movie
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False
    print("⚠️ search_movie not available - favorite movie feature disabled")
from utils import rank_items

# --------------------------------------------------
# Questionnaire (CLI input)
# --------------------------------------------------
def get_user_inputs():
    print("\n🎬 Movie Recommendation Questionnaire\n")

    fav_movie = input(
        "1️⃣ Enter your favorite movie (any language / era): "
    ).strip()

    fav_genres = input(
        "2️⃣ Enter your favorite genres (comma-separated, e.g. Sci-Fi, Thriller): "
    ).split(",")

    fav_genres = [g.strip().title() for g in fav_genres if g.strip()]

    mood = input(
        "3️⃣ What is your current mood? (happy / excited / romantic / sad / scared): "
    ).strip().lower()

    context = input(
        "4️⃣ Who are you watching with? (alone / friends / partner / family): "
    ).strip().lower()

    popularity = input(
        "5️⃣ Do you prefer popular or underrated content? (popular / underrated / mix): "
    ).strip().lower()

    return {
        "favorite_movie": fav_movie,
        "favorite_genres": fav_genres,
        "current_mood": mood,
        "watching_context": context,
        "popularity_bias": popularity,
    }

# --------------------------------------------------
# Extract genres from favorite movie
# --------------------------------------------------
def get_movie_genres(movie_title):
    """
    Search for the movie on TMDb and extract its genres.
    Returns a list of genre names.
    """
    if not SEARCH_AVAILABLE:
        return []
    
    try:
        movie_data = search_movie(movie_title)
        if movie_data and 'genres' in movie_data:
            return [genre['name'] for genre in movie_data['genres']]
        return []
    except Exception as e:
        print(f"⚠️ Could not fetch genres for '{movie_title}': {e}")
        return []

# --------------------------------------------------
# Apply popularity filter
# --------------------------------------------------
def apply_popularity_filter(ranked_items, popularity_bias):
    """
    Filter items based on popularity preference.
    """
    if popularity_bias == "popular":
        # Keep items with popularity > 100 (popular)
        return [(score, item) for score, item in ranked_items if item.get('popularity', 0) > 100]
    elif popularity_bias == "underrated":
        # Keep items with popularity < 100 (underrated)
        return [(score, item) for score, item in ranked_items if item.get('popularity', 0) < 100]
    else:  # mix
        return ranked_items

# --------------------------------------------------
# Main execution
# --------------------------------------------------
if __name__ == "__main__":

    # Load trained XGBoost model
    model = xgb.XGBRegressor()
    model.load_model("model/xgb_model.json")

    # Take user input
    user_input = get_user_inputs()

    # --------------------------------------------------
    # Extract genres from favorite movie (if provided)
    # --------------------------------------------------
    fav_movie_genres = []
    if user_input["favorite_movie"]:
        print(f"\n🔍 Analyzing your favorite movie: {user_input['favorite_movie']}...")
        fav_movie_genres = get_movie_genres(user_input["favorite_movie"])
        if fav_movie_genres:
            print(f"✅ Found genres: {', '.join(fav_movie_genres)}")
        else:
            print("⚠️ Could not find movie or extract genres. Using your genre preferences instead.")

    # Combine favorite movie genres with user-provided genres
    all_favorite_genres = list(set(fav_movie_genres + user_input["favorite_genres"]))

    # --------------------------------------------------
    # DEBUG: Show collected input
    # --------------------------------------------------
    print("\n" + "="*60)
    print("🔍 DEBUG - YOUR INPUT SUMMARY")
    print("="*60)
    print(f"Favorite Movie: {user_input['favorite_movie']}")
    print(f"Movie Genres Found: {fav_movie_genres if fav_movie_genres else 'None'}")
    print(f"Your Genre Preferences: {user_input['favorite_genres']}")
    print(f"Combined Genres: {all_favorite_genres}")
    print(f"Mood: {user_input['current_mood']}")
    print(f"Context: {user_input['watching_context']}")
    print(f"Popularity Preference: {user_input['popularity_bias']}")
    print("="*60 + "\n")

    # --------------------------------------------------
    # Build RULE-based preference vector
    # --------------------------------------------------
    rule_vec = build_rule_preference_vector(
        favorite_movie_genres=fav_movie_genres if fav_movie_genres else all_favorite_genres,
        favorite_genres=all_favorite_genres,
        watching_context=user_input["watching_context"],
        current_mood=user_input["current_mood"],
    )

    rule_vec = np.array(rule_vec)

    # --------------------------------------------------
    # DEBUG: Show rule vector
    # --------------------------------------------------
    print("🔍 DEBUG - RULE-BASED PREFERENCE VECTOR")
    print(f"Vector: {rule_vec}")
    print(f"Shape: {rule_vec.shape}\n")

    # --------------------------------------------------
    # ML-based correction (XGBoost)
    # --------------------------------------------------
    ml_vec = model.predict(rule_vec.reshape(1, -1))[0]

    # --------------------------------------------------
    # DEBUG: Show ML vector
    # --------------------------------------------------
    print("🔍 DEBUG - ML-PREDICTED VECTOR")
    print(f"Vector: {ml_vec}")
    print(f"Shape: {ml_vec.shape}\n")

    # --------------------------------------------------
    # Hybrid preference vector
    # --------------------------------------------------
    # Check if user has strong genre preferences (romantic mood + partner context)
    strong_preference_contexts = {
        ("romantic", "partner"): ["Romance", "Drama"],
        ("scared", "alone"): ["Horror", "Thriller"],
        ("excited", "friends"): ["Action", "Comedy", "Adventure"]
    }
    
    # Normalize context input (handle typos like "friendas" -> "friends")
    normalized_context = user_input["watching_context"].lower().strip()
    if "friend" in normalized_context:
        normalized_context = "friends"
    elif "partner" in normalized_context or "spouse" in normalized_context:
        normalized_context = "partner"
    elif "family" in normalized_context or "famil" in normalized_context:
        normalized_context = "family"
    elif "alone" in normalized_context or "solo" in normalized_context:
        normalized_context = "alone"
    
    context_key = (user_input["current_mood"].lower().strip(), normalized_context)
    
    if context_key in strong_preference_contexts:
        # Use rules-only for strong preferences
        alpha = 1.0  # 100% rules
        beta = 0.0   # 0% ML
        print(f"\n🎯 RULES-ONLY MODE ACTIVATED for {context_key}")
        print(f"   Focusing on: {', '.join(strong_preference_contexts[context_key])}\n")
    else:
        # Use hybrid for other cases
        alpha = 0.85  # rules weight
        beta = 0.15   # ML weight
        print(f"\n🎯 HYBRID MODE for {context_key}\n")

    final_pref = alpha * rule_vec + beta * ml_vec

    # --------------------------------------------------
    # DEBUG: Show final vector
    # --------------------------------------------------
    print("🔍 DEBUG - FINAL HYBRID PREFERENCE VECTOR")
    print(f"Vector: {final_pref}")
    print(f"Formula: {alpha} * rule_vec + {beta} * ml_vec\n")

    # --------------------------------------------------
    # Genre index (shared)
    # --------------------------------------------------
    GENRE_INDEX = {
        "Action": 0,
        "Adventure": 1,
        "Animation": 2,
        "Comedy": 3,
        "Crime": 4,
        "Drama": 5,
        "Fantasy": 6,
        "Horror": 7,
        "Mystery": 8,
        "Romance": 9,
        "Sci-Fi": 10,
        "Thriller": 11,
    }

    # --------------------------------------------------
    # Fetch trending content
    # --------------------------------------------------
    print("📡 Fetching trending movies and TV shows...\n")
    
    try:
        movies = fetch_trending("movie")
        tv_shows = fetch_trending("tv")
        
        # DEBUG: Check TV show genres
        print("🔍 DEBUG - SAMPLE TV SHOW GENRES")
        from tmdb import TMDB_GENRE_MAP
        for show in tv_shows[:3]:
            genre_ids = show.get('genre_ids', [])
            genre_names = [TMDB_GENRE_MAP.get(gid, f"Unknown-{gid}") for gid in genre_ids]
            print(f"   {show.get('name')}: {genre_names}")
        print()
        
    except Exception as e:
        print(f"❌ Error fetching trending content: {e}")
        print("Please check your internet connection and TMDb API status.")
        exit(1)

    # --------------------------------------------------
    # Rank items with diversity boost
    # --------------------------------------------------
    ranked_movies = rank_items(
        movies, final_pref, GENRE_INDEX, build_genre_vector
    )

    ranked_tv = rank_items(
        tv_shows, final_pref, GENRE_INDEX, build_genre_vector
    )
    
    # Apply diversity filter - reduce score for items with similar genres to already selected ones
    def diversify_results(ranked_items, top_n=20):
        """Select diverse items from top_n candidates"""
        if len(ranked_items) <= top_n:
            return ranked_items
        
        selected = []
        candidates = ranked_items[:top_n]  # Only consider top N
        
        for score, item in candidates:
            if not selected:
                selected.append((score, item))
                continue
            
            # Check genre overlap with already selected items
            item_genres = set(item.get('genre_ids', []))
            
            # Calculate average genre overlap with selected items
            overlap_scores = []
            for _, selected_item in selected:
                selected_genres = set(selected_item.get('genre_ids', []))
                if item_genres and selected_genres:
                    overlap = len(item_genres & selected_genres) / len(item_genres | selected_genres)
                    overlap_scores.append(overlap)
            
            avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0
            
            # Penalize high overlap (reduce score by up to 30%)
            diversity_penalty = avg_overlap * 0.3
            adjusted_score = score * (1 - diversity_penalty)
            
            selected.append((adjusted_score, item))
        
        # Re-sort by adjusted scores
        selected.sort(key=lambda x: x[0], reverse=True)
        return selected
    
    # Apply diversity
    ranked_movies = diversify_results(ranked_movies, top_n=30)
    ranked_tv = diversify_results(ranked_tv, top_n=30)

    # --------------------------------------------------
    # DEBUG: Show rankings before filter
    # --------------------------------------------------
    print("🔍 DEBUG - TOP 10 MOVIES (AFTER DIVERSITY, BEFORE POPULARITY FILTER)")
    for i, (score, movie) in enumerate(ranked_movies[:10], 1):
        popularity = movie.get('popularity', 0)
        genre_ids = movie.get('genre_ids', [])
        from tmdb import TMDB_GENRE_MAP
        genres = [TMDB_GENRE_MAP.get(gid, '') for gid in genre_ids]
        print(f"{i}. {movie.get('title')} - Score: {score:.3f}, Pop: {popularity:.1f}, Genres: {genres}")
    print()
    
    print("🔍 DEBUG - TOP 10 TV SHOWS (AFTER DIVERSITY, BEFORE POPULARITY FILTER)")
    for i, (score, show) in enumerate(ranked_tv[:10], 1):
        popularity = show.get('popularity', 0)
        genre_ids = show.get('genre_ids', [])
        genres = [TMDB_GENRE_MAP.get(gid, '') for gid in genre_ids]
        print(f"{i}. {show.get('name')} - Score: {score:.3f}, Pop: {popularity:.1f}, Genres: {genres}")
    print()

    # --------------------------------------------------
    # Apply popularity filter
    # --------------------------------------------------
    ranked_movies = apply_popularity_filter(ranked_movies, user_input["popularity_bias"])
    ranked_tv = apply_popularity_filter(ranked_tv, user_input["popularity_bias"])

    # --------------------------------------------------
    # SMART GENRE FILTER for strong preferences
    # --------------------------------------------------
    if context_key in strong_preference_contexts:
        print(f"\n🎯 APPLYING SMART GENRE FILTER")
        
        # Define what genres are PREFERRED and BANNED for this context
        if context_key == ("romantic", "partner"):
            preferred_genres = ["Romance", "Drama", "Comedy"]
            banned_genre_names = ["Horror", "Thriller"]  # Only ban truly incompatible
            min_score_threshold = 0.15  # Lower threshold for romantic
        elif context_key == ("scared", "alone"):
            preferred_genres = ["Horror", "Thriller", "Mystery"]
            banned_genre_names = ["Comedy", "Animation", "Romance"]
            min_score_threshold = 0.05  # Very low threshold - accept most dark content
        elif context_key == ("excited", "friends"):
            preferred_genres = ["Action", "Comedy", "Adventure", "Thriller"]
            banned_genre_names = []
            min_score_threshold = 0.20
        else:
            preferred_genres = []
            banned_genre_names = []
            min_score_threshold = 0.0
        
        # Convert banned genre names to IDs
        from tmdb import TMDB_GENRE_MAP
        banned_genre_ids = [gid for gid, name in TMDB_GENRE_MAP.items() if name in banned_genre_names]
        
        # Filter movies with flexible matching
        filtered_movies = []
        for score, movie in ranked_movies:
            movie_genre_ids = set(movie.get('genre_ids', []))
            movie_genres = [TMDB_GENRE_MAP.get(gid, '') for gid in movie_genre_ids]
            
            # Check if has ANY preferred genre (flexible)
            has_preferred = any(g in preferred_genres for g in movie_genres)
            
            # Check if has banned genre
            has_banned = any(gid in banned_genre_ids for gid in movie_genre_ids)
            
            # Accept if: (has preferred OR score is decent) AND not banned
            if (has_preferred or score >= min_score_threshold) and not has_banned:
                filtered_movies.append((score, movie))
        
        # Filter TV shows similarly
        filtered_tv = []
        for score, show in ranked_tv:
            show_genre_ids = set(show.get('genre_ids', []))
            show_genres = [TMDB_GENRE_MAP.get(gid, '') for gid in show_genre_ids]
            
            has_preferred = any(g in preferred_genres for g in show_genres)
            has_banned = any(gid in banned_genre_ids for gid in show_genre_ids)
            
            if (has_preferred or score >= min_score_threshold) and not has_banned:
                filtered_tv.append((score, show))
        
        print(f"   Movies: {len(ranked_movies)} -> {len(filtered_movies)} (after filtering)")
        print(f"   TV Shows: {len(ranked_tv)} -> {len(filtered_tv)} (after filtering)")
        
        # If we filtered out too much, relax the filter
        if len(filtered_movies) < 5:
            print(f"   ⚠️ Too few movies ({len(filtered_movies)}), relaxing filter...")
            filtered_movies = [(s, m) for s, m in ranked_movies if not any(gid in banned_genre_ids for gid in m.get('genre_ids', []))][:15]
        
        if len(filtered_tv) < 5:
            print(f"   ⚠️ Too few TV shows ({len(filtered_tv)}), relaxing filter...")
            filtered_tv = [(s, t) for s, t in ranked_tv if not any(gid in banned_genre_ids for gid in t.get('genre_ids', []))][:15]
        
        print(f"   Final: {len(filtered_movies)} movies, {len(filtered_tv)} TV shows\n")
        
        ranked_movies = filtered_movies
        ranked_tv = filtered_tv

    # Take top 5
    ranked_movies = ranked_movies[:5]
    ranked_tv = ranked_tv[:5]

    # --------------------------------------------------
    # Output Final Recommendations
    # --------------------------------------------------
    print("\n" + "="*60)
    print("🎬 YOUR PERSONALIZED RECOMMENDATIONS")
    print("="*60 + "\n")

    print("🎬 TOP 5 MOVIE RECOMMENDATIONS")
    if ranked_movies:
        for i, (score, movie) in enumerate(ranked_movies, 1):
            title = movie.get('title', 'Unknown')
            year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A'
            popularity = movie.get('popularity', 0)
            print(f"{i}. {title} ({year}) - Match Score: {score:.3f}, Popularity: {popularity:.1f}")
    else:
        print("   No movies found matching your criteria. Try 'mix' for popularity.")

    print("\n📺 TOP 5 TV SERIES RECOMMENDATIONS")
    if ranked_tv:
        for i, (score, show) in enumerate(ranked_tv, 1):
            name = show.get('name', 'Unknown')
            year = show.get('first_air_date', '')[:4] if show.get('first_air_date') else 'N/A'
            popularity = show.get('popularity', 0)
            print(f"{i}. {name} ({year}) - Match Score: {score:.3f}, Popularity: {popularity:.1f}")
    else:
        print("   No TV shows found matching your criteria. Try 'mix' for popularity.")

    print("\n" + "="*60)
    print("✨ Enjoy your viewing! ✨")
    print("="*60 + "\n")