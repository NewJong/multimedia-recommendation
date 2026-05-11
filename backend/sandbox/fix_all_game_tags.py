"""
Comprehensive tag/genre audit fixes for all games.
Run: python fix_all_game_tags.py
"""
import sys, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")
DB_URL = os.getenv("DATABASE_URL")

# title → {remove_tags, add_tags, remove_genres, add_genres, set_tags}
FIXES = {
    # ── Too sparse ──────────────────────────────────────────────────────────
    "God of War I": {
        "add_tags": ["Third-Person", "Action-Adventure", "Dark Fantasy", "Cinematic", "Difficult"],
    },
    "Ghost of Tsushima": {
        "add_tags": ["Stealth", "Historical", "Cinematic", "Action-Adventure", "Hack & Slash"],
    },
    "Batman: Arkham Asylum": {
        "add_tags": ["Story Rich", "Third-Person", "Dark", "Action-Adventure",
                     "Beat 'em up", "Detective", "Superhero", "Comic Book"],
    },
    "Uncharted 4: A Thief's End": {
        "add_tags": ["Story Rich", "Cinematic", "Exploration", "Stealth", "Third-Person Shooter"],
    },
    "Disco Elysium": {
        "add_tags": ["Detective", "Mystery", "Choices Matter", "Dark Humor", "Drama", "Narrative"],
    },
    "Planet Zoo": {
        "add_tags": ["Building", "Simulation", "Realistic", "Family Friendly"],
    },
    "Green Hell": {
        "add_tags": ["Realistic", "Difficult", "Action-Adventure"],
    },
    "Total War: THREE KINGDOMS": {
        "add_tags": ["RTS", "Military", "Strategy", "Isometric"],
    },
    "DOOM Eternal": {
        "add_tags": ["Shooter", "Military", "Action-Adventure"],
    },
    "Call of Duty: Warzone": {
        "remove_tags": ["Politics"],
        "add_tags": ["First-Person", "Team-Based", "Competitive", "Shooter", "Co-op"],
    },
    # ── Wrong tags ──────────────────────────────────────────────────────────
    "Resident Evil 4": {
        "remove_tags": ["Un jugador", "Logros de Steam", "Compat. total con control",
                        "Dating Sim", "3D", "Resource Management"],
    },
    "Resident Evil: Village": {
        "remove_tags": ["Dating Sim", "evil"],
    },
    "Street Fighter 6": {
        "remove_tags": ["Open World", "Sandbox", "Action RPG"],
    },
    "Celeste": {
        "remove_tags": ["Horror"],
        "add_tags": ["Difficult", "Side Scroller", "Colorful", "Cute", "Platformer", "Precision Platformer"],
    },
    "Five Nights at Freddy's": {
        "remove_tags": ["Historical", "Sci-fi", "Resource Management"],
        "add_tags": ["Mystery"],
    },
    "Titanfall 2": {
        "remove_tags": ["RTS"],
    },
    "Dead Space (2008)": {
        "remove_tags": ["RPG"],
    },
    "Outlast": {
        "remove_tags": ["Sci-fi", "Parkour", "Walking Simulator"],
        "add_tags": ["Mystery"],
    },
    "F1 23": {
        "remove_tags": ["3D Platformer", "Action-Adventure", "3D", "Simulation"],
        "add_tags": ["Racing Simulation"],
    },
    "The Witness": {
        "remove_tags": ["Survival", "Building"],
    },
    "Death Stranding": {
        "remove_tags": ["Heist"],
    },
    "It Takes Two": {
        "remove_tags": ["Action RPG", "Mining", "relationship"],
    },
    "Overwatch 2": {
        "remove_tags": ["RPG", "Story Rich"],
    },
    "Ori and the Blind Forest": {
        "remove_tags": ["RPG", "Open World"],
    },
    "Firewatch": {
        "remove_tags": ["Horror"],
    },
    "Battlefield V": {
        "remove_tags": ["LGBTQ+", "Battle Royale"],
    },
    "Control": {
        "remove_tags": ["Abstract", "realism"],
        "add_tags": ["Realistic"],
    },
    "Valheim": {
        "remove_tags": ["coop", "Forest", "viking"],  # coop = dup, Forest = location, viking = dup of Norse
    },
    "Metro Exodus": {
        "remove_tags": ["russia"],
    },
    "Marvel's Spider-Man": {
        "remove_tags": ["new york"],
    },
    "World of Tanks": {
        "remove_tags": ["collectathon", "tank"],
    },
    "Forza Horizon 4": {
        "remove_tags": ["street racing", "winter", "autumn", "extreme"],
        "add_tags": ["Racing Simulation"],
    },
    "Forza Horizon 5": {
        "remove_tags": ["cars", "drift", "racing-game", "mexico", "festival", "sprint", "photorealism"],
        "add_tags": ["Racing Simulation"],
    },
    "Need for Speed Heat": {
        "remove_tags": ["street racing"],
        "add_tags": ["Racing Simulation"],
    },
    "Minecraft": {
        "remove_genres": ["Arcade"],
    },
    "DOOM Eternal": {
        "remove_tags": ["Co-op"],  # Co-op was added later, not its identity
        "add_tags": ["Shooter", "Military", "Action-Adventure"],
    },
    "Apex Legends": {
        "remove_tags": ["Exploration"],  # Apex isn't really exploration
    },
    "Batman: Arkham City": {
        "remove_tags": ["Batman"],
    },
    "Batman: Arkham Knight": {
        "remove_tags": ["Batman"],
    },
    "Batman: Arkham Origins": {
        "remove_tags": ["Batman"],
    },
    "Batman: Arkham Asylum": {
        "remove_tags": ["Batman"],
        "add_tags": ["Story Rich", "Third-Person", "Dark", "Action-Adventure",
                     "Beat 'em up", "Detective", "Superhero", "Comic Book"],
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
        if t in tags: tags.remove(t)
    for g in fix.get("remove_genres", []):
        if g in genres: genres.remove(g)

    seen_lower = {t.lower() for t in tags}
    for t in fix.get("add_tags", []):
        if t.lower() not in seen_lower:
            tags.append(t)
            seen_lower.add(t.lower())

    seen_g = {g.lower() for g in genres}
    for g in fix.get("add_genres", []):
        if g.lower() not in seen_g:
            genres.append(g)

    cur.execute("UPDATE games SET genres=%s, tags=%s WHERE id=%s", (genres, tags, row["id"]))

    removed_t = fix.get("remove_tags", [])
    removed_g = fix.get("remove_genres", [])
    added_t   = fix.get("add_tags", [])
    print(f"  [{row['id']:3d}] {title}")
    if removed_t: print(f"        - tags:   {removed_t}")
    if removed_g: print(f"        - genres: {removed_g}")
    if added_t:   print(f"        + tags:   {added_t}")
    return True


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

updated = 0
for title, fix in FIXES.items():
    if apply_fix(cur, title, fix):
        conn.commit()
        updated += 1

cur.close()
conn.close()
print(f"\nFixed: {updated} games")
