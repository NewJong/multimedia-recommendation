import sys, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")
DB_URL = os.getenv("DATABASE_URL")

FIXES = {
    "Grand Theft Auto: San Andreas": {
        "remove_tags": ["Comedy"],                               # дублікат Funny
        "add_tags":    ["Third-Person Shooter", "Driving", "Action-Adventure"],
    },
    "Grand Theft Auto V": {
        "add_tags":    ["Driving", "Story Rich", "Action-Adventure"],
    },
    "Mafia II": {
        "remove_tags": ["RPG", "Music"],                         # не RPG, Music — шум
        "add_tags":    ["Action-Adventure", "Cinematic", "Historical"],
    },
    "Grand Theft Auto: Vice City": {
        "add_tags":    ["Story Rich", "Comedy"],
    },
}

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

for title, fix in FIXES.items():
    cur.execute("SELECT id, genres, tags FROM games WHERE title=%s", (title,))
    row = cur.fetchone()
    if not row:
        print(f"  [not found] {title}")
        continue

    tags = list(row["tags"] or [])

    for t in fix.get("remove_tags", []):
        if t in tags:
            tags.remove(t)

    seen_lower = {t.lower() for t in tags}
    for t in fix.get("add_tags", []):
        if t.lower() not in seen_lower:
            tags.append(t)
            seen_lower.add(t.lower())

    cur.execute("UPDATE games SET tags=%s WHERE id=%s", (tags, row["id"]))
    conn.commit()

    print(f"[{row['id']}] {title}")
    print(f"  removed: {fix.get('remove_tags', [])}")
    print(f"  added:   {fix.get('add_tags', [])}")
    print(f"  final:   {tags}")

cur.close()
conn.close()
