"""
Creates games table and seeds 100 games from RAWG.
Run: python seed_games.py
"""
import sys, httpx, psycopg2, time, re
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

API_KEY = os.getenv("RAWG_API_KEY")
DB_URL  = os.getenv("DATABASE_URL")
BASE    = "https://api.rawg.io/api"

# ── Priority list (user's picks first) ──────────────────────────────────────
PRIORITY = [
    "Red Dead Redemption 2",
    "Grand Theft Auto V",
    "Marvel's Spider-Man",
    "Mafia II",
    "Call of Duty: Warzone",
    "Forza Horizon 4",
    "Minecraft",
    "Counter-Strike 2",
    "American Truck Simulator",
    "World of Tanks",
    "Satisfactory",
    "The Witcher 3: Wild Hunt",
    "Cyberpunk 2077",
    "Grand Theft Auto: Vice City",
    "Grand Theft Auto: San Andreas",
    "Valheim",
    "God of War",
    "Ghost of Tsushima",
    "The Last of Us",
    "The Last of Us Part II",
]

# ── Additional games per genre to reach 100 ──────────────────────────────────
EXTRA = [
    # Action / Adventure
    "The Legend of Zelda: Breath of the Wild",
    "Assassin's Creed Odyssey",
    "Batman: Arkham Knight",
    "Shadow of the Tomb Raider",
    "Death Stranding",
    "Sekiro: Shadows Die Twice",
    "Horizon Zero Dawn",
    "Uncharted 4: A Thief's End",
    "Control",
    "Alan Wake 2",
    # RPG
    "Elden Ring",
    "Dark Souls III",
    "Baldur's Gate 3",
    "Mass Effect 2",
    "Dragon Age: Inquisition",
    "Divinity: Original Sin 2",
    "Final Fantasy XV",
    "Persona 5",
    "Monster Hunter: World",
    "Hollow Knight",
    # Shooter
    "Doom Eternal",
    "Halo Infinite",
    "Apex Legends",
    "Overwatch 2",
    "Battlefield V",
    "Far Cry 5",
    "Borderlands 3",
    "Titanfall 2",
    "Metro Exodus",
    "Escape from Tarkov",
    # Strategy
    "Civilization VI",
    "Total War: Three Kingdoms",
    "StarCraft II",
    "XCOM 2",
    "Age of Empires IV",
    "Into the Breach",
    "Crusader Kings III",
    "Anno 1800",
    # Simulation / Sandbox
    "The Sims 4",
    "Stardew Valley",
    "Cities: Skylines",
    "No Man's Sky",
    "Factorio",
    "RimWorld",
    "Planet Zoo",
    # Racing
    "Forza Horizon 5",
    "Gran Turismo 7",
    "Need for Speed: Heat",
    "F1 23",
    "Dirt Rally 2.0",
    # Horror / Survival
    "Resident Evil Village",
    "Resident Evil 4 (Remake)",
    "Dead Space (Remake)",
    "Alien: Isolation",
    "Subnautica",
    "The Forest",
    "Green Hell",
    # Platformer / Indie
    "Celeste",
    "Hades",
    "Ori and the Will of the Wisps",
    "Cuphead",
    "Disco Elysium",
    "Undertale",
    "Shovel Knight",
    # Fighting / Sports
    "Mortal Kombat 11",
    "Street Fighter 6",
    "FIFA 23",
    "NBA 2K23",
    # MMO / Multiplayer
    "World of Warcraft",
    "Path of Exile",
    "Deep Rock Galactic",
    "Phasmophobia",
    "It Takes Two",
    "A Way Out",
    # Puzzle / Casual
    "Portal 2",
    "The Witness",
    "Return of the Obra Dinn",
]

GENRE_MAP = {
    "action":                 "Action",
    "adventure":              "Adventure",
    "role-playing-games-rpg": "RPG",
    "shooter":                "Shooter",
    "strategy":               "Strategy",
    "simulation":             "Simulation",
    "sports":                 "Sports",
    "racing":                 "Racing",
    "fighting":               "Fighting",
    "puzzle":                 "Puzzle",
    "platformer":             "Platformer",
    "massively-multiplayer":  "MMO",
    "arcade":                 "Arcade",
    "indie":                  "Indie",
    "casual":                 "Casual",
    "family":                 "Family",
    "card":                   "Card",
    "board-games":            "Board Games",
}

# More specific genres take priority over generic "Action"/"Adventure"
GENRE_PRIORITY = [
    "RPG", "Strategy", "Racing", "Simulation", "Puzzle",
    "Platformer", "Fighting", "Sports", "MMO", "Shooter",
    "Indie", "Adventure", "Action", "Casual", "Arcade",
    "Family", "Card", "Board Games",
]


def resolve_genre(genres: list[str]) -> str:
    for preferred in GENRE_PRIORITY:
        if preferred in genres:
            return preferred
    return genres[0] if genres else ""

NOISE_TAGS = {
    "singleplayer", "multiplayer", "steam achievements", "full controller support",
    "steam cloud", "great soundtrack", "stats", "steam trading cards",
    "steam leaderboards", "includes level editor", "commentary available",
}


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def rget(path, **params):
    r = httpx.get(f"{BASE}{path}", params={"key": API_KEY, **params}, timeout=15)
    r.raise_for_status()
    return r.json()


def search_game(name):
    data = rget("/games", search=name, search_precise=True, page_size=5)
    results = data.get("results", [])
    if not results:
        data = rget("/games", search=name, page_size=5)
        results = data.get("results", [])
    return results[0]["id"] if results else None


def fetch_game(rawg_id):
    d = rget(f"/games/{rawg_id}")

    genres = [GENRE_MAP.get(g["slug"], g["name"]) for g in d.get("genres", [])]
    genre  = resolve_genre(genres)

    raw_tags = [t["name"] for t in d.get("tags", [])
                if t.get("language") == "eng"]
    tags = [t for t in raw_tags if t.lower() not in NOISE_TAGS][:12]

    platforms = list({
        p["platform"]["name"]
        for p in d.get("platforms") or []
    })

    devs = [x["name"] for x in d.get("developers") or []]
    pubs = [x["name"] for x in d.get("publishers") or []]

    esrb = (d.get("esrb_rating") or {}).get("name", "")
    desc = strip_html(d.get("description", ""))[:1000]

    release_year = 0
    rd = d.get("released", "")
    if rd and len(rd) >= 4:
        release_year = int(rd[:4])

    return {
        "rawg_id":     d["id"],
        "title":       d["name"],
        "genre":       genre,
        "genres":      genres,
        "tags":        tags,
        "description": desc,
        "release_year": release_year,
        "rating":      round(float(d.get("rating") or 0), 2),
        "metacritic":  d.get("metacritic") or 0,
        "playtime":    d.get("playtime") or 0,
        "platforms":   platforms,
        "developers":  devs,
        "publishers":  pubs,
        "esrb_rating": esrb,
        "poster_url":  d.get("background_image") or "",
    }


# ── DB ────────────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_URL)
cur  = conn.cursor()

cur.execute("DROP TABLE IF EXISTS games;")
cur.execute("""
CREATE TABLE games (
    id           SERIAL PRIMARY KEY,
    title        TEXT NOT NULL,
    genre        TEXT NOT NULL DEFAULT '',
    genres       TEXT[] NOT NULL DEFAULT '{}',
    tags         TEXT[] NOT NULL DEFAULT '{}',
    description  TEXT NOT NULL DEFAULT '',
    release_year INTEGER NOT NULL DEFAULT 0,
    rating       NUMERIC(3,2) NOT NULL DEFAULT 0,
    metacritic   INTEGER NOT NULL DEFAULT 0,
    playtime     INTEGER NOT NULL DEFAULT 0,
    platforms    TEXT[] NOT NULL DEFAULT '{}',
    developers   TEXT[] NOT NULL DEFAULT '{}',
    publishers   TEXT[] NOT NULL DEFAULT '{}',
    esrb_rating  TEXT NOT NULL DEFAULT '',
    poster_url   TEXT NOT NULL DEFAULT '',
    rawg_id      INTEGER NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""")
conn.commit()
print("Table created.\n")

# ── Collect IDs (priority first, then extra) ──────────────────────────────────
all_names = PRIORITY + EXTRA
seen_ids  = set()
ordered_ids = []

print("Searching games...")
for name in all_names:
    try:
        gid = search_game(name)
        time.sleep(0.2)
        if gid and gid not in seen_ids:
            seen_ids.add(gid)
            ordered_ids.append((name, gid))
            print(f"  found  {name}")
        elif not gid:
            print(f"  [404]  {name}")
    except Exception as e:
        print(f"  [err]  {name}: {e}")

print(f"\nFound {len(ordered_ids)} games — inserting...\n")

# ── Insert ────────────────────────────────────────────────────────────────────
inserted = 0
skipped  = 0
failed   = 0

for name, rawg_id in ordered_ids:
    if inserted >= 100:
        break
    try:
        g = fetch_game(rawg_id)
        time.sleep(0.2)

        if not g["poster_url"] or not g["description"]:
            print(f"  [skip] {g['title']} — missing fields")
            failed += 1
            continue

        cur.execute("""
            INSERT INTO games
                (title, genre, genres, tags, description, release_year,
                 rating, metacritic, playtime, platforms,
                 developers, publishers, esrb_rating, poster_url, rawg_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (rawg_id) DO NOTHING
            RETURNING id
        """, (
            g["title"], g["genre"], g["genres"], g["tags"],
            g["description"], g["release_year"], g["rating"],
            g["metacritic"], g["playtime"], g["platforms"],
            g["developers"], g["publishers"], g["esrb_rating"],
            g["poster_url"], g["rawg_id"],
        ))
        conn.commit()

        if cur.fetchone():
            print(f"  + [{g['genre']:12}] {g['title']} ({g['release_year']})  ★{g['rating']}  MC:{g['metacritic'] or '—'}")
            inserted += 1
        else:
            skipped += 1

    except Exception as e:
        conn.rollback()
        print(f"  [err] {name}: {e}")
        failed += 1

cur.execute("SELECT COUNT(*) FROM games;")
total = cur.fetchone()[0]
cur.close()
conn.close()

print(f"\nInserted: {inserted} | Skipped: {skipped} | Failed: {failed}")
print(f"Total in DB: {total}")
