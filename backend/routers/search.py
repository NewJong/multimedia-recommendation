import os, json, re, asyncio
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import cached_query, get_conn, serialize_rows

try:
    import anthropic as _anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

_st_model = None
def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _st_model


LASTFM_KEY    = os.getenv("LASTFM_API_KEY")
LASTFM_BASE   = "https://ws.audioscrobbler.com/2.0"
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

router = APIRouter(tags=["search"])


async def _lfm(method: str, **params):
    async with httpx.AsyncClient() as client:
        r = await client.get(LASTFM_BASE, params={
            "method": method, "api_key": LASTFM_KEY, "format": "json", **params
        })
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["message"])
        return data


class SearchBody(BaseModel):
    q: str
    ai: bool = False


def _substring_match(q: str, tracks: list, movies: list, games: list):
    """Literal substring match across titles, artists, directors, genres, tags."""
    ql = q.lower()
    def mt(t): return (
        ql in t["name"].lower() or ql in t.get("artist", "").lower()
        or any(ql in tag.lower() for tag in t.get("tags", []))
        or any(ql in g.lower()   for g   in t.get("genres", []))
    )
    def mm(m): return (
        ql in m["title"].lower() or ql in m.get("director", "").lower()
        or any(ql in g.lower() for g in m.get("genres", []))
    )
    def mg(g): return (
        ql in g["title"].lower()
        or any(ql in g2.lower()  for g2  in g.get("genres", []))
        or any(ql in tag.lower() for tag in g.get("tags", []))
    )
    return (
        [t for t in tracks if mt(t)],
        [m for m in movies if mm(m)],
        [gm for gm in games if mg(gm)],
    )


def _embedding_match(q: str, tables: tuple[str, ...], top_per_domain: int = 3):
    """Semantic supplement: embed query, run pgvector cosine for top items per domain.
    Only queries the tables passed in — skip domains that already have enough substring hits."""
    if not tables:
        return {}
    model = _get_st_model()
    vec = model.encode(q, normalize_embeddings=True)
    vec_str = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    conn = get_conn()
    out: dict[str, list] = {t: [] for t in tables}
    try:
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"""
                    SELECT *, 1 - (embedding <=> %s::vector) AS _score
                    FROM {table} WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (vec_str, vec_str, top_per_domain))
                rows = [dict(r) for r in cur.fetchall()]
                for r in rows:
                    r["_score"] = round(max(0.0, min(1.0, (float(r["_score"]) - 0.5) * 2)) * 100)
                    r.pop("embedding", None)
                out[table] = serialize_rows(rows)
    finally:
        conn.close()
    return out


@router.post("/search")
async def search(body: SearchBody):
    q = body.q.strip()
    if not q:
        return {"tracks": [], "movies": [], "games": [], "explanation": None}

    tracks = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
    movies = cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
    games  = cached_query("games",  "SELECT * FROM games  ORDER BY rating DESC")

    if not body.ai:
        SPARSE_THRESHOLD = 3
        sub_t, sub_m, sub_g = _substring_match(q, tracks, movies, games)

        sparse_map = {"tracks": sub_t, "movies": sub_m, "games": sub_g}
        sparse_tables = tuple(t for t, hits in sparse_map.items() if len(hits) < SPARSE_THRESHOLD)

        emb: dict[str, list] = {}
        if sparse_tables:
            try:
                emb = await asyncio.to_thread(_embedding_match, q, sparse_tables, 3)
            except Exception:
                emb = {}

        def merge(sub: list, emb_list: list, sub_limit: int = 8, emb_limit: int = 3):
            seen = {x["id"] for x in sub[:sub_limit]}
            extras = [e for e in emb_list if e["id"] not in seen][:emb_limit]
            return sub[:sub_limit] + extras

        return {
            "tracks":      merge(sub_t, emb.get("tracks", [])),
            "movies":      merge(sub_m, emb.get("movies", [])),
            "games":       merge(sub_g, emb.get("games", [])),
            "explanation": None,
        }

    if not _HAS_ANTHROPIC:
        raise HTTPException(status_code=503, detail="anthropic package not installed")
    if not ANTHROPIC_KEY or ANTHROPIC_KEY in ("soon", ""):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not set")

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
            f'Respond with this exact JSON (raw, no markdown):\n'
            f'{{"e":"one sentence about what you found","t":[track ids],"m":[movie ids],"g":[game ids]}}\n\n'
            f'Catalog: {json.dumps(catalog, separators=(",",":"))}'
        }]
    )

    raw = msg.content[0].text.strip()
    result = None
    try:
        result = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(0))
            except Exception:
                result = None
    if result is None:
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


@router.get("/music/track")
async def get_track(artist: str = Query(...), track: str = Query(...)):
    data = await _lfm("track.getInfo", artist=artist, track=track)
    t = data["track"]

    image = None
    if "album" in t and "image" in t["album"]:
        for img in reversed(t["album"]["image"]):
            if img["#text"]:
                image = img["#text"]
                break

    return {
        "name":        t["name"],
        "artist":      t["artist"]["name"],
        "duration_ms": int(t.get("duration", 0)),
        "listeners":   int(t.get("listeners", 0)),
        "playcount":   int(t.get("playcount", 0)),
        "tags":        [tag["name"] for tag in t.get("toptags", {}).get("tag", [])],
        "summary":     t.get("wiki", {}).get("summary", "").split('<a href')[0].strip(),
        "image":       image,
        "url":         t.get("url"),
        "mbid":        t.get("mbid"),
        "album":       t.get("album", {}).get("title"),
    }
