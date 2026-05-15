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
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO likes (user_uid, item_type, item_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_uid, item_type, item_id) DO NOTHING
                RETURNING id
            """, (uid, item_type, item_id))
            if cur.fetchone():
                liked = True
            else:
                cur.execute(
                    "DELETE FROM likes WHERE user_uid=%s AND item_type=%s AND item_id=%s",
                    (uid, item_type, item_id),
                )
                liked = False
    finally:
        conn.close()

    _cache.pop(f"recs_{item_type}_{uid}", None)

    return {"liked": liked}


@router.get("/{uid}")
def get_user_likes(uid: str):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.* FROM tracks t
                JOIN likes l ON l.item_type = 'track' AND l.item_id = t.id
                WHERE l.user_uid = %s
                ORDER BY l.created_at DESC
            """, (uid,))
            tracks = serialize_rows([dict(r) for r in cur.fetchall()])

            cur.execute("""
                SELECT m.* FROM movies m
                JOIN likes l ON l.item_type = 'movie' AND l.item_id = m.id
                WHERE l.user_uid = %s
                ORDER BY l.created_at DESC
            """, (uid,))
            movies = serialize_rows([dict(r) for r in cur.fetchall()])

            cur.execute("""
                SELECT g.* FROM games g
                JOIN likes l ON l.item_type = 'game' AND l.item_id = g.id
                WHERE l.user_uid = %s
                ORDER BY l.created_at DESC
            """, (uid,))
            games = serialize_rows([dict(r) for r in cur.fetchall()])
    finally:
        conn.close()
    return {"tracks": tracks, "movies": movies, "games": games}
