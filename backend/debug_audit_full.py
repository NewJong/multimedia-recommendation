import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import psycopg2, psycopg2.extras
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()
cur.execute("SELECT id, title, genre, genres, tags FROM games ORDER BY title")
games = cur.fetchall()
cur.close(); conn.close()

lines = []
for g in games:
    lines.append(f"[{g['id']:3d}] {g['title']}")
    lines.append(f"  genre    : {g['genre']}")
    lines.append(f"  genres[] : {g['genres']}")
    lines.append(f"  tags[]   : {g['tags']}")
    lines.append("")

text = "\n".join(lines)
print(text)
with open("audit_games.txt", "w", encoding="utf-8") as f:
    f.write(text)
print(f"Total: {len(games)} games — saved to audit_games.txt")
