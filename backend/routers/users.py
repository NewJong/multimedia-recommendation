import math
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from collections import defaultdict
from database import get_conn, cached_query

router = APIRouter(prefix="/users", tags=["users"])


class UserSync(BaseModel):
    uid: str
    email: str
    name: str | None = None
    photo_url: str | None = None


class SocialLinks(BaseModel):
    telegram:  str = ""
    instagram: str = ""
    steam:     str = ""
    discord:   str = ""
    tiktok:    str = ""


def _row_to_dict(row) -> dict:
    d = dict(row)
    if isinstance(d.get("created_at"), datetime):
        d["created_at"] = d["created_at"].isoformat()
    return d


@router.post("/sync")
def sync_user(body: UserSync):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (firebase_uid, email, name, photo_url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (firebase_uid) DO UPDATE
            SET email     = EXCLUDED.email,
                name      = EXCLUDED.name,
                photo_url = EXCLUDED.photo_url
        RETURNING id, firebase_uid, email, name, photo_url, created_at,
                  social_telegram, social_instagram, social_steam, social_discord, social_tiktok
    """, (body.uid, body.email, body.name, body.photo_url))
    row = _row_to_dict(cur.fetchone())
    conn.commit(); cur.close(); conn.close()
    return row


@router.patch("/{uid}/socials")
def update_socials(uid: str, body: SocialLinks):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE users SET
            social_telegram  = %s,
            social_instagram = %s,
            social_steam     = %s,
            social_discord   = %s,
            social_tiktok    = %s
        WHERE firebase_uid = %s
    """, (body.telegram, body.instagram, body.steam, body.discord, body.tiktok, uid))
    if cur.rowcount == 0:
        conn.rollback(); cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit(); cur.close(); conn.close()
    return {"ok": True}


@router.get("/search")
def search_users(q: str = Query(..., min_length=1)):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT firebase_uid, name, email, photo_url FROM users
        WHERE name ILIKE %s OR email ILIKE %s LIMIT 20
    """, (f"%{q}%", f"%{q}%"))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


_USER_TAG_FIELDS = {
    "game":  ("genres", "tags"),
    "movie": ("genres", "keywords"),
    "track": ("genres", "tags"),
}

_idf_cache: dict = {}


def _get_idf_index(games, movies, tracks):
    key = (len(games), len(movies), len(tracks))
    if key in _idf_cache:
        return _idf_cache[key]

    df: dict[str, int] = {}
    total = 0
    by_id: dict[str, dict[int, set[str]]] = {"game": {}, "movie": {}, "track": {}}
    for kind, items in (("game", games), ("movie", movies), ("track", tracks)):
        fields = _USER_TAG_FIELDS[kind]
        for item in items:
            tags: set[str] = set()
            for f in fields:
                for tag in (item.get(f) or []):
                    tags.add(tag.lower())
            by_id[kind][item["id"]] = tags
            for k in tags:
                df[k] = df.get(k, 0) + 1
            total += 1

    vocab = {k: i for i, k in enumerate(df.keys())}
    idf = np.zeros(len(vocab))
    for k, i in vocab.items():
        idf[i] = math.log(total / (df[k] + 1))

    bundle = {"vocab": vocab, "idf": idf, "tags_by_id": by_id}
    _idf_cache[key] = bundle
    return bundle


def _build_user_vector(by_type: dict[str, set[int]], bundle) -> tuple[np.ndarray, set[str]]:
    vocab = bundle["vocab"]
    idf = bundle["idf"]
    tags_by_id = bundle["tags_by_id"]

    vec = np.zeros(len(vocab))
    tag_set: set[str] = set()
    for kind in ("game", "movie", "track"):
        for iid in by_type[kind]:
            for k in tags_by_id[kind].get(iid, ()):
                if k in vocab:
                    vec[vocab[k]] += idf[vocab[k]]
                    tag_set.add(k)
    return vec, tag_set


def _compat_payload(
    user_row: dict,
    my_likes: dict[str, set[int]],
    their_likes: dict[str, set[int]],
    my_vec: np.ndarray, my_norm: float, my_tag_set: set[str],
    bundle,
    titles: dict[str, dict[int, str]],
) -> dict | None:
    if sum(len(v) for v in their_likes.values()) == 0:
        return None

    their_vec, their_tag_set = _build_user_vector(their_likes, bundle)
    their_norm = float(np.linalg.norm(their_vec))
    if their_norm == 0:
        return None

    sim = float(np.dot(my_vec, their_vec) / (my_norm * their_norm))
    compatibility = round(sim * 100)

    vocab = bundle["vocab"]
    idf = bundle["idf"]
    shared_tags_sorted = sorted(
        my_tag_set & their_tag_set,
        key=lambda k: -idf[vocab[k]] if k in vocab else 0,
    )[:4]

    shared_movies = my_likes["movie"] & their_likes["movie"]
    shared_games  = my_likes["game"]  & their_likes["game"]
    shared_tracks = my_likes["track"] & their_likes["track"]
    overlap_count = len(shared_movies) + len(shared_games) + len(shared_tracks)

    sample = []
    for mid in list(shared_movies)[:1]:
        if mid in titles["movie"]: sample.append({"type": "movie", "id": mid, "label": titles["movie"][mid]})
    for gid in list(shared_games)[:1]:
        if gid in titles["game"]:  sample.append({"type": "game",  "id": gid, "label": titles["game"][gid]})
    for tid in list(shared_tracks)[:1]:
        if tid in titles["track"]: sample.append({"type": "track", "id": tid, "label": titles["track"][tid]})

    return {
        **user_row,
        "compatibility":  compatibility,
        "overlap_count":  overlap_count,
        "shared_sample":  sample,
        "shared_tags":    [t.title() for t in shared_tags_sorted],
        "their_total":    sum(len(v) for v in their_likes.values()),
    }


def _load_likes(cur, uids: list[str]) -> dict[str, dict[str, set[int]]]:
    by_user: dict[str, dict[str, set[int]]] = defaultdict(
        lambda: {"game": set(), "movie": set(), "track": set()}
    )
    if not uids:
        return by_user
    cur.execute(
        "SELECT user_uid, item_type, item_id FROM likes WHERE user_uid = ANY(%s)",
        (uids,),
    )
    for r in cur.fetchall():
        by_user[r["user_uid"]][r["item_type"]].add(r["item_id"])
    return by_user


def _rank_with_compat(
    candidate_rows: list[dict],
    cur,
    bundle,
    titles,
    my_likes,
    my_vec,
    my_norm,
    my_tag_set,
    min_compat: int = 0,
) -> list[dict]:
    uids = [c["firebase_uid"] for c in candidate_rows]
    likes_map = _load_likes(cur, uids)

    out = []
    for c in candidate_rows:
        payload = _compat_payload(
            c, my_likes, likes_map.get(c["firebase_uid"], {"game": set(), "movie": set(), "track": set()}),
            my_vec, my_norm, my_tag_set, bundle, titles,
        )
        if payload is None:
            continue
        if payload["compatibility"] < min_compat:
            continue
        out.append(payload)
    out.sort(key=lambda r: (-r["compatibility"], -r["overlap_count"]))
    return out


@router.get("/social/{uid}")
def social_panel(uid: str, suggested_limit: int = Query(8, ge=1, le=30)):
    games  = cached_query("games",  "SELECT * FROM games  ORDER BY rating DESC")
    movies = cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
    tracks = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
    bundle = _get_idf_index(games, movies, tracks)
    titles = {
        "movie": {m["id"]: m["title"] for m in movies},
        "game":  {g["id"]: g["title"] for g in games},
        "track": {t["id"]: f"{t['artist']} — {t['name']}" for t in tracks},
    }

    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT item_type, item_id FROM likes WHERE user_uid = %s", (uid,))
        my_likes: dict[str, set[int]] = {"game": set(), "movie": set(), "track": set()}
        for r in cur.fetchall():
            my_likes[r["item_type"]].add(r["item_id"])

        if sum(len(v) for v in my_likes.values()) == 0:
            return {"friends": [], "suggested": []}

        my_vec, my_tag_set = _build_user_vector(my_likes, bundle)
        my_norm = float(np.linalg.norm(my_vec))
        if my_norm == 0:
            return {"friends": [], "suggested": []}

        cur.execute("""
            SELECT u.firebase_uid, u.name, u.email, u.photo_url
            FROM friend_requests fr
            JOIN users u ON (
                CASE WHEN fr.from_uid = %s THEN fr.to_uid ELSE fr.from_uid END = u.firebase_uid
            )
            WHERE (fr.from_uid = %s OR fr.to_uid = %s) AND fr.status = 'accepted'
        """, (uid, uid, uid))
        friend_rows = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT u.firebase_uid, u.name, u.email, u.photo_url
            FROM users u
            WHERE u.firebase_uid <> %s
              AND u.email NOT LIKE %s
              AND u.firebase_uid NOT IN (
                  SELECT CASE WHEN from_uid = %s THEN to_uid ELSE from_uid END
                  FROM friend_requests
                  WHERE from_uid = %s OR to_uid = %s
              )
        """, (uid, "%@test.local", uid, uid, uid))
        suggested_rows = [dict(r) for r in cur.fetchall()]

        friends = _rank_with_compat(
            friend_rows, cur, bundle, titles,
            my_likes, my_vec, my_norm, my_tag_set,
            min_compat=0,
        )
        for f in friend_rows:
            if not any(x["firebase_uid"] == f["firebase_uid"] for x in friends):
                friends.append({**f, "compatibility": 0, "overlap_count": 0, "shared_sample": [], "shared_tags": [], "their_total": 0})

        suggested = _rank_with_compat(
            suggested_rows, cur, bundle, titles,
            my_likes, my_vec, my_norm, my_tag_set,
            min_compat=1,
        )[:suggested_limit]
    finally:
        cur.close(); conn.close()

    return {"friends": friends, "suggested": suggested}


@router.get("/{uid}")
def get_user(uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT firebase_uid, name, email, photo_url,
               social_telegram, social_instagram, social_steam, social_discord, social_tiktok
        FROM users WHERE firebase_uid = %s
    """, (uid,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)
