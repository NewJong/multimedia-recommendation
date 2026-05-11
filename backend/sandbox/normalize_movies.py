"""
Cleans keywords for all movies already in DB:
  - Removes pure plot-device keywords with no taste signal
  - Merges obvious synonyms
  - Deduplicates
Run: python normalize_movies.py
"""
import sys, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")

DB_URL = os.getenv("DATABASE_URL")

# Keywords that carry no taste signal — too generic or structural
REMOVE = {
    # narrative devices (present in almost every film)
    "flashback", "voice over", "narration", "nonlinear timeline",
    "twist ending", "twist in the end", "surprise ending",
    "based on novel", "based on true story", "based on true events",
    "based on a true story", "based on real events",
    "based on book", "based on short story",
    # production descriptors
    "independent film", "cult film", "cult classic",
    "female protagonist", "male protagonist",
    "ensemble cast", "cameo",
    # time descriptors (too broad)
    "1980s", "1990s", "2000s", "1970s", "1960s", "1950s", "1940s", "1930s",
    "19th century", "20th century", "21st century",
    # location noise (cities, states, countries — not taste signals)
    "new york", "los angeles", "london", "paris", "america", "england", "france",
    "washington dc, usa", "los angeles, california", "san francisco, california",
    "malibu", "brooklyn, new york city", "new mexico", "texas", "virginia",
    "maine", "massachusetts", "california", "minnesota", "tennessee",
    "rome, italy", "paris, france", "london, england", "tokyo, japan",
    "south korea", "seoul, south korea", "italy", "australia", "africa",
    "europe", "middle east", "jamaica", "caribbean sea",
    # structural / meta — not about taste
    "based on comic", "based on novel or book", "based on young adult novel",
    "sequel", "remake", "prequel", "reboot",
}

# Synonym merges: lowercase key → canonical value
MERGE = {
    "sci fi":              "sci-fi",
    "science fiction":     "sci-fi",
    "post apocalypse":     "post-apocalyptic",
    "post-apocalypse":     "post-apocalyptic",
    "post apocalyptic":    "post-apocalyptic",
    "super hero":          "superhero",
    "super-hero":          "superhero",
    "artificial intelligence": "AI",
    "a.i.":                "AI",
    "time travel":         "time travel",
    "time-travel":         "time travel",
    "serial killer":       "serial killer",
    "mass murder":         "serial killer",
    "anti hero":           "anti-hero",
    "anti-hero":           "anti-hero",
    "road trip":           "road trip",
    "road movie":          "road trip",
    "coming of age":       "coming-of-age",
    "coming-of-age story": "coming-of-age",
    "world domination":    "world domination",
    "super villain":       "supervillain",
    "dystopia":            "dystopian",
    "dystopian society":   "dystopian",
    "dystopian future":    "dystopian",
}


def normalise_keyword(kw: str) -> str | None:
    low = kw.lower().strip()
    if low in REMOVE:
        return None
    canonical = MERGE.get(low)
    if canonical:
        return canonical
    return kw.strip()


def normalise_list(keywords: list[str]) -> list[str]:
    seen = set()
    result = []
    for kw in keywords:
        cleaned = normalise_keyword(kw)
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

cur.execute("SELECT id, title, keywords FROM movies ORDER BY id")
movies = cur.fetchall()

updated   = 0
unchanged = 0

for m in movies:
    new_kw = normalise_list(m["keywords"] or [])

    if new_kw == list(m["keywords"] or []):
        unchanged += 1
        continue

    removed = [x for x in (m["keywords"] or []) if x not in new_kw]

    cur.execute("UPDATE movies SET keywords=%s WHERE id=%s", (new_kw, m["id"]))
    conn.commit()
    updated += 1

    print(f"  [{m['id']:3d}] {m['title']}")
    if removed:
        print(f"        removed: {removed}")

cur.close()
conn.close()

print(f"\nUpdated: {updated} | Unchanged: {unchanged}")
