import psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os
load_dotenv(Path(__file__).parents[1] / ".env")
conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()
cur.execute("SELECT id, tags FROM games WHERE id=28")
r = cur.fetchone()
tags = list(r["tags"] or [])
to_add = ["Story Rich", "Cinematic", "Exploration", "Stealth", "Third-Person Shooter"]
seen = {t.lower() for t in tags}
for t in to_add:
    if t.lower() not in seen:
        tags.append(t)
cur.execute("UPDATE games SET tags=%s WHERE id=28", (tags,))
conn.commit()
print(f"Uncharted 4 tags: {tags}")
cur.close(); conn.close()
