from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from database import get_conn

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
