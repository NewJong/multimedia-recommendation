"""
Second audit pass — fixes remaining issues found in full game review.
Run: python fix_audit_pass2.py
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
    # ── Remove wrong tags ────────────────────────────────────────────────────

    # Horror removed from non-horror games
    "No Man's Sky":             {"remove_tags": ["Horror"]},
    "Deep Rock Galactic":       {"remove_tags": ["Horror"]},
    "DOOM Eternal":             {"remove_tags": ["Horror"]},
    "Undertale":                {"remove_tags": ["Horror"]},
    "Batman: Arkham Knight":    {"remove_tags": ["Horror"]},
    "What Remains of Edith Finch": {"remove_tags": ["Horror"]},

    # Open World removed from non-open-world games
    "Hollow Knight":            {"remove_tags": ["Open World"]},
    "Ori and the Will of the Wisps": {"remove_tags": ["Open World", "Souls-like"]},
    "Resident Evil: Village":   {"remove_tags": ["Open World"]},
    "Stardew Valley":           {"remove_tags": ["Open World"]},
    "Sid Meier's Civilization VI": {"remove_tags": ["Open World"]},

    # 3D technical tag removed
    "EA SPORTS FC 24":          {"remove_tags": ["3D", "First-Person"]},
    "Elden Ring":               {"remove_tags": ["3D"]},
    "Mortal Kombat 11":         {"remove_tags": ["3D"]},
    "NBA 2K23":                 {"remove_tags": ["3D"]},
    "World of Tanks":           {"remove_tags": ["3D", "Third-Person Shooter"]},
    "Age of Empires IV":        {"remove_tags": ["3D", "Isometric"]},  # AoE4 is NOT isometric
    "Content Warning":          {"remove_tags": ["3D", "Time Management"]},
    "Phasmophobia":             {"remove_tags": ["3D"]},
    "It Takes Two":             {"remove_tags": ["Magic"]},
    "The Sims 4":               {"remove_tags": ["3D", "Fantasy"]},

    # Genre-specific wrong tags
    "Control":                  {"remove_tags": ["Realistic"]},  # merge artifact; Control is supernatural
    "Anno 1800":                {"remove_tags": ["RTS", "Real-Time"]},  # city builder, not RTS
    "Overwatch 2":              {"remove_tags": ["MOBA"]},
    "Sekiro: Shadows Die Twice": {"remove_tags": ["JRPG", "Open World"]},
    "Path of Exile":            {"remove_tags": ["Fishing"]},
    "Portal 2":                 {"remove_tags": ["Space"]},  # underground lab, not space
    "Cyberpunk 2077":           {"remove_tags": ["Soundtrack"]},
    "Persona 5":                {"remove_tags": ["Action-Adventure", "Third-Person"]},  # JRPG
    "The Witness":              {"remove_tags": ["Sandbox", "Walking Simulator"]},  # puzzle game
    "Counter-Strike 2":         {"remove_tags": ["Trading"]},  # skin trading ≠ gameplay taste
    "Dark Souls III":           {"remove_tags": ["Horror", "Open World"]},
    "StarCraft II":             {"remove_tags": ["Strategy"]},  # redundant with RTS tag
    "Cities: Skylines":         {"remove_tags": ["Funny"]},  # not a comedy game
    "Mass Effect 2":            {"remove_tags": ["Real-Time with Pause"]},  # that was ME1
    "Into the Breach":          {"remove_tags": ["RPG"]},  # strategy, not RPG
    "Shovel Knight":            {"remove_tags": ["RPG", "Metroidvania"]},  # level platformer
    "Apex Legends":             {"remove_tags": ["Dark", "Cyberpunk", "Survival"]},
    "Borderlands 3":            {"remove_tags": ["Western", "Open World"]},  # alien planets, hub-based
    "Halo Infinite":            {"remove_tags": ["Action-Adventure"]},
    "Titanfall 2":              {"remove_tags": ["Exploration", "Action-Adventure"]},
    "Batman: Arkham Asylum":    {"remove_tags": ["Puzzle"]},  # minor element, confusing tag

    # ── Add missing tags ─────────────────────────────────────────────────────

    "The Legend of Zelda: Breath of the Wild": {
        "add_tags": ["Exploration", "Fantasy", "Crafting", "Stealth", "Puzzle"],
    },
    "Persona 5": {
        "add_tags": ["Story Rich", "Turn-Based", "Dark", "Choices Matter", "Stealth",
                     "Visual Novel", "School"],
    },
    "Forza Horizon 5": {
        "add_tags": ["Sandbox", "Realistic", "Family Friendly", "Cinematic", "Offroad"],
    },
    "Marvel's Spider-Man": {
        "add_tags": ["Story Rich", "Crime", "Third-Person Shooter"],
    },
    "HELLDIVERS 2": {
        "add_tags": ["Military", "Team-Based", "Dark Humor", "Action-Adventure", "Shooter"],
    },
    "Batman: Arkham City": {
        "add_tags": ["Detective", "Beat 'em up"],
    },
    "Batman: Arkham Knight": {
        "add_tags": ["Action-Adventure"],
    },
    "Halo Infinite": {
        "add_tags": ["Military", "Shooter"],
    },
    "Resident Evil: Village": {
        "add_tags": ["Cinematic", "Action-Adventure", "Crafting"],
    },
    "Anno 1800": {
        "add_tags": ["Historical", "Building", "Management"],
    },
    "Portal 2": {
        "add_tags": ["Puzzle"],
    },
    "Deep Rock Galactic": {
        "add_tags": ["Shooter", "Team-Based", "Military"],
    },
    "Satisfactory": {
        "add_tags": ["Automation", "Crafting", "Sci-fi"],
    },
    "World of Tanks": {
        "add_tags": ["Simulation"],
    },
    "God of War I": {
        "add_tags": ["Third-Person Shooter"],  # actually GoW uses range attacks, but not shooter. Remove.
    },
    "EA SPORTS FC 24": {
        "add_tags": ["Sports"],
    },
    "Mortal Kombat 11": {
        "add_tags": ["Beat 'em up"],
    },
    "StarCraft II": {
        "add_tags": ["Base Building", "Resource Management"],
    },
    "Into the Breach": {
        "add_tags": ["Sci-fi", "Difficult", "Tactical"],
    },
    "Age of Empires IV": {
        "add_tags": ["Strategy", "Base Building"],
    },
    "Counter-Strike 2": {
        "add_tags": ["Team-Based", "Shooter"],
    },
    "Dark Souls III": {
        "add_tags": ["Souls-like"],
    },
    "The Sims 4": {
        "add_tags": ["Life Sim"],  # already there but let's check
    },
    "Borderlands 3": {
        "add_tags": ["Sci-fi"],
    },
    "Apex Legends": {
        "add_tags": ["Military", "Competitive"],
    },
    "Hades": {
        "remove_tags": [],  # already good
    },
    "Ghost of Tsushima": {
        "add_tags": ["Third-Person Shooter"],  # it does have ranged combat
    },
}

def apply_fix(cur, title, fix):
    cur.execute("SELECT id, genres, tags FROM games WHERE title=%s", (title,))
    row = cur.fetchone()
    if not row:
        print(f"  [not found] {title}")
        return False

    genres = list(row["genres"] or [])
    tags   = list(row["tags"]   or [])

    for t in fix.get("remove_tags", []):
        if t in tags:
            tags.remove(t)
    for g in fix.get("remove_genres", []):
        if g in genres:
            genres.remove(g)

    seen_lower = {t.lower() for t in tags}
    for t in fix.get("add_tags", []):
        if t.lower() not in seen_lower:
            tags.append(t)
            seen_lower.add(t.lower())

    new_genre = resolve_genre(genres)
    cur.execute("UPDATE games SET genres=%s, tags=%s, genre=%s WHERE id=%s",
                (genres, tags, new_genre, row["id"]))

    removed_t = [t for t in fix.get("remove_tags", []) if t in (row["tags"] or [])]
    added_t   = fix.get("add_tags", [])
    if removed_t or added_t:
        print(f"  [{row['id']:3d}] {title}")
        if removed_t: print(f"        - {removed_t}")
        if added_t:   print(f"        + {[t for t in added_t if t.lower() not in {x.lower() for x in (row['tags'] or [])}]}")
    return True


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

# Also fix stale genre field for ALL games
print("=== Fixing stale genre field ===")
cur.execute("SELECT id, title, genre, genres FROM games ORDER BY id")
all_games = cur.fetchall()
genre_fixed = 0
for g in all_games:
    correct = resolve_genre(g["genres"] or [])
    if correct != g["genre"]:
        cur.execute("UPDATE games SET genre=%s WHERE id=%s", (correct, g["id"]))
        print(f"  [{g['id']:3d}] {g['title']}: '{g['genre']}' → '{correct}'")
        genre_fixed += 1
conn.commit()
print(f"Genre field fixed: {genre_fixed}\n")

print("=== Fixing individual game tags ===")
updated = 0
for title, fix in FIXES.items():
    if apply_fix(cur, title, fix):
        conn.commit()
        updated += 1

# Remove Third-Person Shooter from God of War (not a shooter)
cur.execute("SELECT id, tags FROM games WHERE title='God of War I'")
row = cur.fetchone()
if row:
    tags = list(row["tags"] or [])
    if "Third-Person Shooter" in tags:
        tags.remove("Third-Person Shooter")
        cur.execute("UPDATE games SET tags=%s WHERE id=%s", (tags, row["id"]))
        conn.commit()
        print("  [ 17] God of War I — removed wrongly added Third-Person Shooter")

cur.close()
conn.close()
print(f"\nIndividual fixes: {updated} games")
