"""
Adds social link columns to users table and seeds Ruslan's links.
Run: python migrate_socials.py
"""
import sys, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parents[1] / ".env")
DB_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur  = conn.cursor()

# Add columns
cur.execute("""
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS social_telegram  TEXT NOT NULL DEFAULT '',
        ADD COLUMN IF NOT EXISTS social_instagram TEXT NOT NULL DEFAULT '',
        ADD COLUMN IF NOT EXISTS social_steam     TEXT NOT NULL DEFAULT '',
        ADD COLUMN IF NOT EXISTS social_discord   TEXT NOT NULL DEFAULT '',
        ADD COLUMN IF NOT EXISTS social_tiktok    TEXT NOT NULL DEFAULT ''
""")
conn.commit()
print("Columns added.")

# Seed Ruslan's data
cur.execute("SELECT firebase_uid, name, email FROM users WHERE email = 'zserdec@gmail.com'")
ruslan = cur.fetchone()
if ruslan:
    cur.execute("""
        UPDATE users SET
            social_telegram  = %s,
            social_instagram = %s,
            social_steam     = %s,
            social_discord   = %s,
            social_tiktok    = %s
        WHERE firebase_uid = %s
    """, (
        "@ruslan_khoroshev",
        "https://www.instagram.com/ruslan_khor?igsh=Y3A1ZnhyNDdiemht&utm_source=qr",
        "https://steamcommunity.com/profiles/76561199055875215/",
        "ruslan_newjong",
        "newjong",
        ruslan["firebase_uid"],
    ))
    conn.commit()
    print(f"Seeded socials for {ruslan['name']} ({ruslan['email']})")
else:
    print("User zserdec@gmail.com not found — run app first to sync Firebase user")

cur.close()
conn.close()
