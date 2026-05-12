"""
Final audit sweep — removes leftover noise, fixes wrong genres,
adds missing tags found in full re-review of all 113 games.
Run: python fix_audit_pass3b.py
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

# title → patch dict
FIXES = {

    # ── Remove wrong tags ─────────────────────────────────────────────────

    # GTA V: RPG is wrong (GTA has no RPG mechanics)
    "Grand Theft Auto V":   {"remove_tags": ["RPG"]},

    # Sekiro: no stats, no build — remove all RPG tags
    "Sekiro: Shadows Die Twice": {"remove_tags": ["RPG", "Action RPG"]},

    # Ghost of Tsushima: RPG tag duplicates genre
    "Ghost of Tsushima":    {"remove_tags": ["RPG"]},

    # Borderlands 3: RPG tag duplicates genre
    "Borderlands 3":        {"remove_tags": ["RPG"],
                             "add_tags":    ["Funny", "Comedy"]},

    # MK11: Beat 'em up is wrong for a fighting game
    "Mortal Kombat 11":     {"remove_tags": ["Beat 'em up"]},

    # A Way Out: no stealth mechanics
    "A Way Out":            {"remove_tags": ["Stealth"]},

    # AoE4: pure RTS, not turn-based
    "Age of Empires IV":    {"remove_tags": ["Turn-Based Strategy"]},

    # Anno 1800: real-time city builder, NOT turn-based
    "Anno 1800":            {"remove_tags": ["Turn-Based Strategy"]},

    # Content Warning: horror co-op, not sci-fi
    "Content Warning":      {"remove_tags": ["Sci-fi"]},

    # What Remains of Edith Finch: walking sim, not visual novel
    "What Remains of Edith Finch": {"remove_tags": ["Visual Novel"]},

    # StarCraft II: Strategy tag is redundant with RTS
    "StarCraft II":         {"remove_tags": ["Strategy"]},

    # Total War: not isometric — full 3D camera
    "Total War: THREE KINGDOMS": {"remove_tags":   ["Isometric"],
                                  "add_tags":      ["Turn-Based Strategy"]},

    # F1 23: Cinematic feels out of place for a racing sim
    "F1 23":                {"remove_tags": ["Cinematic"]},

    # DOOM Eternal: too sparse — add Difficult
    "DOOM Eternal":         {"add_tags": ["Difficult"]},

    # ── Fix genres[] ─────────────────────────────────────────────────────

    # Batman x4: add Adventure genre (open world, exploration)
    "Batman: Arkham Asylum":  {"add_genres": ["Adventure"]},
    "Batman: Arkham City":    {"add_genres": ["Adventure"]},
    "Batman: Arkham Knight":  {"add_genres": ["Adventure"]},
    "Batman: Arkham Origins": {"add_genres": ["Adventure"]},

    # God of War: adventure/mythology game, not just action
    "God of War I":         {"add_genres": ["Adventure"]},

    # Battlefield V: FPS, not adventure
    "Battlefield V":        {"remove_genres": ["Adventure"]},

    # Halo Infinite: FPS, not adventure
    "Halo Infinite":        {"remove_genres": ["Adventure"]},

    # Satisfactory: factory/sim, not action-adventure
    "Satisfactory":         {"remove_genres": ["Action", "Adventure"],
                             "add_genres":    ["Simulation"]},

    # Total War: not an action game
    "Total War: THREE KINGDOMS": {"remove_genres": ["Action"]},

    # Uncharted 4: not a shooter — action-adventure
    "Uncharted 4: A Thief's End": {"remove_genres": ["Shooter"],
                                   "add_genres":    ["Adventure"]},

    # World of Warcraft: it IS an MMO — add to genres
    "World of Warcraft":    {"add_genres": ["MMO"],
                             "add_tags":   ["MMO", "Co-op"]},

    # ── Add missing tags ─────────────────────────────────────────────────

    # Silent Hill 2 had Horror removed by a previous pass — restore it
    "Silent Hill 2":        {"add_tags": ["Horror", "Dark", "Psychological Horror"]},

    # Ori and the Will of the Wisps: 2D game missing 2D tag
    "Ori and the Will of the Wisps": {"add_tags": ["2D", "Side Scroller"]},

    # Hollow Knight: Silksong: missing 2D
    "Hollow Knight: Silksong": {"add_tags": ["2D"]},

    # Assassin's Creed Odyssey: missing Action-Adventure
    "Assassin's Creed Odyssey": {"add_tags": ["Action-Adventure", "Hack & Slash"]},

    # Street Fighter 6: has a proper story mode with cinematics
    "Street Fighter 6":     {"add_tags": ["Story Rich"]},

    # Deep Rock Galactic: Funny is a key trait of DRG
    "Deep Rock Galactic":   {"add_tags": ["Funny", "Dark Humor"]},

    # Phasmophobia: add Investigation (core loop)  — already has it? check
    # Already has Investigation in tags per audit.

    # Valheim: Norse mythology = core identity
    "Valheim":              {"add_tags": ["Building", "Crafting"]},
    # (already has Crafting? let it deduplicate)

    # Amnesia: The Dark Descent: genre field should be Action not Indie
    "Amnesia: The Dark Descent": {"add_genres": []},  # genres[] is fine, just fix genre field

    # Cyberpunk 2077: Third-Person is odd as primary mode (FP game)
    # Leave it — the game does have third-person cutscenes
}


def apply(cur, title, fix):
    cur.execute("SELECT id, genres, tags FROM games WHERE title=%s", (title,))
    row = cur.fetchone()
    if not row:
        print(f"  [not found] {title}")
        return False

    genres = list(row["genres"] or [])
    tags   = list(row["tags"]   or [])

    removed_g, added_g, removed_t, added_t = [], [], [], []

    for g in fix.get("remove_genres", []):
        if g in genres:
            genres.remove(g)
            removed_g.append(g)

    g_seen = {g.lower() for g in genres}
    for g in fix.get("add_genres", []):
        if g.lower() not in g_seen:
            genres.append(g)
            g_seen.add(g.lower())
            added_g.append(g)

    for t in fix.get("remove_tags", []):
        if t in tags:
            tags.remove(t)
            removed_t.append(t)

    t_seen = {t.lower() for t in tags}
    for t in fix.get("add_tags", []):
        if t.lower() not in t_seen:
            tags.append(t)
            t_seen.add(t.lower())
            added_t.append(t)

    new_genre = resolve_genre(genres)
    cur.execute(
        "UPDATE games SET genres=%s, tags=%s, genre=%s WHERE id=%s",
        (genres, tags, new_genre, row["id"])
    )

    if removed_g or added_g or removed_t or added_t:
        print(f"  [{row['id']:3d}] {title}")
        if removed_g: print(f"        genres -: {removed_g}")
        if added_g:   print(f"        genres +: {added_g}")
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
print(f"\nDone: {updated} games processed")
