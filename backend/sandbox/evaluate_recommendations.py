"""
evaluate_recommendations.py — Експериментальна оцінка системи рекомендацій.

═══════════════════════════════════════════════════════════════════════════════
ЩО ЦЕ:
  Створює 15 синтетичних тестових юзерів (5 на кожен з 3 доменів) і рахує
  Precision@K та Recall@K для трьох алгоритмів:
    • TF-IDF cosine     — наш content-based recommender
    • Popularity        — baseline: топ-K за рейтингом/слухачами
    • Random            — baseline: випадкові K айтемів

НАВІЩО:
  Для глави диплому "Експериментальна оцінка". Дає конкретні числа замість
  експертної оцінки топ-N. Стандартна методологія IR для content-based систем.

МЕТОДОЛОГІЯ (synthetic user profile testing):
  Для кожного жанру G обираємо синтетичний "fan" профіль:
    1. Випадковим чином беремо 5 айтемів з жанром G — TRAINING SET (лайки)
    2. Решта айтемів з жанром G — GROUND TRUTH (що алгоритм має знайти)
    3. Запускаємо алгоритм, отримуємо топ-K рекомендацій
    4. Рахуємо:
         Precision@K = |top_K ∩ ground_truth| / K
         Recall@K    = |top_K ∩ ground_truth| / |ground_truth|
    5. Усереднюємо по 5 personas на домен → per-domain
    6. Усереднюємо по всіх 15 → overall

ЯК ЗАПУСКАТИ:
  cd backend
  python sandbox/evaluate_recommendations.py

ДЕТЕРМІНОВАНІСТЬ:
  random.seed(42) — результати відтворювані. Один і той самий запуск дає однакові
  тестові лайки і однакові метрики. Для диплому це важливо.

ВИВІД:
  • stdout       — таблиці per-domain + overall
  • JSON-файл    — sandbox/evaluation_results.json
"""
import os
import sys
import json
import random
from collections import defaultdict
from pathlib import Path

# ── Setup ─────────────────────────────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parents[1]))  # so we can import database, routers

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

import psycopg2
import psycopg2.extras

from database import cached_query, _cache
from routers.recommendations import _build_recommendations


# ── Config ────────────────────────────────────────────────────────────────────
SEED = 42
SAMPLE_SIZE = 5         # лайків на тестового юзера (training set)
K_VALUES = [5, 10]      # рахуємо Precision@K і Recall@K для цих K

# (firebase_uid, display_name, item_type, genre_filter)
# 5 personas на домен × 3 домени = 15. Жанри підібрані так щоб у кожному було
# щонайменше 10-12 айтемів у БД (для статистично значущого ground truth).
PERSONAS = [
    # GAMES
    ("test_rpg_fan",        "Test: RPG Fan",        "game",  "RPG"),
    ("test_shooter_fan",    "Test: Shooter Fan",    "game",  "Shooter"),
    ("test_strategy_fan",   "Test: Strategy Fan",   "game",  "Strategy"),
    ("test_indie_gamer",    "Test: Indie Gamer",    "game",  "Indie"),
    ("test_simulation_fan", "Test: Simulation Fan", "game",  "Simulation"),
    # MOVIES
    ("test_drama_fan",      "Test: Drama Fan",      "movie", "Drama"),
    ("test_comedy_fan",     "Test: Comedy Fan",     "movie", "Comedy"),
    ("test_scifi_fan",      "Test: Sci-Fi Fan",     "movie", "Sci-Fi"),
    ("test_animation_fan",  "Test: Animation Fan",  "movie", "Animation"),
    ("test_crime_fan",      "Test: Crime Fan",      "movie", "Crime"),
    # TRACKS
    ("test_metal_fan",      "Test: Metal Fan",      "track", "Metal"),
    ("test_hiphop_fan",     "Test: Hip-Hop Fan",    "track", "Hip-Hop"),
    ("test_electronic_fan", "Test: Electronic Fan", "track", "Electronic"),
    ("test_soulblues_fan",  "Test: Soul/Blues Fan", "track", "Soul/Blues"),
    ("test_pop_fan",        "Test: Pop Fan",        "track", "Pop"),
]

# Параметри TF-IDF на кожен домен (consistent з routers/recommendations.py)
DOMAIN_CONFIG = {
    "game":  {"tag_fields": ["genres", "tags"],     "min_df": 1, "table": "games"},
    "movie": {"tag_fields": ["genres", "keywords"], "min_df": 2, "table": "movies"},
    "track": {"tag_fields": ["genres", "tags"],     "min_df": 1, "table": "tracks"},
}


# ── DB helpers ────────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def create_test_users_and_likes() -> dict:
    """
    Створює (або перестворює) 15 синтетичних юзерів з focused likes.
    Повертає dict: uid → {item_type, genre, training (list[int]), ground_truth (set[int])}
    """
    rng = random.Random(SEED)
    conn = get_conn()
    cur = conn.cursor()

    # Очистити попередні тести
    test_uids = [p[0] for p in PERSONAS]
    cur.execute("DELETE FROM likes WHERE user_uid = ANY(%s)", (test_uids,))
    cur.execute("DELETE FROM users WHERE firebase_uid = ANY(%s)", (test_uids,))

    profiles: dict = {}
    for uid, name, item_type, genre in PERSONAS:
        cur.execute(
            "INSERT INTO users (firebase_uid, email, name) VALUES (%s, %s, %s)",
            (uid, f"{uid}@test.local", name),
        )

        table = DOMAIN_CONFIG[item_type]["table"]
        cur.execute(f"SELECT id FROM {table} WHERE %s = ANY(genres)", (genre,))
        all_ids = [r["id"] for r in cur.fetchall()]

        if len(all_ids) < SAMPLE_SIZE + 5:
            raise RuntimeError(
                f"Жанр '{genre}' має лише {len(all_ids)} айтемів у '{table}' — "
                f"замало для тесту (потрібно ≥{SAMPLE_SIZE + 5}). "
                f"Зміни PERSONAS на більш представлений жанр."
            )

        rng.shuffle(all_ids)
        training = all_ids[:SAMPLE_SIZE]
        ground_truth = set(all_ids[SAMPLE_SIZE:])

        for item_id in training:
            cur.execute(
                "INSERT INTO likes (user_uid, item_type, item_id) VALUES (%s, %s, %s)",
                (uid, item_type, item_id),
            )

        profiles[uid] = {
            "name": name,
            "item_type": item_type,
            "genre": genre,
            "training": training,
            "ground_truth": ground_truth,
        }

    conn.commit()
    cur.close()
    conn.close()
    return profiles


# ── Metrics ───────────────────────────────────────────────────────────────────
def precision_recall_at_k(rec_ids: list, ground_truth: set, k: int) -> tuple[float, float]:
    """Стандартні IR-метрики. Повертає (precision, recall) у [0, 1]."""
    top = rec_ids[:k]
    hits = sum(1 for x in top if x in ground_truth)
    precision = hits / k if k > 0 else 0.0
    recall = hits / len(ground_truth) if ground_truth else 0.0
    return precision, recall


# ── Algorithms (returns list of item_ids sorted by score, training excluded) ──
def rec_tfidf(uid: str, item_type: str, items: list) -> list[int]:
    """Наш TF-IDF cosine recommender — використовує production-функцію."""
    cfg = DOMAIN_CONFIG[item_type]
    recs = _build_recommendations(uid, item_type, items, cfg["tag_fields"], cfg["min_df"])
    return [r["id"] for r in recs]


def rec_popularity(items: list, training_set: set, item_type: str) -> list[int]:
    """Baseline: топ за popularity (rating для game/movie, listeners для track)."""
    if item_type == "track":
        key = lambda x: -(x.get("listeners") or 0)
    else:
        key = lambda x: -(x.get("rating") or 0)
    pool = [i for i in items if i["id"] not in training_set]
    return [i["id"] for i in sorted(pool, key=key)]


def rec_random(items: list, training_set: set) -> list[int]:
    """Baseline: випадковий порядок (seed для відтворюваності)."""
    rng = random.Random(SEED)
    pool = [i for i in items if i["id"] not in training_set]
    rng.shuffle(pool)
    return [i["id"] for i in pool]


# ── Evaluation pipeline ───────────────────────────────────────────────────────
def evaluate(profiles: dict) -> list[dict]:
    """Прогоняє всі 3 алгоритми на всіх 15 personas, повертає список рядків."""
    _cache.clear()  # backend кешує recs — скидаємо для чистого замiру
    items_by_type = {
        it: cached_query(cfg["table"], f"SELECT * FROM {cfg['table']}")
        for it, cfg in DOMAIN_CONFIG.items()
    }

    results = []
    for uid, p in profiles.items():
        it = p["item_type"]
        items = items_by_type[it]
        training_set = set(p["training"])
        gt = p["ground_truth"]

        recs_by_algo = {
            "tfidf": rec_tfidf(uid, it, items),
            "pop":   rec_popularity(items, training_set, it),
            "rand":  rec_random(items, training_set),
        }

        row = {
            "uid": uid, "name": p["name"], "domain": it, "genre": p["genre"],
            "training_size": len(p["training"]), "gt_size": len(gt),
        }
        for algo, rec_ids in recs_by_algo.items():
            for k in K_VALUES:
                p_, r_ = precision_recall_at_k(rec_ids, gt, k)
                row[f"{algo}_p@{k}"] = round(p_, 3)
                row[f"{algo}_r@{k}"] = round(r_, 3)
        results.append(row)

    return results


# ── Reporting ─────────────────────────────────────────────────────────────────
DOMAIN_TITLE = {"game": "GAMES", "movie": "MOVIES", "track": "TRACKS"}


def print_report(results: list[dict]):
    by_domain = defaultdict(list)
    for r in results:
        by_domain[r["domain"]].append(r)

    sep = "═" * 90
    print(f"\n{sep}")
    print(f"  EXPERIMENT RESULTS — Precision@10 / Recall@10")
    print(f"  Personas: {len(results)}  |  Training size per persona: {SAMPLE_SIZE}  |  Seed: {SEED}")
    print(sep)

    for domain in ["game", "movie", "track"]:
        rows = by_domain[domain]
        if not rows:
            continue
        print(f"\n── {DOMAIN_TITLE[domain]} " + "─" * (88 - len(DOMAIN_TITLE[domain])))
        print(f"  {'Persona':25s}  {'GT':>3}  {'TF-IDF':>15}  {'Popularity':>15}  {'Random':>15}")
        print(f"  {'-'*25}  {'-'*3}  {'-'*15}  {'-'*15}  {'-'*15}")
        for r in rows:
            print(
                f"  {r['name']:25s}  {r['gt_size']:>3}  "
                f"P={r['tfidf_p@10']:.2f} R={r['tfidf_r@10']:.2f}  "
                f"P={r['pop_p@10']:.2f} R={r['pop_r@10']:.2f}  "
                f"P={r['rand_p@10']:.2f} R={r['rand_r@10']:.2f}"
            )
        # Per-domain averages
        n = len(rows)
        print(f"  {'-'*25}  {'-'*3}  {'-'*15}  {'-'*15}  {'-'*15}")
        for algo, label in [("tfidf", "AVG TF-IDF"), ("pop", "AVG Popularity"), ("rand", "AVG Random")]:
            ap = sum(r[f"{algo}_p@10"] for r in rows) / n
            ar = sum(r[f"{algo}_r@10"] for r in rows) / n
            print(f"  {label:25s}       P={ap:.2f} R={ar:.2f}")

    # Overall summary
    print(f"\n── OVERALL (averaged over all {len(results)} personas) " + "─" * 30)
    print(f"  {'Algorithm':20s}  {'Precision@5':>11}  {'Recall@5':>9}  {'Precision@10':>12}  {'Recall@10':>10}")
    print(f"  {'-'*20}  {'-'*11}  {'-'*9}  {'-'*12}  {'-'*10}")
    for algo, label in [("tfidf", "TF-IDF (ours)"), ("pop", "Popularity"), ("rand", "Random")]:
        avg = {
            f"p@{k}": sum(r[f"{algo}_p@{k}"] for r in results) / len(results)
            for k in K_VALUES
        }
        avg |= {
            f"r@{k}": sum(r[f"{algo}_r@{k}"] for r in results) / len(results)
            for k in K_VALUES
        }
        print(
            f"  {label:20s}  {avg['p@5']:>11.3f}  {avg['r@5']:>9.3f}  "
            f"{avg['p@10']:>12.3f}  {avg['r@10']:>10.3f}"
        )
    print()


def save_json(results: list[dict], path: Path):
    overall = {}
    for algo in ["tfidf", "pop", "rand"]:
        overall[algo] = {}
        for k in K_VALUES:
            overall[algo][f"precision@{k}"] = round(
                sum(r[f"{algo}_p@{k}"] for r in results) / len(results), 4
            )
            overall[algo][f"recall@{k}"] = round(
                sum(r[f"{algo}_r@{k}"] for r in results) / len(results), 4
            )

    per_domain = defaultdict(dict)
    by_domain = defaultdict(list)
    for r in results:
        by_domain[r["domain"]].append(r)
    for dom, rows in by_domain.items():
        n = len(rows)
        for algo in ["tfidf", "pop", "rand"]:
            per_domain[dom][algo] = {}
            for k in K_VALUES:
                per_domain[dom][algo][f"precision@{k}"] = round(
                    sum(r[f"{algo}_p@{k}"] for r in rows) / n, 4
                )
                per_domain[dom][algo][f"recall@{k}"] = round(
                    sum(r[f"{algo}_r@{k}"] for r in rows) / n, 4
                )

    output = {
        "metadata": {
            "personas_count": len(results),
            "sample_size_per_persona": SAMPLE_SIZE,
            "k_values": K_VALUES,
            "seed": SEED,
            "methodology": "Synthetic user profile testing on focused genre preferences.",
        },
        "overall_averages": overall,
        "per_domain_averages": dict(per_domain),
        "per_persona_results": results,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Step 1 — створюємо тестових юзерів і лайки в БД...")
    profiles = create_test_users_and_likes()
    print(f"  ✓ {len(profiles)} тестових юзерів готові")

    print("\nStep 2 — прогоняємо TF-IDF / Popularity / Random на всіх personas...")
    results = evaluate(profiles)
    print(f"  ✓ {len(results)} замірів зроблено")

    print_report(results)

    out_path = Path(__file__).parent / "evaluation_results.json"
    save_json(results, out_path)
    print(f"✓ Деталі (для диплому) збережено: {out_path}")


if __name__ == "__main__":
    main()
