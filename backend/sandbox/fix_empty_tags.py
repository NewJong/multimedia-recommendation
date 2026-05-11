"""
Manually restores tags for games that ended up with empty/near-empty tags
after the RAWG refetch (RAWG's top-voted tags for these games were all
platform features that we filtered out).
Run: python fix_empty_tags.py
"""
import sys, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")
DB_URL = os.getenv("DATABASE_URL")

# game title → correct tags (manually curated)
OVERRIDES = {
    "Gran Turismo 7": {
        "tags": ["Racing Simulation", "Realistic", "Driving", "Competitive", "Sports"],
    },
    "DiRT Rally 2.0": {
        "tags": ["Racing Simulation", "Realistic", "Difficult", "Driving", "Competitive"],
    },
    "Alan Wake 2": {
        "tags": ["Story Rich", "Horror", "Third-Person", "Mystery", "Cinematic",
                 "Psychological Horror", "Survival Horror"],
    },
    "Spiritfarer": {
        "tags": ["Story Rich", "Exploration", "Management", "Hand-drawn",
                 "Cozy", "Peaceful", "Narrative"],
    },
    "Outer Wilds": {
        "tags": ["Story Rich", "Open World", "Sci-fi", "Exploration", "Mystery",
                 "Non-linear", "Space"],
    },
    "Tunic": {
        "tags": ["Exploration", "Difficult", "Mystery", "Souls-like",
                 "Fantasy", "Isometric"],
    },
    "StarCraft II": {
        "tags": ["RTS", "Sci-fi", "War", "Space", "Competitive", "Esports",
                 "Strategy", "Military"],
    },
    "Mortal Kombat 11": {
        "tags": ["Fighting", "Story Rich", "Competitive", "3D", "Cinematic"],
    },
    "Batman: Arkham City": {
        "tags": ["Story Rich", "Open World", "Third-Person", "Stealth",
                 "Action-Adventure", "Sandbox", "Dark", "Comic Book", "Superhero", "Batman"],
    },
    "FINAL FANTASY XV": {
        "tags": ["RPG", "Fantasy", "Open World", "Story Rich", "Action RPG",
                 "JRPG", "Third-Person", "Cinematic"],
    },
    "World of Warcraft": {
        "tags": ["Fantasy", "MMO", "Open World", "Exploration", "Character Customization",
                 "MMORPG", "Medieval", "Magic"],
    },
    "Grand Theft Auto: Vice City": {
        "tags": ["Open World", "Third-Person", "Funny", "Sandbox",
                 "Third-Person Shooter", "Crime", "Driving", "Action-Adventure"],
    },
    "Minecraft": {
        "tags": ["Sandbox", "Crafting", "Building", "Open World",
                 "Procedural Generation", "Survival"],
    },
}

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

updated = 0
for title, data in OVERRIDES.items():
    cur.execute("SELECT id, tags FROM games WHERE title=%s", (title,))
    row = cur.fetchone()
    if not row:
        print(f"  [not found] {title}")
        continue

    new_tags = data["tags"]
    old_tags = list(row["tags"] or [])

    cur.execute("UPDATE games SET tags=%s WHERE id=%s", (new_tags, row["id"]))
    conn.commit()
    updated += 1
    print(f"  [{row['id']:3d}] {title}")
    print(f"        was:  {old_tags}")
    print(f"        now:  {new_tags}")

cur.close()
conn.close()
print(f"\nFixed: {updated}")
