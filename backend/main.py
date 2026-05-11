from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import httpx, os, psycopg2, psycopg2.extras, json

try:
    import anthropic as _anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="TIOKhor API")

_cache: dict = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LASTFM_KEY     = os.getenv("LASTFM_API_KEY")
LASTFM_BASE    = "https://ws.audioscrobbler.com/2.0"
DB_URL         = os.getenv("DATABASE_URL")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def serialize_rows(rows):
    result = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                clean[k] = float(v)
            elif isinstance(v, datetime):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        result.append(clean)
    return result


async def lfm(method: str, **params):
    async with httpx.AsyncClient() as client:
        r = await client.get(LASTFM_BASE, params={
            "method": method, "api_key": LASTFM_KEY, "format": "json", **params
        })
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["message"])
        return data


class UserSync(BaseModel):
    uid: str
    email: str
    name: str | None = None
    photo_url: str | None = None


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/users/sync")
def sync_user(body: UserSync):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (firebase_uid, email, name, photo_url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (firebase_uid) DO UPDATE
            SET email     = EXCLUDED.email,
                name      = EXCLUDED.name,
                photo_url = EXCLUDED.photo_url
        RETURNING id, firebase_uid, email, name, photo_url, created_at
    """, (body.uid, body.email, body.name, body.photo_url))
    row = dict(cur.fetchone())
    conn.commit()
    cur.close(); conn.close()
    if isinstance(row.get("created_at"), datetime):
        row["created_at"] = row["created_at"].isoformat()
    return row


@app.get("/users/search")
def search_users(q: str = Query(..., min_length=1)):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT firebase_uid, name, email, photo_url FROM users
        WHERE name ILIKE %s OR email ILIKE %s LIMIT 20
    """, (f"%{q}%", f"%{q}%"))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


@app.get("/users/{uid}")
def get_user(uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT firebase_uid, name, email, photo_url FROM users WHERE firebase_uid = %s", (uid,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


# ── Friends ────────────────────────────────────────────────────────────────

@app.get("/friends/{uid}/status/{other_uid}")
def friend_status(uid: str, other_uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT from_uid, status FROM friend_requests
        WHERE (from_uid=%s AND to_uid=%s) OR (from_uid=%s AND to_uid=%s)
    """, (uid, other_uid, other_uid, uid))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return {"status": "none"}
    if row["status"] == "accepted":
        return {"status": "friends"}
    return {"status": "pending_sent" if row["from_uid"] == uid else "pending_received"}


@app.get("/friends/{uid}/requests")
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


@app.get("/friends/{uid}")
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


@app.post("/friends/{uid}/request/{to_uid}")
def send_request(uid: str, to_uid: str):
    if uid == to_uid:
        raise HTTPException(status_code=400, detail="Cannot add yourself")
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO friend_requests (from_uid, to_uid)
        VALUES (%s, %s) ON CONFLICT DO NOTHING
    """, (uid, to_uid))
    conn.commit(); cur.close(); conn.close()
    return {"status": "pending_sent"}


@app.post("/friends/{uid}/accept/{from_uid}")
def accept_request(uid: str, from_uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE friend_requests SET status = 'accepted'
        WHERE from_uid = %s AND to_uid = %s AND status = 'pending'
    """, (from_uid, uid))
    conn.commit(); cur.close(); conn.close()
    return {"status": "friends"}


@app.delete("/friends/{uid}/{other_uid}")
def remove_friend(uid: str, other_uid: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        DELETE FROM friend_requests
        WHERE (from_uid=%s AND to_uid=%s) OR (from_uid=%s AND to_uid=%s)
    """, (uid, other_uid, other_uid, uid))
    conn.commit(); cur.close(); conn.close()
    return {"status": "none"}


def _query(key: str, sql: str):
    if key not in _cache:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql)
        _cache[key] = serialize_rows(cur.fetchall())
        cur.close(); conn.close()
    return _cache[key]


@app.get("/tracks")
def get_tracks():
    return _query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")


@app.get("/tracks/{track_id}")
def get_track_by_id(track_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tracks WHERE id = %s", (track_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Track not found")
    return serialize_rows([dict(row)])[0]


@app.get("/movies")
def get_movies():
    return _query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")


@app.get("/movies/{movie_id}")
def get_movie_by_id(movie_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Movie not found")
    return serialize_rows([dict(row)])[0]


@app.get("/games")
def get_games():
    return _query("games", "SELECT * FROM games ORDER BY rating DESC")


@app.get("/games/{game_id}")
def get_game_by_id(game_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM games WHERE id = %s", (game_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Game not found")
    return serialize_rows([dict(row)])[0]


@app.get("/tags/overview")
def get_tags_overview():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT tag, COUNT(*) AS cnt
        FROM tracks, unnest(tags) AS tag
        GROUP BY tag ORDER BY cnt DESC LIMIT 60
    """)
    music_tags = [{"tag": r["tag"], "count": r["cnt"]} for r in cur.fetchall()]

    cur.execute("""
        SELECT kw, COUNT(*) AS cnt
        FROM movies, unnest(keywords) AS kw
        GROUP BY kw ORDER BY cnt DESC LIMIT 60
    """)
    movie_keywords = [{"tag": r["kw"], "count": r["cnt"]} for r in cur.fetchall()]

    cur.execute("""
        SELECT tag, COUNT(*) AS cnt
        FROM games, unnest(tags) AS tag
        GROUP BY tag ORDER BY cnt DESC LIMIT 60
    """)
    game_tags = [{"tag": r["tag"], "count": r["cnt"]} for r in cur.fetchall()]

    music_set  = {t["tag"].lower() for t in music_tags}
    movie_set  = {t["tag"].lower() for t in movie_keywords}
    game_set   = {t["tag"].lower() for t in game_tags}

    cross_mg = sorted(music_set & game_set)
    cross_mf = sorted(music_set & movie_set)
    cross_fg = sorted(movie_set & game_set)
    cross_all = sorted(music_set & movie_set & game_set)

    return {
        "music":  music_tags,
        "movies": movie_keywords,
        "games":  game_tags,
        "overlap": {
            "music_and_games":  cross_mg,
            "music_and_movies": cross_mf,
            "movies_and_games": cross_fg,
            "all_three":        cross_all,
        },
    }


class SearchBody(BaseModel):
    q: str
    ai: bool = False


@app.post("/search")
async def search(body: SearchBody):
    q = body.q.strip()
    if not q:
        return {"tracks": [], "movies": [], "games": [], "explanation": None}

    tracks = _query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
    movies = _query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
    games  = _query("games",  "SELECT * FROM games  ORDER BY rating DESC")

    if not body.ai:
        ql = q.lower()
        def mt(t): return (
            ql in t["name"].lower() or ql in t.get("artist", "").lower()
            or ql in t.get("genre", "").lower()
            or any(ql in tag.lower() for tag in t.get("tags", []))
            or any(ql in g.lower() for g in t.get("genres", []))
        )
        def mm(m): return (
            ql in m["title"].lower() or ql in m.get("director", "").lower()
            or any(ql in g.lower() for g in m.get("genres", []))
        )
        def mg(g): return (
            ql in g["title"].lower()
            or any(ql in g2.lower() for g2 in g.get("genres", []))
            or any(ql in tag.lower() for tag in g.get("tags", []))
        )
        return {
            "tracks": [t for t in tracks if mt(t)][:12],
            "movies": [m for m in movies if mm(m)][:12],
            "games":  [gm for gm in games if mg(gm)][:12],
            "explanation": None,
        }

    # AI mode
    if not _HAS_ANTHROPIC:
        raise HTTPException(status_code=503, detail="anthropic package not installed — run: pip install anthropic")
    if not ANTHROPIC_KEY or ANTHROPIC_KEY in ("soon", ""):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not set")

    # send only top 40 per domain (already sorted by popularity/rating) — keeps prompt small
    catalog = {
        "t": [{"i": t["id"], "n": t["name"],  "g": t.get("genres", [])[:3]} for t in tracks[:40]],
        "m": [{"i": m["id"], "n": m["title"], "g": m.get("genres", [])[:3]} for m in movies[:40]],
        "g": [{"i": g["id"], "n": g["title"], "g": g.get("genres", [])[:3]} for g in games[:40]],
    }

    client = _anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system='You are a recommendation assistant. Always respond with raw JSON only — no markdown, no code fences, no explanation outside the JSON.',
        messages=[{"role": "user", "content":
            f'User wants: "{q}"\n\n'
            f'From the catalog below pick up to 5 best-matching items per category.\n'
            f'Respond with this exact JSON structure (raw, no markdown):\n'
            f'{{"e":"one sentence about what you found","t":[list of track i integers],"m":[list of movie i integers],"g":[list of game i integers]}}\n\n'
            f'Catalog: {json.dumps(catalog, separators=(",",":"))}'
        }]
    )

    raw = msg.content[0].text.strip()
    # strip markdown fences if model wraps anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {raw[:200]}")

    tid = set(result.get("t", []))
    mid = set(result.get("m", []))
    gid = set(result.get("g", []))
    return {
        "tracks":      [t for t in tracks if t["id"] in tid],
        "movies":      [m for m in movies if m["id"] in mid],
        "games":       [g for g in games  if g["id"] in gid],
        "explanation": result.get("e"),
    }


@app.get("/likes/{uid}/{item_type}/{item_id}")
def check_like(uid: str, item_type: str, item_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "SELECT id FROM likes WHERE user_uid=%s AND item_type=%s AND item_id=%s",
        (uid, item_type, item_id)
    )
    row = cur.fetchone(); cur.close(); conn.close()
    return {"liked": row is not None}


@app.post("/likes/{uid}/{item_type}/{item_id}")
def toggle_like(uid: str, item_type: str, item_id: int):
    if item_type not in ("track", "movie", "game"):
        raise HTTPException(status_code=400, detail="Invalid item_type")
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "SELECT id FROM likes WHERE user_uid=%s AND item_type=%s AND item_id=%s",
        (uid, item_type, item_id)
    )
    if cur.fetchone():
        cur.execute(
            "DELETE FROM likes WHERE user_uid=%s AND item_type=%s AND item_id=%s",
            (uid, item_type, item_id)
        )
        liked = False
    else:
        cur.execute(
            "INSERT INTO likes (user_uid, item_type, item_id) VALUES (%s, %s, %s)",
            (uid, item_type, item_id)
        )
        liked = True
    conn.commit(); cur.close(); conn.close()
    return {"liked": liked}


@app.get("/likes/{uid}")
def get_user_likes(uid: str):
    conn = get_conn(); cur = conn.cursor()

    cur.execute(
        "SELECT item_id FROM likes WHERE user_uid=%s AND item_type='track' ORDER BY created_at DESC",
        (uid,)
    )
    track_ids = [r["item_id"] for r in cur.fetchall()]

    cur.execute(
        "SELECT item_id FROM likes WHERE user_uid=%s AND item_type='movie' ORDER BY created_at DESC",
        (uid,)
    )
    movie_ids = [r["item_id"] for r in cur.fetchall()]

    cur.execute(
        "SELECT item_id FROM likes WHERE user_uid=%s AND item_type='game' ORDER BY created_at DESC",
        (uid,)
    )
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


@app.get("/music/track")
async def get_track(artist: str = Query(...), track: str = Query(...)):
    data = await lfm("track.getInfo", artist=artist, track=track)
    t = data["track"]

    image = None
    if "album" in t and "image" in t["album"]:
        for img in reversed(t["album"]["image"]):
            if img["#text"]:
                image = img["#text"]
                break

    return {
        "name": t["name"],
        "artist": t["artist"]["name"],
        "duration_ms": int(t.get("duration", 0)),
        "listeners": int(t.get("listeners", 0)),
        "playcount": int(t.get("playcount", 0)),
        "tags": [tag["name"] for tag in t.get("toptags", {}).get("tag", [])],
        "summary": t.get("wiki", {}).get("summary", "").split('<a href')[0].strip(),
        "image": image,
        "url": t.get("url"),
        "mbid": t.get("mbid"),
        "album": t.get("album", {}).get("title"),
    }
