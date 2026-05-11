import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter
from database import get_conn, cached_query

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _build_recommendations(uid: str, item_type: str, items: list, tag_fields: list) -> list:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT item_id FROM likes WHERE user_uid=%s AND item_type=%s", (uid, item_type))
    liked_ids = {r["item_id"] for r in cur.fetchall()}
    cur.close(); conn.close()

    if not liked_ids:
        return []

    # Build vocabulary: tag → index
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
    idx_to_tag = {v: k for k, v in vocab.items()}

    # User taste vector: dimension = tag, value = how many liked items have that tag
    user_vec = np.zeros(n)
    for item in items:
        if item["id"] not in liked_ids:
            continue
        for field in tag_fields:
            for tag in (item.get(field) or []):
                user_vec[vocab[tag.lower()]] += 1.0

    if not user_vec.any():
        return []

    # Candidate items (not yet liked)
    candidates = [item for item in items if item["id"] not in liked_ids]
    if not candidates:
        return []

    # Item matrix: one row per candidate, binary tag presence
    item_matrix = np.zeros((len(candidates), n))
    for i, item in enumerate(candidates):
        for field in tag_fields:
            for tag in (item.get(field) or []):
                item_matrix[i, vocab[tag.lower()]] = 1.0

    # Cosine similarity: user vector vs all candidates
    scores = cosine_similarity(user_vec.reshape(1, -1), item_matrix)[0]

    top_indices = np.argsort(scores)[::-1]
    results = []
    for idx in top_indices:
        if scores[idx] <= 0 or len(results) >= 24:
            break

        item = candidates[idx]

        # Matched tags: intersection of user taste and item tags, sorted by user weight
        item_tag_indices = {
            vocab[tag.lower()]
            for field in tag_fields
            for tag in (item.get(field) or [])
            if tag.lower() in vocab
        }
        matched = sorted(
            [i for i in item_tag_indices if user_vec[i] > 0],
            key=lambda i: -user_vec[i]
        )[:3]
        matched_tags = [idx_to_tag[i].title() for i in matched]

        result = dict(item)
        result["_score"] = round(float(scores[idx]) * 100)
        result["_matched_tags"] = matched_tags
        results.append(result)

    return results


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
