import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import psycopg2
import psycopg2.extras
from anthropic import Anthropic
from sentence_transformers import SentenceTransformer

DB_URL      = os.getenv("DATABASE_URL")
LLM_KEY     = os.getenv("ANTHROPIC_API_KEY")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL   = "claude-haiku-4-5-20251001"

VIBE_SYSTEM = """You are a semantic normalizer for a multimedia recommendation system.

Given a music track, movie, or video game's metadata, write a SINGLE PARAGRAPH (60-90 words) describing its EXPERIENTIAL essence:
- Mood and emotional tone (melancholic / exhilarating / brooding / playful / bittersweet / etc.)
- Energy and tempo (slow, medium, fast — intense or relaxed)
- Atmosphere (gritty, dreamlike, cinematic, nostalgic, urban, otherworldly, intimate)
- What moment or activity it suits (focus work, late-night drive, workout, melancholy evening, party, contemplation, road trip)
- Thematic abstractions (freedom, isolation, rebellion, longing, escapism, control, chaos)

CRITICAL RULES:
- Use DOMAIN-AGNOSTIC vocabulary. The same words must apply equally to a song, a film, or a game. Avoid medium-specific terms like "gameplay", "soundtrack", "cinematography", "narrative arc", "level design", "vocals".
- DO NOT mention the title, franchise, artist, or release year.
- DO NOT summarize plot or describe mechanics.
- Focus ONLY on what the item FEELS LIKE and WHEN it fits.
- Output the paragraph directly. No preamble, no headers, no labels."""


def build_summary(item: dict, item_type: str) -> str:
    bits: list[str] = []
    if item_type == "track":
        if item.get("name"):   bits.append(f"Title: {item['name']}.")
        if item.get("artist"): bits.append(f"Artist: {item['artist']}.")
        tags = ((item.get("genres") or []) + (item.get("tags") or []))[:12]
        if tags:               bits.append(f"Tags: {', '.join(tags)}.")
        if item.get("summary"):bits.append(f"About: {(item['summary'] or '')[:400]}")
    elif item_type == "movie":
        if item.get("title"):     bits.append(f"Title: {item['title']}.")
        gs = item.get("genres") or []
        if gs:                    bits.append(f"Genres: {', '.join(gs)}.")
        kws = (item.get("keywords") or [])[:12]
        if kws:                   bits.append(f"Keywords: {', '.join(kws)}.")
        if item.get("tagline"):   bits.append(f'Tagline: "{item["tagline"]}".')
        if item.get("overview"):  bits.append(f"Plot: {(item['overview'] or '')[:400]}")
    elif item_type == "game":
        if item.get("title"):     bits.append(f"Title: {item['title']}.")
        tags = ((item.get("genres") or []) + (item.get("tags") or []))[:12]
        if tags:                  bits.append(f"Tags: {', '.join(tags)}.")
        if item.get("description"):bits.append(f"About: {(item['description'] or '')[:400]}")
    return " ".join(bits)


SPECS = [
    ("tracks", "track"),
    ("movies", "movie"),
    ("games",  "game"),
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, default=0)
    p.add_argument("--type", choices=["track", "movie", "game", "all"], default="all")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    print(f"Loading embedding model ({EMBED_MODEL})...")
    embed_model = SentenceTransformer(EMBED_MODEL)
    llm = Anthropic(api_key=LLM_KEY)

    total_in = 0
    total_out = 0

    conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for table, item_type in SPECS:
            if args.type != "all" and args.type != item_type:
                continue

            with conn.cursor() as cur:
                if args.force:
                    sql = f"SELECT * FROM {table} ORDER BY id"
                else:
                    sql = f"SELECT * FROM {table} WHERE vibe_text IS NULL OR vibe_text = '' ORDER BY id"
                if args.sample > 0:
                    sql += f" LIMIT {args.sample}"
                cur.execute(sql)
                rows = cur.fetchall()

            print(f"\n[{table}] {len(rows)} items to process")
            if not rows:
                continue

            for i, row in enumerate(rows, 1):
                summary = build_summary(row, item_type)
                try:
                    msg = llm.messages.create(
                        model=LLM_MODEL,
                        max_tokens=220,
                        system=VIBE_SYSTEM,
                        messages=[{"role": "user", "content": summary}],
                    )
                except Exception as e:
                    print(f"  [{i}/{len(rows)}] LLM failure for id={row['id']}: {e}")
                    continue

                vibe = msg.content[0].text.strip()
                total_in  += msg.usage.input_tokens
                total_out += msg.usage.output_tokens

                emb = embed_model.encode(vibe, normalize_embeddings=True)
                vec_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"

                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE {table} SET vibe_text = %s, embedding = %s::vector WHERE id = %s",
                        (vibe, vec_str, row["id"]),
                    )
                conn.commit()

                title = row.get("title") or row.get("name") or f"id={row['id']}"
                print(f"  [{i}/{len(rows)}] {title[:55]}")
    finally:
        conn.close()

    cost = (total_in / 1_000_000) * 1.0 + (total_out / 1_000_000) * 5.0
    print(f"\nTokens - in: {total_in:,} · out: {total_out:,} · est. cost: ${cost:.4f}")
    print("Done.")


if __name__ == "__main__":
    main()
