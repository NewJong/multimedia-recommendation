from fastapi import APIRouter, HTTPException
from datetime import datetime
from database import get_conn

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("/{uid}/status/{other_uid}")
def friend_status(uid: str, other_uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT from_uid, status FROM friend_requests
        WHERE (from_uid=%s AND to_uid=%s) OR (from_uid=%s AND to_uid=%s)
    """, (uid, other_uid, other_uid, uid))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        return {"status": "none"}
    if row["status"] == "accepted":
        return {"status": "friends"}
    return {"status": "pending_sent" if row["from_uid"] == uid else "pending_received"}


@router.get("/{uid}/requests")
def get_friend_requests(uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.firebase_uid, u.name, u.email, u.photo_url, fr.created_at
        FROM friend_requests fr
        JOIN users u ON fr.from_uid = u.firebase_uid
        WHERE fr.to_uid = %s AND fr.status = 'pending'
        ORDER BY fr.created_at DESC
    """, (uid,))
    result = []
    for r in cur.fetchall():
        row = dict(r)
        if isinstance(row.get("created_at"), datetime):
            row["created_at"] = row["created_at"].isoformat()
        result.append(row)
    cur.close(); conn.close()
    return result


@router.get("/{uid}")
def get_friends(uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.firebase_uid, u.name, u.email, u.photo_url
        FROM friend_requests fr
        JOIN users u ON (
            CASE WHEN fr.from_uid = %s THEN fr.to_uid ELSE fr.from_uid END = u.firebase_uid
        )
        WHERE (fr.from_uid = %s OR fr.to_uid = %s) AND fr.status = 'accepted'
    """, (uid, uid, uid))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


@router.post("/{uid}/request/{to_uid}")
def send_request(uid: str, to_uid: str):
    if uid == to_uid:
        raise HTTPException(status_code=400, detail="Cannot add yourself")
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO friend_requests (from_uid, to_uid) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, to_uid))
    conn.commit(); cur.close(); conn.close()
    return {"status": "pending_sent"}


@router.post("/{uid}/accept/{from_uid}")
def accept_request(uid: str, from_uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE friend_requests SET status = 'accepted'
        WHERE from_uid = %s AND to_uid = %s AND status = 'pending'
    """, (from_uid, uid))
    conn.commit(); cur.close(); conn.close()
    return {"status": "friends"}


@router.delete("/{uid}/{other_uid}")
def remove_friend(uid: str, other_uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        DELETE FROM friend_requests
        WHERE (from_uid=%s AND to_uid=%s) OR (from_uid=%s AND to_uid=%s)
    """, (uid, other_uid, other_uid, uid))
    conn.commit(); cur.close(); conn.close()
    return {"status": "none"}
