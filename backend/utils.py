import numpy as np

def normalize(v):
    return v / v.sum() if v.sum() > 0 else v

def rank_items(items, preference_vector, genre_index, vector_builder):
    scored = []
    for item in items:
        vec = vector_builder(item, genre_index)
        score = np.dot(preference_vector, vec)
        scored.append((score, item))

    # Sort ONLY by score (avoid dict comparison error)
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
