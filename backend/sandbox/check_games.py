import psycopg2, psycopg2.extras, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parents[1] / ".env")
conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()
cur.execute("""
    SELECT id, title, genre, genres, tags FROM games
    WHERE title ILIKE '%uncharted%'
       OR title ILIKE '%age of empires%'
       OR title ILIKE '%silksong%'
       OR title ILIKE '%total war%'
    ORDER BY title
""")
for r in cur.fetchall():
    print(f"[{r['id']:3d}] {r['title']}")
    print(f"  genre:  {r['genre']}")
    print(f"  genres: {r['genres']}")
    print(f"  tags:   {r['tags']}")
    print()
cur.close(); conn.close()
