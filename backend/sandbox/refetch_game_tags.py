"""
Re-fetches ALL tags from RAWG for every game in DB, applies noise filter,
then runs the full normalize pipeline. Fixes the [:12] truncation that was
hiding meaningful tags like Western, Hunting, Historical, Crime etc.
Run: python refetch_game_tags.py
"""
import sys, html as _html, re, time, httpx, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

API_KEY = os.getenv("RAWG_API_KEY")
DB_URL  = os.getenv("DATABASE_URL")
BASE    = "https://api.rawg.io/api"

GENRE_MAP = {
    "action": "Action", "adventure": "Adventure", "role-playing-games-rpg": "RPG",
    "shooter": "Shooter", "strategy": "Strategy", "simulation": "Simulation",
    "sports": "Sports", "racing": "Racing", "fighting": "Fighting",
    "puzzle": "Puzzle", "platformer": "Platformer", "massively-multiplayer": "MMO",
    "arcade": "Arcade", "indie": "Indie", "casual": "Casual",
    "family": "Family", "card": "Card", "board-games": "Board Games",
}

# Same NOISE_TAGS as seed_games — anything the normalize script would also kill
NOISE_TAGS = {
    "singleplayer", "multiplayer", "steam achievements", "full controller support",
    "steam cloud", "great soundtrack", "stats", "steam trading cards",
    "steam leaderboards", "includes level editor", "commentary available",
    "partial controller support", "controller support", "valve anti-cheat enabled",
    "in-app purchases", "free to play", "vr mod",
    "early access", "mature", "teen", "everyone", "everyone 10+", "adults only",
    "moddable", "mod support", "controller", "vr",
    "pvp", "pve", "online pvp", "online multiplayer", "local multiplayer",
    "cross-platform multiplayer", "split screen",
    "gore", "violent", "violence", "blood", "nudity", "sexual content",
    "masterpiece", "emotional", "relaxing", "replay value",
    "short", "remake", "story",
    "classic", "atmospheric", "beautiful",
    "battle", "friends", "night", "ship", "cats", "hero", "island",
    "city", "prison", "1-bit", "japanese", "combat",
    "america",  # location noise
    "3rd-person",  # malformed duplicate of Third-Person
}

# Same MERGE as normalize_games.py
MERGE = {
    "cooperative": "Co-op", "multiplayer co-op": "Co-op", "co op": "Co-op",
    "online co-op": "Co-op", "local co-op": "Co-op",
    "e-sports": "Esports", "esports": "Esports",
    "first person": "First-Person", "third person": "Third-Person", "third-person": "Third-Person",
    "open-world": "Open World",
    "third person shooter": "Third-Person Shooter",
    "fps": "First-Person", "first-person shooter": "First-Person",
    "3rd-person perspective": "Third-Person",
    "role-playing": "RPG", "role playing": "RPG",
    "hack and slash": "Hack & Slash", "hack-and-slash": "Hack & Slash",
    "real-time strategy": "RTS", "real time strategy": "RTS",
    "turn-based strategy": "Turn-Based Strategy", "turn based strategy": "Turn-Based Strategy",
    "battle royale": "Battle Royale",
    "puzzles": "Puzzle", "story": "Story Rich",
}


def clean_tag(tag: str) -> str | None:
    low = tag.lower().strip()
    if low in NOISE_TAGS:
        return None
    canonical = MERGE.get(low)
    return canonical if canonical else tag.strip()


def dedup(tags):
    seen, result = set(), []
    for t in tags:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            result.append(t)
    return result


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

cur.execute("SELECT id, title, rawg_id, genres, tags FROM games ORDER BY id")
games = cur.fetchall()
print(f"Re-fetching tags for {len(games)} games...\n")

updated = 0
failed  = 0

for g in games:
    try:
        d = httpx.get(f"{BASE}/games/{g['rawg_id']}",
                      params={"key": API_KEY}, timeout=15).json()
        time.sleep(0.25)

        # Genres
        new_genres = [GENRE_MAP.get(ge["slug"], ge["name"]) for ge in d.get("genres", [])]
        if not new_genres:
            new_genres = list(g["genres"] or [])

        # Tags — take ALL english, apply noise+merge+dedup
        raw = [t["name"] for t in d.get("tags", []) if t.get("language") == "eng"]
        cleaned = [c for t in raw if (c := clean_tag(t)) is not None]
        new_tags = dedup(cleaned)

        old_tags = list(g["tags"] or [])
        added   = [t for t in new_tags if t not in old_tags]
        removed = [t for t in old_tags if t not in new_tags]

        cur.execute(
            "UPDATE games SET genres=%s, tags=%s WHERE id=%s",
            (new_genres, new_tags, g["id"])
        )
        conn.commit()
        updated += 1

        status = []
        if added:   status.append(f"  + {added}")
        if removed: status.append(f"  - {removed}")
        print(f"[{g['id']:3d}] {g['title']}")
        print(f"      tags: {new_tags}")
        for s in status:
            print(f"      {s}")

    except Exception as e:
        conn.rollback()
        print(f"  [err] {g['title']}: {e}")
        failed += 1

cur.close()
conn.close()
print(f"\nUpdated: {updated} | Failed: {failed}")
