"""
Fetches up to 100 NEW movies from TMDB and inserts them into the existing table.
Does NOT drop or recreate the table.
Run: python seed_movies.py
"""
import sys, httpx, psycopg2, psycopg2.extras, time
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

API_KEY = os.getenv("IMDB_API_KEY")
DB_URL  = os.getenv("DATABASE_URL")
BASE    = "https://api.themoviedb.org/3"
IMG     = "https://image.tmdb.org/t/p/w500"
BACK    = "https://image.tmdb.org/t/p/w1280"

HEADERS = {"Authorization": f"Bearer {os.getenv('IMDB_API_ACCESS_KEY')}"}

GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi",
    53: "Thriller", 10752: "War", 37: "Western",
}

# Fetch across genres — discovers more unique IDs than we need, stops at 100 inserts
GENRE_PAGES = [
    (28,    2),  # Action
    (35,    2),  # Comedy
    (18,    2),  # Drama
    (27,    2),  # Horror
    (878,   2),  # Sci-Fi
    (53,    1),  # Thriller
    (10749, 1),  # Romance
    (16,    1),  # Animation
    (80,    1),  # Crime
    (14,    1),  # Fantasy
    (12,    1),  # Adventure
    (10752, 1),  # War
    (37,    1),  # Western
    (99,    1),  # Documentary
]


def get(path, **params):
    r = httpx.get(f"{BASE}{path}", headers=HEADERS,
                  params={"language": "en-US", **params}, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_movie(tmdb_id):
    d = get(f"/movie/{tmdb_id}", append_to_response="credits,keywords")

    genres   = [GENRE_MAP.get(g["id"], g["name"]) for g in d.get("genres", [])]
    kw_list  = d.get("keywords", {}).get("keywords", [])
    keywords = [k["name"] for k in kw_list[:15]]

    crew     = d.get("credits", {}).get("crew", [])
    cast_raw = d.get("credits", {}).get("cast", [])
    director = next((p["name"] for p in crew if p["job"] == "Director"), "")
    cast     = [p["name"] for p in cast_raw[:6]]

    poster   = f"{IMG}{d['poster_path']}"   if d.get("poster_path")   else ""
    backdrop = f"{BACK}{d['backdrop_path']}" if d.get("backdrop_path") else ""

    release_year = int(d.get("release_date", "0")[:4]) if d.get("release_date") else 0
    collection   = d.get("belongs_to_collection") or {}

    return {
        "tmdb_id":       d["id"],
        "title":         d["title"],
        "genres":        genres,
        "keywords":      keywords,
        "overview":      d.get("overview", ""),
        "tagline":       d.get("tagline", ""),
        "release_year":  release_year,
        "runtime":       d.get("runtime") or 0,
        "rating":        round(float(d.get("vote_average") or 0), 1),
        "vote_count":    d.get("vote_count") or 0,
        "popularity":    round(float(d.get("popularity") or 0), 3),
        "language":      d.get("original_language", ""),
        "status":        d.get("status", ""),
        "director":      director,
        "actors":        cast,
        "poster_url":    poster,
        "backdrop_url":  backdrop,
        "budget":        d.get("budget") or 0,
        "revenue":       d.get("revenue") or 0,
        "collection":    collection.get("name", "") if collection else "",
    }


# ── DB ────────────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

# Load existing tmdb_ids so we skip them
cur.execute("SELECT tmdb_id FROM movies")
existing_tmdb_ids = {r["tmdb_id"] for r in cur.fetchall()}
print(f"Already in DB: {len(existing_tmdb_ids)} movies\n")

# ── Collect candidate IDs from TMDB discover ──────────────────────────────────
seen_ids  = set()
movie_ids = []

for genre_id, pages in GENRE_PAGES:
    for page in range(1, pages + 1):
        data = get("/discover/movie",
                   with_genres=genre_id,
                   sort_by="vote_count.desc",
                   page=page,
                   vote_count_gte=1000)
        for m in data.get("results", []):
            if m["id"] not in seen_ids and m["id"] not in existing_tmdb_ids:
                seen_ids.add(m["id"])
                movie_ids.append(m["id"])
        time.sleep(0.15)

print(f"Collected {len(movie_ids)} new candidate IDs — fetching details...\n")

# ── Fetch & insert ────────────────────────────────────────────────────────────
inserted = 0
skipped  = 0
failed   = 0

for tmdb_id in movie_ids:
    if inserted >= 100:
        break
    try:
        m = fetch_movie(tmdb_id)
        time.sleep(0.2)

        if not m["poster_url"] or not m["overview"] or not m["director"]:
            print(f"  [skip] {m['title']} — missing fields")
            failed += 1
            continue

        cur.execute("""
            INSERT INTO movies
                (title, genres, keywords, overview, tagline,
                 release_year, runtime, rating, vote_count, popularity, language,
                 status, director, actors, poster_url, backdrop_url,
                 budget, revenue, collection, tmdb_id)
            VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (tmdb_id) DO NOTHING
            RETURNING id
        """, (
            m["title"], m["genres"],
            m["keywords"], m["overview"], m["tagline"], m["release_year"],
            m["runtime"], m["rating"], m["vote_count"], m["popularity"],
            m["language"], m["status"], m["director"], m["actors"],
            m["poster_url"], m["backdrop_url"], m["budget"], m["revenue"],
            m["collection"], m["tmdb_id"],
        ))
        conn.commit()

        if cur.fetchone():
            primary = (m['genres'] or ['?'])[0]
            print(f"  + [{primary:15}] {m['title']} ({m['release_year']})  ★{m['rating']}")
            inserted += 1
        else:
            skipped += 1

    except Exception as e:
        conn.rollback()
        print(f"  [err] tmdb:{tmdb_id} — {e}")
        failed += 1

cur.execute("SELECT COUNT(*) as n FROM movies")
total = cur.fetchone()["n"]
cur.close()
conn.close()

print(f"\nInserted: {inserted} | Skipped: {skipped} | Failed: {failed}")
print(f"Total in DB: {total}")
