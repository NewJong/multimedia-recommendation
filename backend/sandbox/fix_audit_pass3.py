"""
Audit pass 3 — fixes all remaining issues from the full checklist.
Run: python fix_audit_pass3.py
"""
import sys, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")
DB_URL = os.getenv("DATABASE_URL")

GENRE_PRIORITY = [
    "RPG", "Strategy", "Racing", "Simulation", "Puzzle", "Platformer",
    "Fighting", "Sports", "MMO", "Shooter", "Indie", "Adventure", "Action",
    "Casual", "Arcade", "Family", "Card", "Board Games",
]

def resolve_genre(genres):
    for g in GENRE_PRIORITY:
        if g in genres:
            return g
    return genres[0] if genres else ""

FIXES = {
    # 1
    "Age of Empires IV": {
        "remove_tags":   ["3D", "Isometric", "Strategy"],
    },
    # 2
    "Anno 1800": {
        "remove_tags":   ["RTS", "Real-Time"],
        "add_tags":      ["Turn-Based Strategy"],  # Anno has both RT and TB campaign
    },
    # 3
    "Apex Legends": {
        "remove_tags":   ["Survival", "Action-Adventure", "Dark", "Cyberpunk"],
    },
    # 4
    "Batman: Arkham Knight": {
        "remove_tags":   ["Horror"],
    },
    # 5
    "Battlefield V": {
        "remove_tags":   ["Open World", "Action-Adventure", "Female Protagonist"],
        "add_tags":      ["Team-Based", "Competitive", "Shooter"],
    },
    # 6
    "Borderlands 3": {
        "remove_tags":   ["Open World", "Western", "Driving"],
    },
    # 7
    "Content Warning": {
        "remove_tags":   ["Dungeon Crawler"],
    },
    # 8 — only Trading; War is marginal but CS2 IS military themed, leave it
    "Counter-Strike 2": {
        "remove_tags":   ["Trading"],
    },
    # 9
    "DOOM Eternal": {
        "remove_tags":   ["Military", "Action-Adventure"],
    },
    # 10
    "Dark Souls III": {
        "remove_tags":   ["Open World", "Horror"],
    },
    # 11
    "Deep Rock Galactic": {
        "remove_tags":   ["Horror"],
    },
    # 12
    "EA SPORTS FC 24": {
        "remove_tags":   ["First-Person", "3D"],
    },
    # 13
    "Firewatch": {
        "remove_tags":   ["Visual Novel"],
    },
    # 14 — fix genres for FNAF
    "Five Nights at Freddy's": {
        "remove_genres": ["Strategy", "Simulation"],
    },
    # 15
    "Ghost of Tsushima": {
        "remove_tags":   ["Third-Person Shooter"],
    },
    # 16 — Into the Breach: remove RPG from tags AND genres
    "Into the Breach": {
        "remove_tags":   ["RPG"],
        "remove_genres": ["RPG"],
    },
    # 17
    "Lethal Company": {
        "remove_tags":   ["Dungeon Crawler"],
    },
    # 18
    "Monster Hunter: World": {
        "remove_tags":   ["JRPG", "Souls-like"],
    },
    # 19 — MK11: remove 3D tag + Adventure genre
    "Mortal Kombat 11": {
        "remove_tags":   ["3D"],
        "remove_genres": ["Adventure"],
    },
    # 20
    "Need for Speed Heat": {
        "remove_tags":   ["First-Person"],
    },
    # 21
    "Persona 5": {
        "remove_tags":   ["Action-Adventure", "Third-Person"],
    },
    # 22
    "Portal 2": {
        "remove_tags":   ["Space"],
    },
    # 23
    "Resident Evil: Village": {
        "remove_tags":   ["Open World"],
    },
    # 24 — SF6: remove 3D tag + Adventure genre
    "Street Fighter 6": {
        "remove_tags":   ["3D"],
        "remove_genres": ["Adventure"],
    },
    # 25
    "The Sims 4": {
        "remove_tags":   ["Fantasy", "3D"],
    },
    # 26 — WoT: 3D (technical) and Third-Person Shooter (it's a tank sim)
    "World of Tanks": {
        "remove_tags":   ["3D", "Third-Person Shooter"],
        "add_tags":      ["Competitive"],
    },
    # 27
    "XCOM 2": {
        "remove_tags":   ["Horror", "RPG"],
    },
}


def apply(cur, title, fix):
    cur.execute("SELECT id, genres, tags FROM games WHERE title=%s", (title,))
    row = cur.fetchone()
    if not row:
        # try by id pattern for curly-apostrophe titles
        print(f"  [not found] {title}")
        return False

    genres = list(row["genres"] or [])
    tags   = list(row["tags"]   or [])

    removed_g, removed_t, added_t = [], [], []

    for g in fix.get("remove_genres", []):
        if g in genres:
            genres.remove(g)
            removed_g.append(g)

    for t in fix.get("remove_tags", []):
        if t in tags:
            tags.remove(t)
            removed_t.append(t)

    seen = {t.lower() for t in tags}
    for t in fix.get("add_tags", []):
        if t.lower() not in seen:
            tags.append(t)
            seen.add(t.lower())
            added_t.append(t)

    new_genre = resolve_genre(genres)
    cur.execute(
        "UPDATE games SET genres=%s, tags=%s, genre=%s WHERE id=%s",
        (genres, tags, new_genre, row["id"])
    )

    print(f"  [{row['id']:3d}] {title}")
    if removed_g: print(f"        genres -: {removed_g}")
    if removed_t: print(f"        tags   -: {removed_t}")
    if added_t:   print(f"        tags   +: {added_t}")
    return True


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

updated = 0
for title, fix in FIXES.items():
    if apply(cur, title, fix):
        conn.commit()
        updated += 1

cur.close()
conn.close()
print(f"\nDone: {updated} games updated")
