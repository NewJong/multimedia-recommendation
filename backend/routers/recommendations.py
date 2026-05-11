import math
from fastapi import APIRouter
from database import get_conn, cached_query, serialize_rows

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _cosine(user_vec: dict[str, float], item_tags: list[str]) -> float:
    if not user_vec or not item_tags:
        return 0.0
    item_vec = {t.lower(): 1.0 for t in item_tags}
    dot     = sum(user_vec.get(k, 0.0) * v for k, v in item_vec.items())
    mag_u   = math.sqrt(sum(v * v for v in user_vec.values()))
    mag_i   = math.sqrt(sum(v * v for v in item_vec.values()))
    if mag_u == 0 or mag_i == 0:
        return 0.0
    return dot / (mag_u * mag_i)


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

    # Build user taste vector: {tag: how_many_liked_items_have_it}
    liked_items = [item for item in items if item["id"] in liked_ids]
    user_vec: dict[str, float] = {}
    for item in liked_items:
        for field in tag_fields:
            for tag in (item.get(field) or []):
                key = tag.lower()
                user_vec[key] = user_vec.get(key, 0.0) + 1.0

    if not user_vec:
        return []

    # Score every un-liked item with cosine similarity
    scored = []
    for item in items:
        if item["id"] in liked_ids:
            continue
        item_tags = []
        for field in tag_fields:
            item_tags.extend(item.get(field) or [])
        score = _cosine(user_vec, item_tags)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:24]]


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
