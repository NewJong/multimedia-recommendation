import psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os
load_dotenv(Path(__file__).parents[1] / ".env")
conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()
cur.execute("SELECT id, tags FROM games WHERE id=51")
r = cur.fetchone()
tags = list(r["tags"] or [])
if "Open World" in tags:
    tags.remove("Open World")
    print("removed Open World")
cur.execute("UPDATE games SET tags=%s WHERE id=51", (tags,))
conn.commit()
print(f"Civ VI tags: {tags}")
cur.close(); conn.close()
