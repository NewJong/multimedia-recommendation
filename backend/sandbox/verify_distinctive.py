"""Verify distinctive picks for two users: explain why a specific track gets 100%."""
import os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

import psycopg2, psycopg2.extras
from database import cached_query
from routers.compare import _distinctive_picks, _likes_by_type, _get_name


UID1 = "Rpbs4oNLQEg2H2BbgQZs8DoYcyz2"   # viewer
UID2 = "tgnSdDUJFnaDkK03W2UgTiVXV3W2"   # profile being viewed


def main():
    name1 = _get_name(UID1)
    name2 = _get_name(UID2)
    print(f"\nViewer: {name1} ({UID1[:8]}…)")
    print(f"Target: {name2} ({UID2[:8]}…)\n")

    likes1 = _likes_by_type(UID1)
    likes2 = _likes_by_type(UID2)

    tracks = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
    track_by_id = {t["id"]: t for t in tracks}

    print(f"=== TRACK LIKES ===")
    print(f"{name1}: {len(likes1['track'])} tracks")
    print(f"{name2}: {len(likes2['track'])} tracks")

    common = likes1["track"] & likes2["track"]
    only_2  = likes2["track"] - likes1["track"]
    print(f"Common: {len(common)} | Only-{name2}: {len(only_2)}\n")

    # Run distinctive picks
    picks = _distinctive_picks(likes1["track"], likes2["track"], tracks, ["genres", "tags"])

    print(f"=== TOP DISTINCTIVE PICKS ({name2} → {name1}) ===")
    for i, (item, score, matched_tags) in enumerate(picks, 1):
        print(f"  {i}. [{score:>3}%]  {item['name']} — {item.get('artist', '')}")
        print(f"        Matched: {matched_tags}")
        print(f"        Track tags: {(item.get('genres') or []) + (item.get('tags') or [])}")

    # Deep-dive on top pick
    if picks:
        top_item, top_score, top_tags = picks[0]
        print(f"\n=== WHY '{top_item['name']}' = {top_score}% ===\n")

        top_tags_lower = {t.lower() for f in ("genres", "tags") for t in (top_item.get(f) or [])}
        print(f"All tags on this track: {sorted(top_tags_lower)}\n")

        # For each tag of Teenagers, check presence in both users
        print(f"{'Tag':<25}  {'In {name1}?':>15}  {'In {name2}?':>15}")
        print(f"{'-'*25}  {'-'*15}  {'-'*15}")
        for tag in sorted(top_tags_lower):
            in_1 = any(
                tag in {t.lower() for f in ("genres", "tags") for t in (track_by_id[tid].get(f) or [])}
                for tid in likes1["track"]
            )
            in_2 = any(
                tag in {t.lower() for f in ("genres", "tags") for t in (track_by_id[tid].get(f) or [])}
                for tid in likes2["track"]
            )
            print(f"  {tag:<23}  {'YES' if in_1 else '—':>15}  {'YES' if in_2 else '—':>15}")

        print(f"\nThe 100% score means: 'Teenagers' has the **highest distinctive score** among all")
        print(f"of {name2}'s liked tracks that {name1} doesn't have. Score is normalized so top = 100%.")
        print(f"It does NOT mean '100% semantic match' — it means '#1 most-different-from-{name1}'s-taste'.")


if __name__ == "__main__":
    main()
