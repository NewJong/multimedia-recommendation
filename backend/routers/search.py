import os, json
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import cached_query

try:
    import anthropic as _anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

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


@router.post("/search")
async def search(body: SearchBody):
    q = body.q.strip()
    if not q:
        return {"tracks": [], "movies": [], "games": [], "explanation": None}

    tracks = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
    movies = cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
    games  = cached_query("games",  "SELECT * FROM games  ORDER BY rating DESC")

    if not body.ai:
        ql = q.lower()
        def mt(t): return (
            ql in t["name"].lower() or ql in t.get("artist", "").lower()
            or ql in t.get("genre", "").lower()
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
        return {
            "tracks":      [t for t in tracks if mt(t)][:12],
            "movies":      [m for m in movies if mm(m)][:12],
            "games":       [gm for gm in games if mg(gm)][:12],
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
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
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
