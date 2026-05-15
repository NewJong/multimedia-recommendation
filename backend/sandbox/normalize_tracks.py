import sys, re, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

DB_URL = os.getenv("DATABASE_URL")

NOISE = {
    "seen live", "best intro ever", "sonicuniverse", "beautiful", "emotional",
    "radio", "radio edit", "favorite", "amazing", "awesome", "great", "love",
    "lovely", "nice", "good", "perfect", "favorites", "my favorite", "love it",
    "lush", "dreamy", "chillout", "mellow", "catchy", "epic", "legendary",
    "timeless", "masterpiece", "brilliant", "chill", "relax", "relaxing",
    "party", "workout", "running", "study", "sleep",
    "rock",
    "80s", "70s", "90s", "60s", "50s",
}

MERGE = {
    "alternative":         "Alternative Rock",
    "pop":                 "Pop",
    "electronic":          "Electronic",
    "jazz":                "Jazz",
    "soul":                "Soul/Blues",
    "blues":               "Soul/Blues",
    "punk":                "Punk/Emo",
    "indie":               "Indie",
    "folk":                "Folk",
    "metal":               "Metal",
    "progressive rock":    "Progressive Rock",
    "fusion":              "Jazz",
    "hip hop":             "Hip-Hop",
    "hip-hop":             "Hip-Hop",
    "hiphop":              "Hip-Hop",
    "rap":                 "Hip-Hop",
    "trap":                "Hip-Hop",
    "electronic music":    "Electronic",
    "electronica":         "Electronic",
    "electro":             "Electronic",
    "edm":                 "Electronic",
    "dance":               "Electronic",
    "dance music":         "Electronic",
    "trip hop":            "Trip-Hop",
    "trip-hop":            "Trip-Hop",
    "rock music":          "Rock",
    "alternative rock":    "Alternative Rock",
    "indie rock":          "Indie Rock",
    "hard rock":           "Hard Rock",
    "classic rock":        "Classic Rock",
    "post-grunge":         "Grunge",
    "grunge":              "Grunge",
    "heavy metal":         "Metal",
    "alternative metal":   "Metal",
    "thrash metal":        "Metal",
    "nu metal":            "Metal",
    "death metal":         "Metal",
    "black metal":         "Metal",
    "pop music":           "Pop",
    "electropop":          "Pop",
    "dance-pop":           "Pop",
    "alt-pop":             "Pop",
    "jazz music":          "Jazz",
    "vocal jazz":          "Jazz",
    "jazz piano":          "Jazz",
    "bebop":               "Jazz",
    "folk music":          "Folk",
    "indie folk":          "Folk",
    "singer-songwriter":   "Folk",
    "acoustic":            "Folk",
    "rhythm and blues":    "Soul/Blues",
    "r&b":                 "Soul/Blues",
    "rnb":                 "Soul/Blues",
    "soul music":          "Soul/Blues",
    "blues music":         "Soul/Blues",
    "funk":                "Soul/Blues",
    "punk rock":           "Punk/Emo",
    "punk music":          "Punk/Emo",
    "emo":                 "Punk/Emo",
    "contemporary classical": "Classical",
    "modern classical":    "Classical",
    "neoclassical":        "Classical",
    "post-classical":      "Classical",
    "orchestral":          "Classical",
    "symphonic":           "Classical",
    "minimalism":          "Classical",
    "reggae music":        "Reggae",
    "ska":                 "Reggae",
    "post rock":           "Post-Rock",
    "post-rock":           "Post-Rock",
    "math rock":           "Post-Rock",
    "ambient music":       "Ambient",
    "lo-fi":               "Lo-Fi",
    "lo fi":               "Lo-Fi",
    "lofi":                "Lo-Fi",
    "lofi hip hop":        "Lo-Fi",
}

TAG_TO_GENRE = {
    "Hip-Hop": "Hip-Hop", "Electronic": "Electronic", "Trip-Hop": "Trip-Hop",
    "Rock": "Rock", "Alternative Rock": "Rock", "Indie Rock": "Rock",
    "Hard Rock": "Rock", "Classic Rock": "Rock", "Grunge": "Rock",
    "Metal": "Metal", "Pop": "Pop", "Jazz": "Jazz", "Folk": "Folk",
    "Soul/Blues": "Soul/Blues", "Punk/Emo": "Punk/Emo", "Classical": "Classical",
    "Reggae": "Reggae", "Post-Rock": "Post-Rock", "Ambient": "Electronic",
    "Lo-Fi": "Electronic",
}


def normalise_tag(tag: str) -> str | None:
    low = tag.lower().strip()
    if low in NOISE:
        return None
    if re.fullmatch(r"\d{4}s?", low):
        return None
    if re.search(r"fm\b|\d+\.\d+", tag, re.I):
        return None
    canonical = MERGE.get(low)
    if canonical:
        return canonical
    return tag.strip()


def normalise_list(tags: list[str]) -> list[str]:
    seen = set()
    result = []
    for tag in tags:
        cleaned = normalise_tag(tag)
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def derive_genre(tags: list[str]) -> str:
    for tag in tags:
        g = TAG_TO_GENRE.get(tag)
        if g:
            return g
    return ""


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

cur.execute("SELECT id, artist, name, genre, tags FROM tracks ORDER BY id")
tracks = cur.fetchall()

updated   = 0
unchanged = 0

for t in tracks:
    new_tags  = normalise_list(t["tags"] or [])
    new_genre = t["genre"] or derive_genre(new_tags)
    if not new_genre:
        new_genre = derive_genre(new_tags)

    if new_tags == list(t["tags"] or []) and new_genre == t["genre"]:
        unchanged += 1
        continue

    removed = [x for x in (t["tags"] or []) if x not in new_tags]

    cur.execute(
        "UPDATE tracks SET tags=%s, genre=%s WHERE id=%s",
        (new_tags, new_genre, t["id"])
    )
    conn.commit()
    updated += 1

    print(f"  [{t['id']:3d}] {t['artist']} — {t['name']}")
    if removed:
        print(f"        removed: {removed}")
    if new_genre != t["genre"]:
        print(f"        genre: '{t['genre']}' → '{new_genre}'")

cur.close()
conn.close()

print(f"\nUpdated: {updated} | Unchanged: {unchanged}")
