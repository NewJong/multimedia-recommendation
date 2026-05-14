import re
from fastapi import APIRouter, HTTPException, Query
from database import get_conn, serialize_rows

router = APIRouter(prefix="/cross", tags=["cross"])

TABLE = {"track": "tracks", "movie": "movies", "game": "games"}
TAG_FIELDS = {
    "track": ("genres", "tags"),
    "movie": ("genres", "keywords"),
    "game":  ("genres", "tags"),
}

# Hybrid scoring: semantic embedding similarity + structural tag-overlap bonus.
# Pure semantic on a general-purpose 22M-param model (all-MiniLM-L6-v2) tends to
# cap cross-domain pairs in 0.5–0.7 because movies vs games use different vocab
# (plot vs gameplay). Adding a small bonus per shared tag rewards franchise/
# theme overlap that the embedding doesn't fully capture on its own.
SHARED_TAG_BONUS = 0.07   # per shared tag (lowercased)
MAX_TAG_BONUS    = 0.35   # cap so semantic still dominates
POOL_MULT        = 4      # over-fetch from pgvector, then re-rank by hybrid

# Display calibration: LLM-augmented vibe-space embeddings cluster all items in
# a narrow band (~55–95% raw cosine) because every vibe_text uses the same
# experiential vocabulary by design. Random pairs land at ~58–62%, so displaying
# raw 60% as "60% match" feels misleading. We linearly remap [50, 100] → [0, 100]
# so that the displayed score reflects perceived match strength:
#   raw  0.50 →  0%   (noise floor)
#   raw  0.75 → 50%
#   raw  0.90 → 80%
#   raw  1.00 → 100%
# The raw semantic value is still exposed as _semantic_score for transparency.
DISPLAY_BASELINE = 0.50
DISPLAY_SCALE    = 2.0


def _calibrate(raw: float) -> int:
    """Map raw cosine-like score [0, 1] to displayed percentage [0, 100]."""
    return round(max(0.0, min(1.0, (raw - DISPLAY_BASELINE) * DISPLAY_SCALE)) * 100)

# Title tokens help catch franchise matches across domains
# (e.g. "Spider-Man" movie ↔ "Marvel's Spider-Man" game).
TITLE_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "your", "this", "that",
    "edition", "remaster", "remastered", "definitive", "ultimate", "complete",
    "deluxe", "anniversary", "collection", "trilogy", "marvels", "marvel",
}
_TOKEN_RE = re.compile(r"[\w\-]+", re.UNICODE)


def _title_tokens(title: str | None) -> set[str]:
    if not title: return set()
    return {t for t in _TOKEN_RE.findall(title.lower()) if len(t) >= 4 and t not in TITLE_STOPWORDS}


def _collect_tags(row: dict, item_type: str) -> set[str]:
    out: set[str] = set()
    for f in TAG_FIELDS[item_type]:
        for v in row.get(f) or []:
            if v: out.add(str(v).lower())
    out |= _title_tokens(row.get("title") or row.get("name"))
    return out


@router.get("/{anchor_type}/{anchor_id}")
def cross_recommendations(anchor_type: str, anchor_id: int, k: int = Query(5, ge=1, le=20)):
    if anchor_type not in TABLE:
        raise HTTPException(status_code=400, detail="Invalid anchor_type")

    anchor_table = TABLE[anchor_type]
    other_types = [t for t in TABLE if t != anchor_type]

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {anchor_table} WHERE id = %s", (anchor_id,))
            anchor_row = cur.fetchone()
            if not anchor_row:
                raise HTTPException(status_code=404, detail="Anchor not found")
            anchor = dict(anchor_row)
            if anchor.get("embedding") is None:
                raise HTTPException(status_code=409, detail="Anchor has no embedding — run embed_items.py")

            anchor_tags = _collect_tags(anchor, anchor_type)
            result: dict = {"anchor": serialize_rows([anchor])[0]}
            # anchor's own embedding is a string like "[0.1,0.2,...]" via pgvector;
            # casting it back to ::vector in the query is clean and avoids parsing here.
            anchor_vec = anchor["embedding"]

            for other in other_types:
                other_table = TABLE[other]
                # Over-fetch by semantic distance, then re-rank in Python by hybrid score.
                cur.execute(f"""
                    SELECT *, 1 - (embedding <=> %s::vector) AS _semantic
                    FROM {other_table}
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (anchor_vec, anchor_vec, k * POOL_MULT))
                pool = [dict(r) for r in cur.fetchall()]

                for r in pool:
                    cand_tags = _collect_tags(r, other)
                    shared = anchor_tags & cand_tags
                    bonus = min(MAX_TAG_BONUS, len(shared) * SHARED_TAG_BONUS)
                    hybrid = min(1.0, float(r["_semantic"]) + bonus)
                    r["_score"] = _calibrate(hybrid)
                    r["_raw_score"] = round(hybrid * 100)
                    r["_semantic_score"] = round(float(r["_semantic"]) * 100)
                    r["_shared_tags"] = sorted(shared)[:3]
                    r.pop("embedding", None)
                    r.pop("_semantic", None)

                # Sort by raw hybrid (more granular than the rounded display score).
                pool.sort(key=lambda r: -r["_raw_score"])
                result[other_table] = serialize_rows(pool[:k])
            # also strip the anchor embedding from the response
            result["anchor"].pop("embedding", None)
    finally:
        conn.close()

    return result
