import os
import re
import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import get_conn, serialize_rows

try:
    from anthropic import Anthropic
    _llm = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None
except Exception:
    _llm = None


router = APIRouter(prefix="/cross", tags=["cross"])

_LLM_MODEL = "claude-haiku-4-5-20251001"
_EXPLAIN_BATCH = 12

TABLE = {"track": "tracks", "movie": "movies", "game": "games"}
TAG_FIELDS = {
    "track": ("genres", "tags"),
    "movie": ("genres", "keywords"),
    "game":  ("genres", "tags"),
}

SHARED_TAG_BONUS = 0.07
MAX_TAG_BONUS    = 0.35
POOL_MULT        = 4
DISPLAY_BASELINE = 0.50
DISPLAY_SCALE    = 2.0

_cross_cache: dict = {}


def _calibrate(raw: float) -> int:
    return round(max(0.0, min(1.0, (raw - DISPLAY_BASELINE) * DISPLAY_SCALE)) * 100)


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


def _fetch_cached_explanations(cur, keys: list[tuple]) -> dict[tuple, str]:
    if not keys:
        return {}
    placeholders = ",".join(["(%s,%s,%s,%s)"] * len(keys))
    flat: list = []
    for k in keys: flat.extend(k)
    cur.execute(
        f"""SELECT anchor_type, anchor_id, rec_type, rec_id, explanation
            FROM cross_explanations
            WHERE (anchor_type, anchor_id, rec_type, rec_id) IN ({placeholders})""",
        flat,
    )
    return {
        (r["anchor_type"], r["anchor_id"], r["rec_type"], r["rec_id"]): r["explanation"]
        for r in cur.fetchall()
    }


def _generate_explanations(cur, pairs: list[tuple]) -> dict[tuple, str]:
    if not pairs or _llm is None:
        return {}

    def _instruction(score: int) -> str:
        if score >= 75:
            return "Strong match — lead confidently with the shared trait. Format: \"both [share/feel/have] X\"."
        if score >= 55:
            return "Medium match — describe what they share, then briefly contrast a key difference. Format: \"share X, but differ in Y\"."
        return "Weak match — start with \"loosely connected\". Briefly mention the thin shared element, then explicitly contrast difference. Format: \"loosely connected by X — but one is Y while other is Z\"."

    new: dict[tuple, str] = {}
    for i in range(0, len(pairs), _EXPLAIN_BATCH):
        batch = pairs[i:i + _EXPLAIN_BATCH]
        pair_lines: list[str] = []
        for idx, (_, _, a_vibe, _, _, r_vibe, score) in enumerate(batch, 1):
            pair_lines.append(
                f"{idx}. [score {score}%] {_instruction(score)}\n"
                f"  A: {(a_vibe or '').strip()[:600]}\n"
                f"  B: {(r_vibe or '').strip()[:600]}"
            )
        prompt = (
            "For each pair below, write ONE short sentence (max 18 words, start lowercase, no period) "
            "explaining in PLAIN ENGLISH the relationship between A and B. Each pair has a score and an "
            "instruction telling you the tone — follow it precisely. Be concrete, not poetic.\n\n"
            "RULES:\n"
            "  - Everyday words only. NEVER use: catharsis, brooding, melancholic, sublime, "
            "ethereal, visceral, transcendent, evocative, primal, existential.\n"
            "  - No literary metaphors. No \"whispered rage\", no \"thunderous\", no \"haze\".\n"
            "  - Don't name titles, plots, mechanics, instruments, or people.\n"
            "  - For weak/medium matches, the contrast part (\"but\", \"while\", \"though\") is mandatory.\n\n"
            "Good examples by score band:\n"
            "  [87%] both feel like driving alone at night — calm but a little lonely\n"
            "  [83%] high-energy and aggressive, all about pushing forward without stopping\n"
            "  [62%] share a slow contemplative pace, but one is hopeful while the other stays sad\n"
            "  [57%] both have young-hero energy, though one is hopeful and bright while the other is dark and defiant\n"
            "  [48%] loosely connected by atmospheric exploration — but one is medieval fantasy while the other is urban modern\n\n"
            f"Return raw JSON: {{\"explanations\":[\"...\",\"...\"]}} — exactly {len(batch)} strings, same order.\n\n"
            "Pairs:\n" + "\n\n".join(pair_lines)
        )
        try:
            msg = _llm.messages.create(
                model=_LLM_MODEL,
                max_tokens=80 * len(batch),
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            try:
                parsed = json.loads(raw)
            except Exception:
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                parsed = json.loads(m.group(0)) if m else {}
            sentences = parsed.get("explanations", [])
        except Exception:
            sentences = []

        for j, (a_t, a_id, _, r_t, r_id, _, _) in enumerate(batch):
            sent = sentences[j].strip() if j < len(sentences) and isinstance(sentences[j], str) else ""
            if sent:
                new[(a_t, a_id, r_t, r_id)] = sent

    if new:
        rows = [(a_t, a_id, r_t, r_id, expl) for (a_t, a_id, r_t, r_id), expl in new.items()]
        flat_rows: list = []
        for r in rows: flat_rows.extend(r)
        cur.execute(
            f"""INSERT INTO cross_explanations (anchor_type, anchor_id, rec_type, rec_id, explanation)
                VALUES {",".join(["(%s,%s,%s,%s,%s)"] * len(rows))}
                ON CONFLICT (anchor_type, anchor_id, rec_type, rec_id) DO NOTHING""",
            flat_rows,
        )

    return new


def _node_payload(row: dict, item_type: str, is_liked: bool) -> dict:
    return {
        "id":           f"{item_type}-{row['id']}",
        "raw_id":       row["id"],
        "type":         item_type,
        "title":        row.get("title") or row.get("name") or "—",
        "image_url":    row.get("poster_url") or row.get("image_url"),
        "artist":       row.get("artist"),
        "release_year": row.get("release_year"),
        "genres":       (row.get("genres") or [])[:3],
        "is_liked":     is_liked,
    }


@router.get("/graph/{uid}")
def discover_graph(uid: str, k: int = Query(1, ge=1, le=3)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.*, 'track' AS _item_type FROM tracks t
                JOIN likes l ON l.item_id = t.id AND l.item_type = 'track'
                WHERE l.user_uid = %s AND t.embedding IS NOT NULL
            """, (uid,))
            tracks = [dict(r) for r in cur.fetchall()]
            cur.execute("""
                SELECT m.*, 'movie' AS _item_type FROM movies m
                JOIN likes l ON l.item_id = m.id AND l.item_type = 'movie'
                WHERE l.user_uid = %s AND m.embedding IS NOT NULL
            """, (uid,))
            movies = [dict(r) for r in cur.fetchall()]
            cur.execute("""
                SELECT g.*, 'game' AS _item_type FROM games g
                JOIN likes l ON l.item_id = g.id AND l.item_type = 'game'
                WHERE l.user_uid = %s AND g.embedding IS NOT NULL
            """, (uid,))
            games = [dict(r) for r in cur.fetchall()]

            anchors = tracks + movies + games
            if not anchors:
                return {"nodes": [], "edges": []}

            nodes: dict[str, dict] = {}
            for a in anchors:
                node = _node_payload(a, a["_item_type"], is_liked=True)
                nodes[node["id"]] = node

            edges: list[dict] = []
            edge_keys: list[tuple] = []

            for a in anchors:
                a_type = a["_item_type"]
                a_id   = a["id"]
                a_vec  = a["embedding"]
                a_tags = _collect_tags(a, a_type)

                for other_type, other_table in [(t, TABLE[t]) for t in TABLE if t != a_type]:
                    cur.execute(f"""
                        SELECT *, 1 - (embedding <=> %s::vector) AS _semantic
                        FROM {other_table}
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (a_vec, a_vec, k * POOL_MULT))
                    pool = [dict(r) for r in cur.fetchall()]

                    scored: list[tuple[float, dict, list[str]]] = []
                    for r in pool:
                        r_tags = _collect_tags(r, other_type)
                        shared = a_tags & r_tags
                        bonus = min(MAX_TAG_BONUS, len(shared) * SHARED_TAG_BONUS)
                        hybrid = min(1.0, float(r["_semantic"]) + bonus)
                        scored.append((hybrid, r, sorted(shared)[:3]))
                    scored.sort(key=lambda x: -x[0])

                    for hybrid, r, shared_tags in scored[:k]:
                        r_id    = r["id"]
                        node_id = f"{other_type}-{r_id}"
                        if node_id not in nodes:
                            nodes[node_id] = _node_payload(r, other_type, is_liked=False)
                        edges.append({
                            "source":      f"{a_type}-{a_id}",
                            "target":      node_id,
                            "score":       _calibrate(hybrid),
                            "shared_tags": shared_tags,
                            "explanation": None,
                        })
                        edge_keys.append((a_type, a_id, other_type, r_id))

            cached = _fetch_cached_explanations(cur, edge_keys)
            for i, key in enumerate(edge_keys):
                edges[i]["explanation"] = cached.get(key)
    finally:
        conn.close()

    return {"nodes": list(nodes.values()), "edges": edges}


class _ExplainPair(BaseModel):
    anchor_type: str
    anchor_id:   int
    rec_type:    str
    rec_id:      int
    score:       int = 70


class _ExplainRequest(BaseModel):
    pairs: list[_ExplainPair]


@router.post("/explain")
def explain_pairs(body: _ExplainRequest):
    if not body.pairs:
        return {}
    for p in body.pairs:
        if p.anchor_type not in TABLE or p.rec_type not in TABLE:
            raise HTTPException(status_code=400, detail="Invalid type")

    keys = [(p.anchor_type, p.anchor_id, p.rec_type, p.rec_id) for p in body.pairs]
    score_by_key = {(p.anchor_type, p.anchor_id, p.rec_type, p.rec_id): p.score for p in body.pairs}
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cached = _fetch_cached_explanations(cur, keys)
            missing = [k for k in keys if k not in cached]

            new: dict[tuple, str] = {}
            if missing:
                by_domain: dict[str, set[int]] = {"track": set(), "movie": set(), "game": set()}
                for a_t, a_id, r_t, r_id in missing:
                    by_domain[a_t].add(a_id)
                    by_domain[r_t].add(r_id)

                vibes: dict[tuple[str, int], str] = {}
                for t, ids in by_domain.items():
                    if not ids: continue
                    cur.execute(
                        f"SELECT id, vibe_text FROM {TABLE[t]} WHERE id = ANY(%s)",
                        (list(ids),),
                    )
                    for r in cur.fetchall():
                        vibes[(t, r["id"])] = r["vibe_text"] or ""

                pairs_to_gen = [
                    (a_t, a_id, vibes.get((a_t, a_id), ""), r_t, r_id, vibes.get((r_t, r_id), ""),
                     score_by_key.get((a_t, a_id, r_t, r_id), 70))
                    for a_t, a_id, r_t, r_id in missing
                ]
                new = _generate_explanations(cur, pairs_to_gen)
                conn.commit()
    finally:
        conn.close()

    out: dict[str, str] = {}
    for a_t, a_id, r_t, r_id in keys:
        expl = cached.get((a_t, a_id, r_t, r_id)) or new.get((a_t, a_id, r_t, r_id))
        if expl:
            out[f"{a_t}-{a_id}__{r_t}-{r_id}"] = expl
    return out


@router.get("/{anchor_type}/{anchor_id}")
def cross_recommendations(anchor_type: str, anchor_id: int, k: int = Query(5, ge=1, le=20)):
    if anchor_type not in TABLE:
        raise HTTPException(status_code=400, detail="Invalid anchor_type")

    cache_key = (anchor_type, anchor_id, k)
    if cache_key in _cross_cache:
        return _cross_cache[cache_key]

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
                raise HTTPException(status_code=409, detail="Anchor has no embedding")

            anchor_tags = _collect_tags(anchor, anchor_type)
            result: dict = {"anchor": serialize_rows([anchor])[0]}
            anchor_vec = anchor["embedding"]

            for other in other_types:
                other_table = TABLE[other]
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

                pool.sort(key=lambda r: -r["_raw_score"])
                result[other_table] = serialize_rows(pool[:k])
            result["anchor"].pop("embedding", None)
    finally:
        conn.close()

    _cross_cache[cache_key] = result
    return result
