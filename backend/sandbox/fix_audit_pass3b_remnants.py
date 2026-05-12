"""
Remnants from pass3b:
  - Total War THREE KINGDOMS: duplicate key in FIXES dict lost the tag fixes
  - Uncharted 4: curly apostrophe title → use ID-based lookup
"""
import sys, psycopg2, psycopg2.extras, os
from dotenv import load_dotenv
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

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

conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

# ── Total War: THREE KINGDOMS (id=52) ────────────────────────────────────────
cur.execute("SELECT id, genre, genres, tags FROM games WHERE id=52")
r = cur.fetchone()
tags   = list(r["tags"] or [])
genres = list(r["genres"] or [])

if "Isometric" in tags:
    tags.remove("Isometric")
    print("Total War: tags - Isometric")
if "Turn-Based Strategy" not in tags:
    tags.append("Turn-Based Strategy")
    print("Total War: tags + Turn-Based Strategy")

new_genre = resolve_genre(genres)
cur.execute("UPDATE games SET tags=%s, genre=%s WHERE id=52", (tags, new_genre))
conn.commit()

# ── Uncharted 4: A Thief's End (id=28) ───────────────────────────────────────
cur.execute("SELECT id, genre, genres, tags FROM games WHERE id=28")
r = cur.fetchone()
genres = list(r["genres"] or [])
tags   = list(r["tags"]   or [])

if "Shooter" in genres:
    genres.remove("Shooter")
    print("Uncharted 4: genres - Shooter")
if "Adventure" not in genres:
    genres.append("Adventure")
    print("Uncharted 4: genres + Adventure")

new_genre = resolve_genre(genres)
cur.execute("UPDATE games SET genres=%s, genre=%s WHERE id=28", (genres, new_genre))
conn.commit()

print(f"  genre now: {new_genre}")
print("Done")
cur.close(); conn.close()
