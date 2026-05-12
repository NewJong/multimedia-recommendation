import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter, HTTPException
from database import get_conn, cached_query
from anthropic import Anthropic

router = APIRouter(prefix="/compare", tags=["compare"])
_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _likes_by_type(uid: str) -> dict[str, set[int]]:
    conn = get_conn(); cur = conn.cursor()
    result: dict[str, set[int]] = {"game": set(), "movie": set(), "track": set()}
    for t in result:
        cur.execute("SELECT item_id FROM likes WHERE user_uid=%s AND item_type=%s", (uid, t))
        result[t] = {r["item_id"] for r in cur.fetchall()}
    cur.close(); conn.close()
    return result


def _top_tags(likes: dict[str, set[int]], games, movies, tracks, n=8) -> list[str]:
    w: dict[str, float] = {}
    for g in games:
        if g["id"] in likes["game"]:
            for tag in (g.get("tags") or []) + (g.get("genres") or []):
                w[tag] = w.get(tag, 0) + 1
    for m in movies:
        if m["id"] in likes["movie"]:
            for tag in (m.get("genres") or []) + (m.get("keywords") or []):
                w[tag] = w.get(tag, 0) + 1
    for t in tracks:
        if t["id"] in likes["track"]:
            for tag in (t.get("genres") or []) + (t.get("tags") or []):
                w[tag] = w.get(tag, 0) + 1
    return [tag for tag, _ in sorted(w.items(), key=lambda x: -x[1])[:n]]


def _cosine(tags1: list[str], tags2: list[str]) -> int:
    vocab = list(set(tags1) | set(tags2))
    if not vocab:
        return 0
    s1 = set(t.lower() for t in tags1)
    s2 = set(t.lower() for t in tags2)
    v1 = np.array([1.0 if t.lower() in s1 else 0.0 for t in vocab])
    v2 = np.array([1.0 if t.lower() in s2 else 0.0 for t in vocab])
    if not v1.any() or not v2.any():
        return 0
    return round(float(cosine_similarity(v1.reshape(1, -1), v2.reshape(1, -1))[0][0]) * 100)


@router.get("/{uid1}/{uid2}/insight")
def get_insight(uid1: str, uid2: str):
    if uid1 == uid2:
        raise HTTPException(status_code=400, detail="Same user")

    games  = cached_query("games",  "SELECT id, title, genres, tags FROM games ORDER BY id")
    movies = cached_query("movies", "SELECT id, title, genres, keywords FROM movies ORDER BY id")
    tracks = cached_query("tracks", "SELECT id, name, genres, tags FROM tracks ORDER BY id")

    likes1 = _likes_by_type(uid1)
    likes2 = _likes_by_type(uid2)

    # Common liked items (up to 5 per domain for display)
    common_games  = [g["title"] for g in games  if g["id"] in likes1["game"]  & likes2["game"]][:5]
    common_movies = [m["title"] for m in movies if m["id"] in likes1["movie"] & likes2["movie"]][:5]
    common_tracks = [t["name"]  for t in tracks if t["id"] in likes1["track"] & likes2["track"]][:5]

    tags1 = _top_tags(likes1, games, movies, tracks)
    tags2 = _top_tags(likes2, games, movies, tracks)
    compatibility = _cosine(tags1, tags2)

    total1 = sum(len(v) for v in likes1.values())
    total2 = sum(len(v) for v in likes2.values())

    common_all = common_games + common_movies + common_tracks
    shared_line = ", ".join(common_all) if common_all else "nothing in common yet"

    prompt = f"""Two users on a multimedia recommendation platform (games, movies, music).

User A — {total1} liked items. Their taste: {", ".join(tags1) or "nothing liked yet"}.
User B — {total2} liked items. Their taste: {", ".join(tags2) or "nothing liked yet"}.

Shared liked content: {shared_line}.
Taste compatibility score: {compatibility}%.

Write 3 sentences comparing their tastes — what they share, how they differ, and a fun compatibility verdict. Be specific using the genres/themes above. Casual friendly tone, no bullet points."""

    msg = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=280,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "insight": msg.content[0].text,
        "compatibility": compatibility,
        "common": {
            "games":  common_games,
            "movies": common_movies,
            "tracks": common_tracks,
        },
        "tags1": [t.title() for t in tags1[:5]],
        "tags2": [t.title() for t in tags2[:5]],
    }
