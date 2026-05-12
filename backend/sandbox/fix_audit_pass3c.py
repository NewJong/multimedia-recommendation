"""
Critical fixes after pass3b review:
  - Sekiro: remove RPG from genres (no stats/build/customization)
  - Total War THREE KINGDOMS: remove redundant "Strategy" tag (already the genre)
  - Indie genre priority: for horror/action games that have Indie in genres[],
    remove Indie from genres so the primary genre resolves correctly
    (Amnesia, FNaF, Phasmophobia, Outlast, Content Warning, Lethal Company, DRG)
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

def patch(game_id, remove_genres=None, add_genres=None, remove_tags=None):
    cur.execute("SELECT id, title, genres, tags FROM games WHERE id=%s", (game_id,))
    r = cur.fetchone()
    genres = list(r["genres"] or [])
    tags   = list(r["tags"]   or [])

    for g in (remove_genres or []):
        if g in genres: genres.remove(g)
    for g in (add_genres or []):
        if g not in genres: genres.append(g)
    for t in (remove_tags or []):
        if t in tags: tags.remove(t)

    new_genre = resolve_genre(genres)
    cur.execute("UPDATE games SET genres=%s, tags=%s, genre=%s WHERE id=%s",
                (genres, tags, new_genre, game_id))
    conn.commit()
    print(f"  [{game_id:3d}] {r['title']}")
    print(f"        genres: {genres}  →  genre: {new_genre}")

# Sekiro (id=26): RPG is wrong — pure action game
patch(26, remove_genres=["RPG"])

# Total War THREE KINGDOMS (id=52): "Strategy" tag duplicates genre
patch(52, remove_tags=["Strategy"])

# Games where "Indie" inflates genre field above more meaningful genres.
# Removing Indie from genres[] lets the real primary genre surface.
# We keep Indie identity through tags if needed, but these games are not
# primarily "Indie" — they're Horror/Action/Adventure games.
INDIE_GENRE_FIXES = [
    (109, "Amnesia: The Dark Descent"),   # → Adventure
    (111, "Five Nights at Freddy's"),     # → Action
    ( 92, "Phasmophobia"),                # → Action
    (108, "Outlast"),                     # → Action
    (107, "Content Warning"),             # → Adventure
    (106, "Lethal Company"),              # → Adventure
    ( 91, "Deep Rock Galactic"),          # → Action (Shooter preferred)
]
for gid, _ in INDIE_GENRE_FIXES:
    patch(gid, remove_genres=["Indie"])

cur.close()
conn.close()
print("\nDone")
