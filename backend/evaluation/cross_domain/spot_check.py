import os, sys, json
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

import psycopg2, psycopg2.extras
from routers.cross import TABLE, _collect_tags, SHARED_TAG_BONUS, MAX_TAG_BONUS, POOL_MULT, _calibrate, _generate_explanations


def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)


ANCHORS_BY_TITLE = [
    ("movie", "The Dark Knight"),
    ("movie", "Pulp Fiction"),
    ("movie", "Spider-Man"),
    ("movie", "La La Land"),
    ("game",  "The Witcher 3: Wild Hunt"),
    ("game",  "Doom"),
    ("game",  "Stardew Valley"),
    ("track", "Black"),
    ("track", "Hurt"),
]


def fetch_anchor(cur, item_type: str, title_or_name: str):
    table = TABLE[item_type]
    name_col = "name" if item_type == "track" else "title"
    cur.execute(f"SELECT * FROM {table} WHERE {name_col} ILIKE %s AND embedding IS NOT NULL ORDER BY id LIMIT 1",
                (f"%{title_or_name}%",))
    r = cur.fetchone()
    return dict(r) if r else None


def cross_for_anchor(cur, anchor: dict, anchor_type: str, other_type: str, k: int = 3):
    other_table = TABLE[other_type]
    cur.execute(f"""
        SELECT *, 1 - (embedding <=> %s::vector) AS _sem
        FROM {other_table} WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector LIMIT %s
    """, (anchor["embedding"], anchor["embedding"], k * POOL_MULT))
    pool = [dict(r) for r in cur.fetchall()]

    anchor_tags = _collect_tags(anchor, anchor_type)
    scored = []
    for r in pool:
        r_tags = _collect_tags(r, other_type)
        shared = anchor_tags & r_tags
        bonus = min(MAX_TAG_BONUS, len(shared) * SHARED_TAG_BONUS)
        hybrid = min(1.0, float(r["_sem"]) + bonus)
        scored.append((r, hybrid, float(r["_sem"]), sorted(shared)[:4]))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


def title_of(item, item_type):
    return item.get("title") or item.get("name") or "—"


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for anchor_type, title in ANCHORS_BY_TITLE:
                anchor = fetch_anchor(cur, anchor_type, title)
                if not anchor:
                    print(f"\n⚠️  '{title}' ({anchor_type}) not found in DB — skipping\n")
                    continue

                print(f"\n{'═'*92}")
                print(f"  ANCHOR  [{anchor_type.upper()}]  {title_of(anchor, anchor_type)}")
                print(f"  Genres: {', '.join((anchor.get('genres') or [])[:5])}")
                print(f"  vibe_text: {(anchor.get('vibe_text') or '')[:200]}…")
                print(f"{'═'*92}")

                pairs_for_llm = []
                results = []

                for other in [t for t in TABLE if t != anchor_type]:
                    matches = cross_for_anchor(cur, anchor, anchor_type, other, k=10)
                    print(f"\n  → Top-10 {other.upper()}S:")
                    for rank, (item, hybrid, sem, shared) in enumerate(matches, 1):
                        cal = _calibrate(hybrid)
                        print(f"    {rank}. [{cal:>2}%]  {title_of(item, other):<50}  "
                              f"sem={sem:.3f}  shared={shared if shared else '∅'}")
                        results.append((other, item, cal, shared))
                        pairs_for_llm.append((
                            anchor_type, anchor["id"], anchor.get("vibe_text") or "",
                            other, item["id"], item.get("vibe_text") or "",
                            cal,
                        ))

                print(f"\n  AI EXPLANATIONS (Claude Haiku, batched):")
                expls = _generate_explanations(cur, pairs_for_llm)
                for other, item, cal, shared in results:
                    key = (anchor_type, anchor["id"], other, item["id"])
                    expl = expls.get(key, "(no explanation)")
                    print(f"    [{cal}%] {title_of(item, other)[:45]:<45} → {expl}")

            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
