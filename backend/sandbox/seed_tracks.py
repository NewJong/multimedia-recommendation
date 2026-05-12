"""
Fetches up to 100 NEW tracks from Last.fm and inserts them into the existing table.
Skips tracks already present in DB before making any API calls.
Run: python seed_tracks.py
"""
import sys, httpx, psycopg2, psycopg2.extras, time, re
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

API_KEY = os.getenv("LASTFM_API_KEY")
DB_URL  = os.getenv("DATABASE_URL")
BASE    = "https://ws.audioscrobbler.com/2.0"

TRACKS = [
    # Rock
    ("Nirvana",          "Smells Like Teen Spirit"),
    ("Nirvana",          "Come as You Are"),
    ("Pearl Jam",        "Black"),
    ("Pearl Jam",        "Jeremy"),
    ("Foo Fighters",     "Everlong"),
    ("Foo Fighters",     "The Pretender"),
    ("Led Zeppelin",     "Stairway to Heaven"),
    ("Led Zeppelin",     "Whole Lotta Love"),
    ("Queen",            "Bohemian Rhapsody"),
    ("Queen",            "We Will Rock You"),
    ("Pink Floyd",       "Comfortably Numb"),
    ("Pink Floyd",       "Wish You Were Here"),
    ("AC/DC",            "Back in Black"),
    ("AC/DC",            "Highway to Hell"),
    ("The Rolling Stones","Paint It Black"),
    ("The Rolling Stones","Sympathy for the Devil"),
    ("U2",               "With or Without You"),
    ("Coldplay",         "The Scientist"),
    ("Coldplay",         "Fix You"),
    ("Oasis",            "Wonderwall"),
    ("Linkin Park",      "In the End"),
    ("Linkin Park",      "Numb"),
    ("Green Day",        "Boulevard of Broken Dreams"),
    ("Green Day",        "American Idiot"),
    ("The Cure",         "Lovesong"),
    ("Depeche Mode",     "Personal Jesus"),
    # Metal
    ("Metallica",        "Enter Sandman"),
    ("Metallica",        "One"),
    ("Iron Maiden",      "The Trooper"),
    ("Iron Maiden",      "Fear of the Dark"),
    ("Black Sabbath",    "Iron Man"),
    ("Black Sabbath",    "Paranoid"),
    ("Slipknot",         "Duality"),
    ("Slipknot",         "Psychosocial"),
    ("Pantera",          "Walk"),
    ("System of a Down", "Toxicity"),
    ("System of a Down", "Chop Suey!"),
    ("My Chemical Romance", "Welcome to the Black Parade"),
    ("My Chemical Romance", "Teenagers"),
    # Punk / Emo
    ("Green Day",        "Good Riddance (Time of Your Life)"),
    ("The Offspring",    "Come Out and Play"),
    ("Blink-182",        "All the Small Things"),
    ("Blink-182",        "What's My Age Again?"),
    # Hip-Hop
    ("Eminem",           "Lose Yourself"),
    ("Eminem",           "Stan"),
    ("Kendrick Lamar",   "HUMBLE."),
    ("Kendrick Lamar",   "Swimming Pools (Drank)"),
    ("Kanye West",       "Stronger"),
    ("Kanye West",       "Gold Digger"),
    ("Jay-Z",            "99 Problems"),
    ("Nas",              "N.Y. State of Mind"),
    ("J. Cole",          "No Role Modelz"),
    ("Outkast",          "Hey Ya!"),
    # R&B / Soul
    ("The Weeknd",       "Blinding Lights"),
    ("The Weeknd",       "Save Your Tears"),
    ("Frank Ocean",      "Thinkin Bout You"),
    ("Beyonce",          "Crazy in Love"),
    ("Amy Winehouse",    "Rehab"),
    ("Amy Winehouse",    "Back to Black"),
    ("Alicia Keys",      "Fallin'"),
    ("Sam Smith",        "Stay with Me"),
    ("Usher",            "Yeah!"),
    # Pop
    ("Taylor Swift",     "Blank Space"),
    ("Taylor Swift",     "Shake It Off"),
    ("Ed Sheeran",       "Shape of You"),
    ("Ed Sheeran",       "Thinking Out Loud"),
    ("Adele",            "Rolling in the Deep"),
    ("Adele",            "Someone Like You"),
    ("Bruno Mars",       "Uptown Funk"),
    ("Bruno Mars",       "Grenade"),
    ("Dua Lipa",         "Levitating"),
    ("Michael Jackson",  "Thriller"),
    ("Michael Jackson",  "Billie Jean"),
    ("David Bowie",      "Heroes"),
    ("David Bowie",      "Space Oddity"),
    # Electronic / Dance
    ("Daft Punk",        "Get Lucky"),
    ("Daft Punk",        "One More Time"),
    ("The Chemical Brothers", "Galvanize"),
    ("Massive Attack",   "Teardrop"),
    ("Massive Attack",   "Unfinished Sympathy"),
    ("Aphex Twin",       "Windowlicker"),
    ("Boards of Canada", "Roygbiv"),
    # Trip-Hop
    ("Portishead",       "Glory Box"),
    ("Portishead",       "Roads"),
    ("Portishead",       "Sour Times"),
    # Jazz
    ("Miles Davis",      "So What"),
    ("John Coltrane",    "My Favorite Things"),
    ("Bill Evans",       "Waltz for Debby"),
    ("Dave Brubeck",     "Take Five"),
    ("Chet Baker",       "My Funny Valentine"),
    ("Thelonious Monk",  "'Round Midnight"),
    ("Norah Jones",      "Don't Know Why"),
    # Folk / Acoustic
    ("Nick Drake",       "Pink Moon"),
    ("Bon Iver",         "Skinny Love"),
    ("Phoebe Bridgers",  "Savior Complex"),
    ("Sufjan Stevens",   "Death with Dignity"),
    ("Iron & Wine",      "Naked as We Came"),
    # Indie / Dream Pop
    ("Radiohead",        "Creep"),
    ("Radiohead",        "No Surprises"),
    ("The xx",           "Intro"),
    ("Cigarettes After Sex", "Apocalypse"),
    ("Mazzy Star",       "Fade Into You"),
    ("Arcade Fire",      "Wake Up"),
    ("Interpol",         "Obstacle 1"),
    # Classical / Neoclassical
    ("Ludovico Einaudi", "Experience"),
    ("Max Richter",      "On the Nature of Daylight"),
    ("Explosions in the Sky", "The Birth and Death of the Day"),
    # Reggae
    ("Bob Marley",       "No Woman No Cry"),
    ("Bob Marley",       "Redemption Song"),
    ("Bob Marley",       "One Love"),
    # Soul / Blues
    ("Ray Charles",      "Hit the Road Jack"),
    ("B.B. King",        "The Thrill Is Gone"),
    ("Otis Redding",     "Sittin' On The Dock of the Bay"),
]

TAG_TO_GENRE = {
    "alternative metal": "Metal", "heavy metal": "Metal", "thrash metal": "Metal",
    "death metal": "Metal", "black metal": "Metal", "nu metal": "Metal", "metal": "Metal",
    "post-grunge": "Rock", "grunge": "Rock", "hard rock": "Rock", "classic rock": "Rock",
    "alternative rock": "Rock", "indie rock": "Rock", "alternative": "Rock", "rock": "Rock",
    "punk rock": "Punk/Emo", "punk": "Punk/Emo", "emo": "Punk/Emo",
    "avant-garde jazz": "Jazz", "modal jazz": "Jazz", "hard bop": "Jazz", "cool jazz": "Jazz",
    "free jazz": "Jazz", "vocal jazz": "Jazz", "jazz piano": "Jazz", "bebop": "Jazz",
    "jazz fusion": "Jazz", "jazz": "Jazz",
    "singer-songwriter": "Folk", "indie folk": "Folk", "acoustic": "Folk", "folk": "Folk",
    "dream pop": "Indie", "shoegaze": "Indie", "slowcore": "Indie",
    "indie pop": "Indie", "indie": "Indie",
    "electropop": "Pop", "dance-pop": "Pop", "alt-pop": "Pop", "pop": "Pop",
    "hip-hop": "Hip-Hop", "hip hop": "Hip-Hop", "trap": "Hip-Hop", "rap": "Hip-Hop",
    "trip-hop": "Trip-Hop", "trip hop": "Trip-Hop",
    "lo-fi": "Electronic", "ambient": "Electronic", "electronic": "Electronic", "techno": "Electronic",
    "house": "Electronic", "idm": "Electronic",
    "contemporary classical": "Classical", "modern classical": "Classical",
    "neoclassical": "Classical", "minimalism": "Classical", "orchestral": "Classical",
    "symphonic": "Classical", "classical": "Classical",
    "soundtracks": "Soundtrack", "soundtrack": "Soundtrack", "score": "Soundtrack",
    "soul": "Soul/Blues", "blues": "Soul/Blues", "rhythm and blues": "Soul/Blues",
    "r&b": "Soul/Blues", "funk": "Soul/Blues",
    "reggae": "Reggae", "ska": "Reggae",
    "piano": "Instrumental", "instrumental": "Instrumental",
    "post-rock": "Post-Rock", "post rock": "Post-Rock",
}

NOISE = {
    "seen live", "best intro ever", "sonicuniverse", "beautiful", "emotional",
    "radio", "peter", "radio edit", "favorite", "amazing", "awesome", "great",
    "love", "lovely", "nice", "good", "perfect", "classic", "favorites",
    "my favorite", "love it", "lush", "dreamy", "chillout", "mellow",
}


def clean_tags(tags, artist):
    result = []
    for t in tags:
        low = t.lower().strip()
        if low == artist.lower():
            continue
        if low in NOISE:
            continue
        if re.search(r"fm\b|\d+\.\d+|^\d{4}$", t, re.I):
            continue
        result.append(t)
    return result


def resolve_genre(tags):
    for t in tags:
        g = TAG_TO_GENRE.get(t.lower().strip())
        if g:
            return g
    return ""


def strip_html(text):
    text = re.sub(r"<a href[^>]*>.*?</a>", "", text, flags=re.DOTALL)
    return text.strip()


def lfm(method, **params):
    r = httpx.get(BASE, params={"method": method, "api_key": API_KEY, "format": "json", **params}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data["message"])
    return data


artist_summary_cache = {}

def get_artist_summary(artist):
    if artist in artist_summary_cache:
        return artist_summary_cache[artist]
    try:
        data = lfm("artist.getInfo", artist=artist)
        bio = data["artist"]["bio"]["summary"]
        result = strip_html(bio)[:600]
        artist_summary_cache[artist] = result
        time.sleep(0.25)
    except Exception:
        result = ""
        artist_summary_cache[artist] = result
    return result


def fetch_track(artist, title):
    data = lfm("track.getInfo", artist=artist, track=title)
    t = data["track"]

    image = ""
    if "album" in t:
        for img in reversed(t["album"].get("image", [])):
            if img["#text"]:
                image = img["#text"]
                break

    album   = t.get("album", {}).get("title", "") or ""
    summary = strip_html(t.get("wiki", {}).get("summary", ""))
    if not summary:
        summary = get_artist_summary(artist)

    tags = clean_tags(
        [tag["name"] for tag in t.get("toptags", {}).get("tag", [])],
        artist
    )
    if not tags:
        try:
            raw  = lfm("artist.getTopTags", artist=artist)
            tags = clean_tags(
                [tg["name"] for tg in raw["toptags"]["tag"][:8]],
                artist
            )
            time.sleep(0.2)
        except Exception:
            pass

    primary = resolve_genre(tags)
    return {
        "name":        t["name"],
        "genres":      [primary] if primary else [],
        "tags":        tags,
        "artist":      t["artist"]["name"],
        "album":       album,
        "duration_ms": int(t.get("duration") or 0),
        "listeners":   int(t.get("listeners") or 0),
        "playcount":   int(t.get("playcount") or 0),
        "summary":     summary,
        "image_url":   image,
        "url":         t.get("url", ""),
    }


# ── DB ────────────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

# Load existing (name, artist) pairs — normalised to lowercase for comparison
cur.execute("SELECT LOWER(name) as name, LOWER(artist) as artist FROM tracks")
existing = {(r["name"], r["artist"]) for r in cur.fetchall()}
print(f"Already in DB: {len(existing)} tracks\n")

# Filter out tracks we already have before hitting the API
new_tracks = [
    (artist, title) for artist, title in TRACKS
    if (title.lower(), artist.lower()) not in existing
]
print(f"{len(new_tracks)} new tracks to fetch ({len(TRACKS) - len(new_tracks)} already in DB)\n")

inserted = 0
skipped  = 0
failed   = 0

for artist, title in new_tracks:
    if inserted >= 100:
        break
    try:
        info = fetch_track(artist, title)
        time.sleep(0.25)

        if not info["image_url"] or not info["album"]:
            print(f"  [skip] {artist} — {title}  (image={bool(info['image_url'])}, album={bool(info['album'])})")
            failed += 1
            continue

        cur.execute("""
            INSERT INTO tracks
                (name, genres, tags, artist, album, duration_ms,
                 listeners, playcount, summary, image_url, url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (name, artist) DO NOTHING
            RETURNING id
        """, (
            info["name"], info["genres"], info["tags"], info["artist"],
            info["album"], info["duration_ms"], info["listeners"],
            info["playcount"], info["summary"], info["image_url"], info["url"],
        ))
        conn.commit()

        if cur.fetchone():
            primary = (info['genres'] or ['?'])[0]
            print(f"  + [{primary:15}] {info['artist']} — {info['name']}")
            inserted += 1
        else:
            print(f"  ~ exists: {info['artist']} — {info['name']}")
            skipped += 1

    except Exception as e:
        conn.rollback()
        print(f"  [err] {artist} — {title}: {e}")
        failed += 1

cur.execute("SELECT COUNT(*) as n FROM tracks")
total = cur.fetchone()["n"]
cur.close()
conn.close()

print(f"\nInserted: {inserted} | Skipped: {skipped} | Failed/incomplete: {failed}")
print(f"Total in DB: {total}")
