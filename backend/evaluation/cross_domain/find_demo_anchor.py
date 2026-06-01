import os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

import psycopg2, psycopg2.extras
from routers.cross import TABLE, _collect_tags, SHARED_TAG_BONUS, MAX_TAG_BONUS, POOL_MULT, _calibrate


def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)


def top1_score(cur, anchor: dict, anchor_type: str, other_type: str) -> tuple[int, str]:
    other_table = TABLE[other_type]
    cur.execute(f"""
        SELECT *, 1 - (embedding <=> %s::vector) AS _sem
        FROM {other_table} WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector LIMIT %s
    """, (anchor["embedding"], anchor["embedding"], 4 * POOL_MULT))
    pool = [dict(r) for r in cur.fetchall()]

    a_tags = _collect_tags(anchor, anchor_type)
    best_hybrid = 0.0
    best_title = ""
    for r in pool:
        r_tags = _collect_tags(r, other_type)
        bonus = min(MAX_TAG_BONUS, len(a_tags & r_tags) * SHARED_TAG_BONUS)
        hybrid = min(1.0, float(r["_sem"]) + bonus)
        if hybrid > best_hybrid:
            best_hybrid = hybrid
            best_title = r.get("title") or r.get("name") or "—"
    return _calibrate(best_hybrid), best_title


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM movies WHERE embedding IS NOT NULL")
            movies = [dict(r) for r in cur.fetchall()]

            results = []
            for m in movies:
                track_score, track_title = top1_score(cur, m, "movie", "track")
                game_score,  game_title  = top1_score(cur, m, "movie", "game")
                # Score the candidate by MIN of two — best demo means BOTH look good.
                min_score = min(track_score, game_score)
                results.append({
                    "title":       m["title"],
                    "track_score": track_score,
                    "track":       track_title,
                    "game_score":  game_score,
                    "game":        game_title,
                    "min_score":   min_score,
                    "avg_score":   (track_score + game_score) / 2,
                })

            results.sort(key=lambda r: (-r["min_score"], -r["avg_score"]))

            print(f"\n{'Movie':<35} {'Top Track':<35} {'%':>5}  {'Top Game':<35} {'%':>5}  {'Min':>5}")
            print("─" * 130)
            for r in results[:15]:
                print(f"{r['title'][:34]:<35} {r['track'][:34]:<35} {r['track_score']:>4}%  "
                      f"{r['game'][:34]:<35} {r['game_score']:>4}%  {r['min_score']:>4}%")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
