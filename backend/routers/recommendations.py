import math
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter
from database import get_conn, cached_query, _cache

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _build_recommendations(uid: str, item_type: str, items: list, tag_fields: list, min_df: int = 1) -> list:

    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT item_id FROM likes WHERE user_uid=%s AND item_type=%s", (uid, item_type))
    liked_ids = {r["item_id"] for r in cur.fetchall()}
    cur.close(); conn.close()

    if not liked_ids:
        return []

    doc_freq: dict[str, int] = {}
    for item in items:
        seen: set[str] = set()
        for field in tag_fields:
            for tag in (item.get(field) or []):
                key = tag.lower()
                if key not in seen:
                    doc_freq[key] = doc_freq.get(key, 0) + 1
                    seen.add(key)

    vocab: dict[str, int] = {}
    for key, freq in doc_freq.items():
        if freq >= min_df:
            vocab[key] = len(vocab)

    if not vocab:
        return []

    n = len(vocab)
    idx_to_tag = {v: k for k, v in vocab.items()}
    N = len(items)
    idf = {tag: math.log(N / (freq + 1)) for tag, freq in doc_freq.items()}

    user_vec = np.zeros(n)
    for item in items:
        if item["id"] not in liked_ids:
            continue
        for field in tag_fields:
            for tag in (item.get(field) or []):
                key = tag.lower()
                if key in vocab:
                    user_vec[vocab[key]] += idf[key]

    if not user_vec.any():
        return []

    candidates = [item for item in items if item["id"] not in liked_ids]
    if not candidates:
        return []

    item_matrix = np.zeros((len(candidates), n))
    for i, item in enumerate(candidates):
        for field in tag_fields:
            for tag in (item.get(field) or []):
                key = tag.lower()
                if key in vocab:
                    item_matrix[i, vocab[key]] = 1.0

    scores = cosine_similarity(user_vec.reshape(1, -1), item_matrix)[0]

    top_indices = np.argsort(scores)[::-1]
    results = []
    for idx in top_indices:
        if scores[idx] <= 0 or len(results) >= 50:
            break

        item = candidates[idx]

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
    key = f"recs_track_{uid}"
    if key not in _cache:
        items = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
        _cache[key] = _build_recommendations(uid, "track", items, ["genres", "tags"])
    return _cache[key]


@router.get("/{uid}/movies")
def recommend_movies(uid: str):
    key = f"recs_movie_{uid}"
    if key not in _cache:
        items = cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
        _cache[key] = _build_recommendations(uid, "movie", items, ["genres", "keywords"], min_df=2)
    return _cache[key]


@router.get("/{uid}/games")
def recommend_games(uid: str):
    key = f"recs_game_{uid}"
    if key not in _cache:
        items = cached_query("games", "SELECT * FROM games ORDER BY rating DESC")
        _cache[key] = _build_recommendations(uid, "game", items, ["genres", "tags"])
    return _cache[key]
