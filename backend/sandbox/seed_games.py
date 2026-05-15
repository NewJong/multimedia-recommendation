"""
Fetches up to 100 NEW games from RAWG and inserts them into the existing table.
Does NOT drop or recreate the table.
Run: python seed_games.py
"""
import sys, httpx, psycopg2, psycopg2.extras, time, re
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

API_KEY = os.getenv("RAWG_API_KEY")
DB_URL  = os.getenv("DATABASE_URL")
BASE    = "https://api.rawg.io/api"

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

EXTRA = [
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
    "Civilization VI",
    "Total War: Three Kingdoms",
    "StarCraft II",
    "XCOM 2",
    "Age of Empires IV",
    "Into the Breach",
    "Crusader Kings III",
    "Anno 1800",
    "The Sims 4",
    "Stardew Valley",
    "Cities: Skylines",
    "No Man's Sky",
    "Factorio",
    "RimWorld",
    "Planet Zoo",
    "Forza Horizon 5",
    "Gran Turismo 7",
    "Need for Speed: Heat",
    "F1 23",
    "Dirt Rally 2.0",
    "Resident Evil Village",
    "Resident Evil 4 (Remake)",
    "Dead Space (Remake)",
    "Alien: Isolation",
    "Subnautica",
    "The Forest",
    "Green Hell",
    "Celeste",
    "Hades",
    "Ori and the Will of the Wisps",
    "Cuphead",
    "Disco Elysium",
    "Undertale",
    "Shovel Knight",
    "Mortal Kombat 11",
    "Street Fighter 6",
    "FIFA 23",
    "NBA 2K23",
    "World of Warcraft",
    "Path of Exile",
    "Deep Rock Galactic",
    "Phasmophobia",
    "It Takes Two",
    "A Way Out",
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

GENRE_PRIORITY = [
    "RPG", "Strategy", "Racing", "Simulation", "Puzzle",
    "Platformer", "Fighting", "Sports", "MMO", "Shooter",
    "Indie", "Adventure", "Action", "Casual", "Arcade",
    "Family", "Card", "Board Games",
]

NOISE_TAGS = {
    "singleplayer", "multiplayer", "steam achievements", "full controller support",
    "steam cloud", "great soundtrack", "stats", "steam trading cards",
    "steam leaderboards", "includes level editor", "commentary available",
    "early access", "mature", "teen", "everyone", "everyone 10+", "adults only",
    "moddable",
}


def strip_html(text: str, max_len: int = 1500) -> str:
    import html as _html
    text = _html.unescape(text or "")       
    text = re.sub(r"<[^>]+>", "", text)     
    text = re.sub(r"\n{3,}", "\n\n", text)  
    text = text.strip()
    if len(text) <= max_len:
        return text
    cut = text.rfind(". ", 0, max_len)
    return text[:cut + 1] if cut != -1 else text[:max_len]


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

    raw_tags = [t["name"] for t in d.get("tags", []) if t.get("language") == "eng"]
    tags = [t for t in raw_tags if t.lower() not in NOISE_TAGS]  

    platforms = list({p["platform"]["name"] for p in d.get("platforms") or []})
    devs = [x["name"] for x in d.get("developers") or []]
    pubs = [x["name"] for x in d.get("publishers") or []]
    esrb = (d.get("esrb_rating") or {}).get("name", "")
    desc = strip_html(d.get("description", ""))

    release_year = 0
    rd = d.get("released", "")
    if rd and len(rd) >= 4:
        release_year = int(rd[:4])

    return {
        "rawg_id":      d["id"],
        "title":        d["name"],
        "genres":       genres,
        "tags":         tags,
        "description":  desc,
        "release_year": release_year,
        "rating":       round(float(d.get("rating") or 0), 2),
        "metacritic":   d.get("metacritic") or 0,
        "playtime":     d.get("playtime") or 0,
        "platforms":    platforms,
        "developers":   devs,
        "publishers":   pubs,
        "esrb_rating":  esrb,
        "poster_url":   d.get("background_image") or "",
    }


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

cur.execute("SELECT rawg_id FROM games")
existing_rawg_ids = {r["rawg_id"] for r in cur.fetchall()}
print(f"Already in DB: {len(existing_rawg_ids)} games\n")

all_names   = PRIORITY + EXTRA
seen_ids    = set()
ordered_ids = []

print("Searching for new games...")
for name in all_names:
    try:
        gid = search_game(name)
        time.sleep(0.2)
        if not gid:
            print(f"  [404]  {name}")
            continue
        if gid in existing_rawg_ids:
            print(f"  [skip] {name} — already in DB")
            continue
        if gid not in seen_ids:
            seen_ids.add(gid)
            ordered_ids.append((name, gid))
            print(f"  found  {name}")
    except Exception as e:
        print(f"  [err]  {name}: {e}")

print(f"\n{len(ordered_ids)} new games to fetch — inserting...\n")

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
                (title, genres, tags, description, release_year,
                 rating, metacritic, playtime, platforms,
                 developers, publishers, esrb_rating, poster_url, rawg_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (rawg_id) DO NOTHING
            RETURNING id
        """, (
            g["title"], g["genres"], g["tags"],
            g["description"], g["release_year"], g["rating"],
            g["metacritic"], g["playtime"], g["platforms"],
            g["developers"], g["publishers"], g["esrb_rating"],
            g["poster_url"], g["rawg_id"],
        ))
        conn.commit()

        if cur.fetchone():
            primary = (g['genres'] or ['?'])[0]
            print(f"  + [{primary:12}] {g['title']} ({g['release_year']})  ★{g['rating']}  MC:{g['metacritic'] or '—'}")
            inserted += 1
        else:
            skipped += 1

    except Exception as e:
        conn.rollback()
        print(f"  [err] {name}: {e}")
        failed += 1

cur.execute("SELECT COUNT(*) as n FROM games")
total = cur.fetchone()["n"]
cur.close()
conn.close()

print(f"\nInserted: {inserted} | Skipped: {skipped} | Failed: {failed}")
print(f"Total in DB: {total}")
