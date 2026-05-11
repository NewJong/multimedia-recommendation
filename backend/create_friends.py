import psycopg2, os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_url TEXT;")

cur.execute("""
CREATE TABLE IF NOT EXISTS friend_requests (
    id          SERIAL PRIMARY KEY,
    from_uid    VARCHAR(128) NOT NULL,
    to_uid      VARCHAR(128) NOT NULL,
    status      VARCHAR(10)  NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted')),
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (from_uid, to_uid)
);
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_fr_from ON friend_requests(from_uid);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_fr_to   ON friend_requests(to_uid);")

conn.commit()
cur.close()
conn.close()
print("OK: photo_url added to users, friend_requests table created")
