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

REMOVE = {
    "early access", "steam achievements", "steam cloud", "steam trading cards",
    "steam-trading-cards", "steam leaderboards", "steam workshop",
    "full controller support", "partial controller support", "controller support",
    "includes level editor", "commentary available",
    "valve anti-cheat enabled", "in-app purchases", "free to play",
    "exclusive", "true exclusive", "w10 exclusive", "xbox exclusive",
    "pc exclusive", "console exclusive",
    "remote play on tablet", "remote play on phone", "remote play on tv",
    "remote play together",
    "pvp", "pve", "online pvp", "online multiplayer", "local multiplayer",
    "cross-platform multiplayer", "split screen", "multiplayer",
    "shared/split screen co-op", "shared/split screen pvp",
    "4 player local", "lan co-op", "co-op campaign", "co-op multiplayer",
    "co op multiplayer", "family sharing",
    "overlay", "cloud saves", "achievements", "captions available",
    "vr supported", "trackir", "3d vision",
    "online", "offline", "console",
    "mature", "teen", "everyone", "everyone 10+", "adults only", "rating pending",
    "controller", "vr", "mouse only",
    "gore", "violent", "violence", "blood", "nudity", "sexual content",
    "lootboxes", "microtransactions", "ea play", "in development",
    "skins", "loot",
    "memes", "illuminati",
    "masterpiece", "emotional", "relaxing", "replay value",
    "experience", "atmosphere", "immersive",
    "short", "remake", "story",
    "classic", "great soundtrack", "stats", "beautiful",
    "atmospheric",
    "battle", "friends", "night", "ship", "cats", "hero", "island",
    "city", "prison", "1-bit", "japanese", "combat",
    "batman", "lara croft", "assassin",
    "lgbtq+",
    "new york", "russia", "mexico", "forest",
    "voxel", "photorealistic", "photorealism", "3d vision",
    "science", "mod", "politics", "conversation", "destruction",
    "kickstarter",
    "coop",           
    "cartoon",        
    "tank",           
    "paranormal",     
    "street racing", "cars", "drift", "racing-game",
    "festival", "sprint", "winter", "autumn", "extreme", "photorealism",
    "karaihb", "controversial", "first person mod",
    "tir", "mac-plus", "dinn", "obra",
    "celeste", "xna", "fna", "miniboss", "towerfall", "matt-makes-games",
    "great-graphics", "character-development",
    "steam", "meat", "category",
    "build", "life", "race", "character", "work", "love", "light",
    "learn", "obstacles", "delivery", "journey", "treasure", "collect",
    "food", "water", "sea", "sun", "crash", "health", "alien",
    "fight", "nature", "weapons", "planets", "galaxy", "sky",
    "guns", "trees", "wasteland", "solo", "team",
    "interactive movie", "interactive game",
    "planetary", "philisophical",
    "modding", "cube", "procedural-generation",
    "explore", "simple", "modern",
    "lifestyle", "reality-based", "family-simulator",
    "overlay", "achievements",
    "1980s",
    "ww2", "history",
    "mmo",  
    "dungeons", "epic",
    "arena", "tv", "map", "hd", "gaming", "balance", "endless",
    "skill", "online", "offline", "evil",
    "grappling-hook", "collectathon",
}

MERGE = {
    "cooperative":        "Co-op",
    "multiplayer co-op":  "Co-op",
    "co op":              "Co-op",
    "online co-op":       "Co-op",
    "local co-op":        "Co-op",
    "e-sports":           "Esports",
    "esports":            "Esports",
    "first person":       "First-Person",
    "third person":       "Third-Person",
    "third-person":       "Third-Person",
    "open-world":         "Open World",
    "third person shooter": "Third-Person Shooter",
    "fps":                "First-Person",
    "first-person shooter": "First-Person",
    "3rd-person perspective": "Third-Person",
    "3rd-person":            "Third-Person",
    "puzzles":               "Puzzle",
    "story":                 "Story Rich",
    "mmo":                   "MMO",
    "realism":               "Realistic",
    "paranormal":            "Supernatural",
    "nonlinear":             "Non-linear",
    "action rts":            "RTS",
    "role playing game":     "RPG",
    "looter shooter":        "Shooter",
    "hero shooter":          "Shooter",
    "arena shooter":         "Shooter",
    "2d fighter":            "Fighting",
    "immersive sim":         "Simulation",

    "role-playing":       "RPG",
    "role playing":       "RPG",
    "hack and slash":     "Hack & Slash",
    "hack-and-slash":     "Hack & Slash",
    "real-time strategy": "RTS",
    "real time strategy": "RTS",
    "turn-based strategy": "Turn-Based Strategy",
    "turn based strategy": "Turn-Based Strategy",
    "battle royale":      "Battle Royale",
}


import re as _re

def normalise_tag(tag: str) -> str | None:
    low = tag.lower().strip()
    if low in REMOVE:
        return None
    if _re.search(r'[^\x00-\x7F]', tag):
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
