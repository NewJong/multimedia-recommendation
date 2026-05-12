from fastapi import APIRouter, HTTPException
from database import get_conn, serialize_rows, _cache

router = APIRouter(prefix="/likes", tags=["likes"])


@router.get("/friends/{uid}/{item_type}/{item_id}")
def friends_who_liked(uid: str, item_type: str, item_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.firebase_uid, u.name, u.photo_url
        FROM likes l
        JOIN users u ON l.user_uid = u.firebase_uid
        WHERE l.item_type = %s AND l.item_id = %s
          AND l.user_uid IN (
              SELECT CASE WHEN from_uid = %s THEN to_uid ELSE from_uid END
              FROM friend_requests
              WHERE (from_uid = %s OR to_uid = %s) AND status = 'accepted'
          )
        LIMIT 8
    """, (item_type, item_id, uid, uid, uid))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


@router.get("/{uid}/{item_type}/{item_id}")
def check_like(uid: str, item_type: str, item_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "SELECT id FROM likes WHERE user_uid=%s AND item_type=%s AND item_id=%s",
        (uid, item_type, item_id)
    )
    row = cur.fetchone(); cur.close(); conn.close()
    return {"liked": row is not None}


@router.post("/{uid}/{item_type}/{item_id}")
def toggle_like(uid: str, item_type: str, item_id: int):
    if item_type not in ("track", "movie", "game"):
        raise HTTPException(status_code=400, detail="Invalid item_type")
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "SELECT id FROM likes WHERE user_uid=%s AND item_type=%s AND item_id=%s",
        (uid, item_type, item_id)
    )
    if cur.fetchone():
        cur.execute("DELETE FROM likes WHERE user_uid=%s AND item_type=%s AND item_id=%s", (uid, item_type, item_id))
        liked = False
    else:
        cur.execute("INSERT INTO likes (user_uid, item_type, item_id) VALUES (%s, %s, %s)", (uid, item_type, item_id))
        liked = True
    conn.commit(); cur.close(); conn.close()

    # Invalidate cached recommendations so next For You load is fresh
    _cache.pop(f"recs_{item_type}_{uid}", None)

    return {"liked": liked}


@router.get("/{uid}")
def get_user_likes(uid: str):
    conn = get_conn(); cur = conn.cursor()

    cur.execute("SELECT item_id FROM likes WHERE user_uid=%s AND item_type='track' ORDER BY created_at DESC", (uid,))
    track_ids = [r["item_id"] for r in cur.fetchall()]

    cur.execute("SELECT item_id FROM likes WHERE user_uid=%s AND item_type='movie' ORDER BY created_at DESC", (uid,))
    movie_ids = [r["item_id"] for r in cur.fetchall()]

    cur.execute("SELECT item_id FROM likes WHERE user_uid=%s AND item_type='game' ORDER BY created_at DESC", (uid,))
    game_ids = [r["item_id"] for r in cur.fetchall()]

    tracks: list = []
    if track_ids:
        cur.execute("SELECT * FROM tracks WHERE id = ANY(%s)", (track_ids,))
        m = {r["id"]: dict(r) for r in cur.fetchall()}
        tracks = serialize_rows([m[i] for i in track_ids if i in m])

    movies: list = []
    if movie_ids:
        cur.execute("SELECT * FROM movies WHERE id = ANY(%s)", (movie_ids,))
        m = {r["id"]: dict(r) for r in cur.fetchall()}
        movies = serialize_rows([m[i] for i in movie_ids if i in m])

    games: list = []
    if game_ids:
        cur.execute("SELECT * FROM games WHERE id = ANY(%s)", (game_ids,))
        m = {r["id"]: dict(r) for r in cur.fetchall()}
        games = serialize_rows([m[i] for i in game_ids if i in m])

    cur.close(); conn.close()
    return {"tracks": tracks, "movies": movies, "games": games}
