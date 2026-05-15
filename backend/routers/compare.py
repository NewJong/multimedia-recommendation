import os
import math
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


def _get_name(uid: str) -> str:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT name FROM users WHERE firebase_uid=%s", (uid,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return (row["name"] if row else "Unknown").split()[0]  


def _domain_idf(items: list, fields: list, min_df: int = 1) -> dict[str, float]:
    N = len(items)
    df: dict[str, int] = {}
    for item in items:
        seen: set[str] = set()
        for f in fields:
            for tag in (item.get(f) or []):
                k = tag.lower()
                if k not in seen:
                    df[k] = df.get(k, 0) + 1
                    seen.add(k)
    return {tag: math.log(N / (freq + 1)) for tag, freq in df.items() if freq >= min_df}


def _top_tags(likes: dict[str, set[int]], games, movies, tracks, n=8) -> list[str]:
    idf_g = _domain_idf(games,  ["tags", "genres"])
    idf_m = _domain_idf(movies, ["genres", "keywords"], min_df=2)
    idf_t = _domain_idf(tracks, ["genres", "tags"])

    w: dict[str, float] = {}
    for g in games:
        if g["id"] in likes["game"]:
            for tag in (g.get("tags") or []) + (g.get("genres") or []):
                w[tag] = w.get(tag, 0) + idf_g.get(tag.lower(), 0.0)
    for m in movies:
        if m["id"] in likes["movie"]:
            for tag in (m.get("genres") or []) + (m.get("keywords") or []):
                w[tag] = w.get(tag, 0) + idf_m.get(tag.lower(), 0.0)
    for t in tracks:
        if t["id"] in likes["track"]:
            for tag in (t.get("genres") or []) + (t.get("tags") or []):
                w[tag] = w.get(tag, 0) + idf_t.get(tag.lower(), 0.0)
    return [tag for tag, _ in sorted(w.items(), key=lambda x: -x[1]) if w[tag] > 0][:n]


def _distinctive_picks(
    my_liked: set[int], their_liked: set[int], items: list,
    tag_fields: list, min_df: int = 1
) -> list[tuple[dict, int, list[str]]]:
    """
    Items from their library (minus mine) that capture what's DISTINCTIVE about
    their taste compared to mine. Score = how much they prefer this item's tags
    over how much I do (their_vec − my_vec, clipped at 0).

    This is the opposite of For You: For You finds what matches MY taste; this
    finds what they bring that I don't already have. If I love rock and they
    love jazz, jazz tracks bubble to the top here — even though they'd never
    appear in my For You.

    Returns up to 3 (item, score_0_100, top_diff_tags) tuples, with the highest
    distinctive score normalized to 100.
    """
    doc_freq: dict[str, int] = {}
    for item in items:
        seen: set[str] = set()
        for f in tag_fields:
            for tag in (item.get(f) or []):
                k = tag.lower()
                if k not in seen:
                    doc_freq[k] = doc_freq.get(k, 0) + 1
                    seen.add(k)

    vocab: dict[str, int] = {}
    for k, freq in doc_freq.items():
        if freq >= min_df:
            vocab[k] = len(vocab)
    if not vocab:
        return []
    N = len(items)
    idf_arr = np.zeros(len(vocab))
    for k, idx in vocab.items():
        idf_arr[idx] = math.log(N / (doc_freq[k] + 1))

    def build_vec(liked: set[int]) -> np.ndarray:
        v = np.zeros(len(vocab))
        for item in items:
            if item["id"] not in liked:
                continue
            for f in tag_fields:
                for tag in (item.get(f) or []):
                    k = tag.lower()
                    if k in vocab:
                        v[vocab[k]] += idf_arr[vocab[k]]
        return v

    my_vec    = build_vec(my_liked)
    their_vec = build_vec(their_liked)
    diff_vec  = np.maximum(their_vec - my_vec, 0)

    idx_to_tag = {i: k for k, i in vocab.items()}
    candidates = [i for i in items if i["id"] in their_liked and i["id"] not in my_liked]
    scored: list[tuple[float, dict, list[str]]] = []
    for item in candidates:
        tag_indices = set()
        for f in tag_fields:
            for tag in (item.get(f) or []):
                k = tag.lower()
                if k in vocab:
                    tag_indices.add(vocab[k])
        if not tag_indices:
            continue
        score = float(sum(diff_vec[i] for i in tag_indices))
        if score <= 0:
            continue
        top_tags = sorted(tag_indices, key=lambda i: -diff_vec[i])
        matched_tags = [idx_to_tag[i].title() for i in top_tags if diff_vec[i] > 0][:3]
        scored.append((score, item, matched_tags))

    scored.sort(key=lambda x: -x[0])
    if not scored:
        return []
    max_score = scored[0][0]
    return [(item, round((s / max_score) * 100), tags) for s, item, tags in scored[:3]]


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

    games  = cached_query("games",  "SELECT * FROM games  ORDER BY rating DESC")
    movies = cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
    tracks = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")

    likes1 = _likes_by_type(uid1)
    likes2 = _likes_by_type(uid2)
    name1  = _get_name(uid1)
    name2  = _get_name(uid2)

    common_games  = [{"id": g["id"], "title": g["title"]} for g in games  if g["id"] in likes1["game"]  & likes2["game"]][:6]
    common_movies = [{"id": m["id"], "title": m["title"]} for m in movies if m["id"] in likes1["movie"] & likes2["movie"]][:6]
    common_tracks = [{"id": t["id"], "title": t["name"]}  for t in tracks if t["id"] in likes1["track"] & likes2["track"]][:6]

    games_picks  = _distinctive_picks(likes1["game"],  likes2["game"],  games,  ["genres", "tags"])
    movies_picks = _distinctive_picks(likes1["movie"], likes2["movie"], movies, ["genres", "keywords"], min_df=2)
    tracks_picks = _distinctive_picks(likes1["track"], likes2["track"], tracks, ["genres", "tags"])

    picks = {
        "games":  [{"id": i["id"], "title": i["title"], "poster_url": i.get("poster_url"),
                    "release_year": i.get("release_year"), "score": s, "matched_tags": t}
                   for i, s, t in games_picks],
        "movies": [{"id": i["id"], "title": i["title"], "poster_url": i.get("poster_url"),
                    "release_year": i.get("release_year"), "score": s, "matched_tags": t}
                   for i, s, t in movies_picks],
        "tracks": [{"id": i["id"], "title": i["name"], "image_url": i.get("image_url"),
                    "artist": i.get("artist"), "score": s, "matched_tags": t}
                   for i, s, t in tracks_picks],
    }

    tags1 = _top_tags(likes1, games, movies, tracks)
    tags2 = _top_tags(likes2, games, movies, tracks)
    compatibility = _cosine(tags1, tags2)

    total1 = sum(len(v) for v in likes1.values())
    total2 = sum(len(v) for v in likes2.values())

    all_common_titles = (
        [x["title"] for x in common_games] +
        [x["title"] for x in common_movies] +
        [x["title"] for x in common_tracks]
    )
    shared_line = ", ".join(all_common_titles) if all_common_titles else "nothing in common yet"

    pick_titles = (
        [f'"{p["title"]}" (music)' for p in picks["tracks"]] +
        [f'"{p["title"]}" (movie)' for p in picks["movies"]] +
        [f'"{p["title"]}" (game)'  for p in picks["games"]]
    )
    picks_line = ", ".join(pick_titles) if pick_titles else "no distinctive picks"

    domains_with_picks = sum(1 for k in ("tracks", "movies", "games") if picks[k])
    if domains_with_picks >= 3:
        diversity_rule = "Pick exactly THREE items — ONE from music, ONE from a movie, ONE from a game. Never pick two from the same domain."
    elif domains_with_picks == 2:
        diversity_rule = "Pick exactly TWO items — one from each of the two domains that have picks. Never both from the same domain."
    elif domains_with_picks == 1:
        diversity_rule = "Pick 1-2 items from the single domain with picks."
    else:
        diversity_rule = "Skip the suggestion sentence — there are no distinctive picks to recommend."

    prompt = f"""Two users on a multimedia recommendation platform (games, movies, music).

{name1} — {total1} liked items. Their taste: {", ".join(tags1) or "nothing liked yet"}.
{name2} — {total2} liked items. Their taste: {", ".join(tags2) or "nothing liked yet"}.

Shared liked content: {shared_line}.
Taste compatibility score: {compatibility}%.

Items that capture what's DISTINCTIVE about {name2}'s taste vs {name1}'s: {picks_line}.

Write EXACTLY 3 short sentences addressed to {name1} in second person ("you"), ~80-100 words total.

Sentence 1: what you and {name2} share — specific genres/themes.
Sentence 2: where {name2}'s taste diverges from yours — what vibes they bring that you don't.
Sentence 3: concrete suggestions to broaden taste. {diversity_rule} Use the format: "Title" (music/movie/game) — for example: "Kind of Blue" (music) and "Pulp Fiction" (movie). Do NOT wrap the whole quotation in single quotes — write the titles directly in the sentence.

Start directly, no intro words. Casual tone, specific not generic, no bullet points."""

    msg = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=280,
        messages=[{"role": "user", "content": prompt}],
    )

    import re
    insight = msg.content[0].text.strip()
    insight = re.sub(r'^[\w]+[—–:]\s*', '', insight)

    return {
        "insight": insight,
        "compatibility": compatibility,
        "name1": name1,
        "name2": name2,
        "common": {
            "games":  common_games,
            "movies": common_movies,
            "tracks": common_tracks,
        },
        "picks": picks,
        "tags1": [t.title() for t in tags1[:6]],
        "tags2": [t.title() for t in tags2[:6]],
    }
