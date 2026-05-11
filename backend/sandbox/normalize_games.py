"""
Cleans genres + tags for all games already in DB:
  - Removes noise tags (platform status, ESRB duplicates, technical flags)
  - Merges synonyms to canonical form
  - Deduplicates within each game
Run: python normalize_games.py
"""
import sys, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

DB_URL = os.getenv("DATABASE_URL")

# Tags that carry no taste signal — remove them
REMOVE = {
    # platform / store status
    "early access", "steam achievements", "steam cloud", "steam trading cards",
    "steam leaderboards", "steam workshop", "full controller support",
    "includes level editor", "commentary available",
    # ESRB ratings that leak into tags
    "mature", "teen", "everyone", "everyone 10+", "adults only", "rating pending",
    # technical feature flags (not about what kind of game it is)
    "moddable", "mod support",
    # pure sentiment / noise
    "classic", "great soundtrack", "stats",
    # too generic — appears in 60%+ of games, kills signal
    "atmospheric",
}

# Synonyms: any key → canonical value (title-cased)
# Keys must be lowercase
MERGE = {
    # co-op variants
    "cooperative":        "Co-op",
    "multiplayer co-op":  "Co-op",
    "co op":              "Co-op",
    "online co-op":       "Co-op",
    "local co-op":        "Co-op",
    # esports
    "e-sports":           "Esports",
    "esports":            "Esports",
    # perspective — standardise spelling
    "first person":       "First-Person",
    "third person":       "Third-Person",
    "third-person":       "Third-Person",
    # open world
    "open-world":         "Open World",
    # shooter sub-genres
    "third person shooter": "Third-Person Shooter",
    # fps — merge into First-Person (RDR2 has both FPS and First-Person as duplicates)
    "fps":                "First-Person",
    "first-person shooter": "FPS",
    # rpg
    "role-playing":       "RPG",
    "role playing":       "RPG",
    # misc
    "hack and slash":     "Hack & Slash",
    "hack-and-slash":     "Hack & Slash",
    "real-time strategy": "RTS",
    "real time strategy": "RTS",
    "turn-based strategy": "Turn-Based Strategy",
    "turn based strategy": "Turn-Based Strategy",
    "battle royale":      "Battle Royale",
}


def normalise_tag(tag: str) -> str | None:
    low = tag.lower().strip()
    if low in REMOVE:
        return None
    canonical = MERGE.get(low)
    if canonical:
        return canonical
    return tag.strip()


def normalise_list(tags: list[str]) -> list[str]:
    seen = set()
    result = []
    for tag in tags:
        cleaned = normalise_tag(tag)
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

cur.execute("SELECT id, title, genres, tags FROM games ORDER BY id")
games = cur.fetchall()

updated = 0
unchanged = 0

for g in games:
    new_genres = normalise_list(g["genres"] or [])
    new_tags   = normalise_list(g["tags"]   or [])

    if new_genres == list(g["genres"] or []) and new_tags == list(g["tags"] or []):
        unchanged += 1
        continue

    removed_genres = [x for x in (g["genres"] or []) if x not in new_genres]
    removed_tags   = [x for x in (g["tags"]   or []) if x not in new_tags]
    merged_tags    = [new_tags[i] for i, x in enumerate(new_tags)
                      if x != (g["tags"] or [])[i] if i < len(g["tags"] or [])]

    cur.execute(
        "UPDATE games SET genres=%s, tags=%s WHERE id=%s",
        (new_genres, new_tags, g["id"])
    )
    conn.commit()
    updated += 1

    changes = []
    if removed_genres: changes.append(f"genres removed: {removed_genres}")
    if removed_tags:   changes.append(f"tags removed: {removed_tags}")

    print(f"  [{g['id']:3d}] {g['title']}")
    for c in changes:
        print(f"        {c}")

cur.close()
conn.close()

print(f"\nUpdated: {updated} | Unchanged: {unchanged}")
