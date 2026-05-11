import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter
from database import get_conn, cached_query

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _build_recommendations(uid: str, item_type: str, items: list, tag_fields: list) -> list:
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "SELECT item_id FROM likes WHERE user_uid=%s AND item_type=%s",
        (uid, item_type)
    )
    liked_ids = {r["item_id"] for r in cur.fetchall()}
    cur.close(); conn.close()

    if not liked_ids:
        return []

    # Build vocabulary from all items
    vocab: dict[str, int] = {}
    for item in items:
        for field in tag_fields:
            for tag in (item.get(field) or []):
                key = tag.lower()
                if key not in vocab:
                    vocab[key] = len(vocab)

    if not vocab:
        return []

    n = len(vocab)

    # User vector: sum of liked items' tag vectors (weighted by frequency)
    user_vec = np.zeros(n)
    for item in items:
        if item["id"] not in liked_ids:
            continue
        for field in tag_fields:
            for tag in (item.get(field) or []):
                user_vec[vocab[tag.lower()]] += 1.0

    if not user_vec.any():
        return []

    # Item matrix: one row per un-liked item
    candidates = [item for item in items if item["id"] not in liked_ids]
    if not candidates:
        return []

    item_matrix = np.zeros((len(candidates), n))
    for i, item in enumerate(candidates):
        for field in tag_fields:
            for tag in (item.get(field) or []):
                item_matrix[i, vocab[tag.lower()]] = 1.0

    # Cosine similarity between user vector and all candidate items
    scores = cosine_similarity(user_vec.reshape(1, -1), item_matrix)[0]

    # Sort by score descending, return top 24
    top_indices = np.argsort(scores)[::-1]
    return [candidates[i] for i in top_indices if scores[i] > 0][:24]


@router.get("/{uid}/tracks")
def recommend_tracks(uid: str):
    items = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
    return _build_recommendations(uid, "track", items, ["genres", "tags"])


@router.get("/{uid}/movies")
def recommend_movies(uid: str):
    items = cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
    return _build_recommendations(uid, "movie", items, ["genres", "keywords"])


@router.get("/{uid}/games")
def recommend_games(uid: str):
    items = cached_query("games", "SELECT * FROM games ORDER BY rating DESC")
    return _build_recommendations(uid, "game", items, ["genres", "tags"])
