"""
evaluate_recommendations.py — Експериментальна оцінка системи рекомендацій.

═══════════════════════════════════════════════════════════════════════════════
ЩО ЦЕ:
  Створює 15 синтетичних тестових юзерів (5 на кожен з 3 доменів) і рахує
  метрики IR для трьох алгоритмів:
    • TF-IDF cosine     — наш content-based recommender
    • Popularity        — baseline: топ-K за рейтингом/слухачами
    • Random            — baseline: випадкові K айтемів

  Метрики: Precision@K, Recall@K, MRR@K (mean reciprocal rank).

НАВІЩО:
  Для глави диплому "Експериментальна оцінка". Дає конкретні числа +
  довірчі інтервали (стабільність), а не точкову оцінку.

МЕТОДОЛОГІЯ:
  Synthetic user profile testing з multi-seed повтором:
    1. Для кожного жанру G формуємо профіль:
       - SAMPLE_SIZE випадкових айтемів з жанром G = training set (лайки)
       - Решта айтемів з жанром G = ground truth
    2. Прогоняємо алгоритм, отримуємо топ-K
    3. Рахуємо: Precision@K, Recall@K, MRR@K
    4. Повторюємо з N різних random seeds → mean ± std deviation
    5. Усереднюємо по 5 personas на домен, по 15 загалом

МЕТРИКИ — формули і інтерпретація:
  Precision@K = |top_K ∩ ground_truth| / K
       → "Зі K показаних — скільки правильно?"
  Recall@K    = |top_K ∩ ground_truth| / |ground_truth|
       → "Зі всіх можливих правильних — скільки знайшли?"
  MRR@K       = mean(1 / rank_of_first_hit), 0 якщо немає влучень у top_K
       → "Як високо в списку перший влучний?" (1.0 = перший item, 0.5 = другий)

ЯК ЗАПУСКАТИ:
  cd backend
  python evaluation/single_domain/evaluate.py

ВИВІД:
  • stdout       — таблиці per-seed, per-domain, overall з mean ± std
  • JSON-файл    — evaluation/single_domain/results.json (для диплому)
"""
import os
import sys
import json
import math
import random
from collections import defaultdict
from pathlib import Path

# ── Setup ─────────────────────────────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

import psycopg2
import psycopg2.extras

from database import cached_query, _cache
from routers.recommendations import _build_recommendations


# ── Config ────────────────────────────────────────────────────────────────────
SEEDS = [42, 100, 200, 300, 400]    # 5 різних посівів для оцінки стабільності
SAMPLE_SIZE = 7                      # лайків на тестового юзера (7 = sweet spot:
                                     # Hip-Hop має 12 треків → 12-7=5 GT, інші більше)
K_VALUES = [5, 10]                   # рахуємо @K для цих K
FINAL_SEED = 42                      # яким seed залишити DB-стан після всього

# (firebase_uid, display_name, item_type, genre_filter)
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

DOMAIN_CONFIG = {
    "game":  {"tag_fields": ["genres", "tags"],     "min_df": 1, "table": "games"},
    "movie": {"tag_fields": ["genres", "keywords"], "min_df": 2, "table": "movies"},
    "track": {"tag_fields": ["genres", "tags"],     "min_df": 1, "table": "tracks"},
}

ALGOS = [
    ("tfidf", "TF-IDF (ours)"),
    ("pop",   "Popularity"),
    ("rand",  "Random"),
]


# ── DB helpers ────────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def create_test_users_and_likes(seed: int) -> dict:
    """
    (Пере)створює 15 синтетичних юзерів і їх focused likes для заданого seed.
    Повертає profiles dict: uid → {item_type, genre, training, ground_truth}.
    """
    rng = random.Random(seed)
    conn = get_conn()
    cur = conn.cursor()

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
                f"замало (потрібно ≥{SAMPLE_SIZE + 5})."
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
def precision_at_k(rec_ids: list, ground_truth: set, k: int) -> float:
    """|top_K ∩ GT| / K"""
    top = rec_ids[:k]
    hits = sum(1 for x in top if x in ground_truth)
    return hits / k if k > 0 else 0.0


def recall_at_k(rec_ids: list, ground_truth: set, k: int) -> float:
    """|top_K ∩ GT| / |GT|"""
    top = rec_ids[:k]
    hits = sum(1 for x in top if x in ground_truth)
    return hits / len(ground_truth) if ground_truth else 0.0


def mrr_at_k(rec_ids: list, ground_truth: set, k: int) -> float:
    """
    Reciprocal Rank @K: 1/rank першого влучного у top_K, 0 якщо немає влучень.
    Високий MRR = релевантне на ранніх позиціях.
    """
    for i, item_id in enumerate(rec_ids[:k]):
        if item_id in ground_truth:
            return 1.0 / (i + 1)
    return 0.0


# ── Algorithms (return item_ids sorted by score, training excluded) ──────────
def rec_tfidf(uid: str, item_type: str, items: list) -> list[int]:
    cfg = DOMAIN_CONFIG[item_type]
    recs = _build_recommendations(uid, item_type, items, cfg["tag_fields"], cfg["min_df"])
    return [r["id"] for r in recs]


def rec_popularity(items: list, training_set: set, item_type: str) -> list[int]:
    if item_type == "track":
        key = lambda x: -(x.get("listeners") or 0)
    else:
        key = lambda x: -(x.get("rating") or 0)
    pool = [i for i in items if i["id"] not in training_set]
    return [i["id"] for i in sorted(pool, key=key)]


def rec_random(items: list, training_set: set, seed: int) -> list[int]:
    rng = random.Random(seed)
    pool = [i for i in items if i["id"] not in training_set]
    rng.shuffle(pool)
    return [i["id"] for i in pool]


# ── Single-seed evaluation ────────────────────────────────────────────────────
def evaluate_once(profiles: dict, seed: int) -> list[dict]:
    """Один прогін: 15 personas × 3 algo × (P@K, R@K, MRR@K)."""
    _cache.clear()
    items_by_type = {
        it: cached_query(cfg["table"], f"SELECT * FROM {cfg['table']}")
        for it, cfg in DOMAIN_CONFIG.items()
    }

    results = []
    for uid, p in profiles.items():
        it = p["item_type"]
        items = items_by_type[it]
        train_set = set(p["training"])
        gt = p["ground_truth"]

        recs = {
            "tfidf": rec_tfidf(uid, it, items),
            "pop":   rec_popularity(items, train_set, it),
            "rand":  rec_random(items, train_set, seed),
        }

        row = {"uid": uid, "name": p["name"], "domain": it, "genre": p["genre"],
               "training_size": len(p["training"]), "gt_size": len(gt)}
        for algo, rec_ids in recs.items():
            for k in K_VALUES:
                row[f"{algo}_p@{k}"]   = round(precision_at_k(rec_ids, gt, k), 4)
                row[f"{algo}_r@{k}"]   = round(recall_at_k(rec_ids, gt, k),    4)
                row[f"{algo}_mrr@{k}"] = round(mrr_at_k(rec_ids, gt, k),       4)
        results.append(row)

    return results


# ── Multi-seed aggregation ────────────────────────────────────────────────────
def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return m, math.sqrt(var)


def aggregate_overall(all_runs: list[list[dict]]) -> dict:
    """
    На вхід: список з SEEDS прогонів, кожен — list[15 рядків].
    На виході: для кожного algo × metric → (mean, std) обчислені:
        - спочатку усереднюємо по 15 personas у межах одного seed (= overall score for that run)
        - потім mean ± std по SEEDS
    """
    out = {}
    for algo, _ in ALGOS:
        out[algo] = {}
        for k in K_VALUES:
            for metric in ("p", "r", "mrr"):
                key = f"{algo}_{metric}@{k}"
                run_means = [
                    sum(row[key] for row in run) / len(run)
                    for run in all_runs
                ]
                m, s = mean_std(run_means)
                out[algo][f"{metric}@{k}"] = {"mean": round(m, 4), "std": round(s, 4)}
    return out


def aggregate_per_domain(all_runs: list[list[dict]]) -> dict:
    """Mean ± std по seeds, для кожного домену окремо."""
    out = defaultdict(dict)
    for domain in ("game", "movie", "track"):
        for algo, _ in ALGOS:
            out[domain][algo] = {}
            for k in K_VALUES:
                for metric in ("p", "r", "mrr"):
                    key = f"{algo}_{metric}@{k}"
                    run_means = [
                        sum(row[key] for row in run if row["domain"] == domain)
                        / sum(1 for row in run if row["domain"] == domain)
                        for run in all_runs
                    ]
                    m, s = mean_std(run_means)
                    out[domain][algo][f"{metric}@{k}"] = {"mean": round(m, 4), "std": round(s, 4)}
    return dict(out)


# ── Reporting ─────────────────────────────────────────────────────────────────
DOMAIN_TITLE = {"game": "GAMES", "movie": "MOVIES", "track": "TRACKS"}


def fmt(m, s):
    """Format mean ± std with proper alignment."""
    return f"{m:.3f} ± {s:.3f}"


def print_report(overall: dict, per_domain: dict, seeds: list[int], sample_size: int):
    sep = "═" * 92
    print(f"\n{sep}")
    print(f"  EXPERIMENT — mean ± std deviation across {len(seeds)} seeds")
    print(f"  Personas: {len(PERSONAS)}  |  Training size: {sample_size}  |  Seeds: {seeds}")
    print(sep)

    # Per-domain @10
    for domain in ("game", "movie", "track"):
        print(f"\n── {DOMAIN_TITLE[domain]} @10 " + "─" * (80 - len(DOMAIN_TITLE[domain])))
        print(f"  {'Algorithm':20s}  {'Precision@10':>15}  {'Recall@10':>15}  {'MRR@10':>15}")
        print(f"  {'-'*20}  {'-'*15}  {'-'*15}  {'-'*15}")
        for algo, label in ALGOS:
            d = per_domain[domain][algo]
            print(
                f"  {label:20s}  "
                f"{fmt(d['p@10']['mean'], d['p@10']['std']):>15}  "
                f"{fmt(d['r@10']['mean'], d['r@10']['std']):>15}  "
                f"{fmt(d['mrr@10']['mean'], d['mrr@10']['std']):>15}"
            )

    # Overall @5 і @10
    print(f"\n── OVERALL (averaged over 15 personas × {len(seeds)} seeds) " + "─" * 30)
    print(f"  {'Algorithm':20s}  {'P@5':>13}  {'R@5':>13}  {'MRR@5':>13}  {'P@10':>13}  {'R@10':>13}  {'MRR@10':>13}")
    print(f"  {'-'*20}  {'-'*13}  {'-'*13}  {'-'*13}  {'-'*13}  {'-'*13}  {'-'*13}")
    for algo, label in ALGOS:
        d = overall[algo]
        print(
            f"  {label:20s}  "
            f"{fmt(d['p@5']['mean'], d['p@5']['std']):>13}  "
            f"{fmt(d['r@5']['mean'], d['r@5']['std']):>13}  "
            f"{fmt(d['mrr@5']['mean'], d['mrr@5']['std']):>13}  "
            f"{fmt(d['p@10']['mean'], d['p@10']['std']):>13}  "
            f"{fmt(d['r@10']['mean'], d['r@10']['std']):>13}  "
            f"{fmt(d['mrr@10']['mean'], d['mrr@10']['std']):>13}"
        )

    # Lift над baselines
    print(f"\n── LIFT @10 (наш TF-IDF / baseline)" + " " + "─" * 50)
    tfidf = overall["tfidf"]
    pop   = overall["pop"]
    rand  = overall["rand"]
    for metric in ("p@10", "r@10", "mrr@10"):
        tf = tfidf[metric]["mean"]
        pop_lift  = tf / pop[metric]["mean"]  if pop[metric]["mean"]  > 0 else float("inf")
        rand_lift = tf / rand[metric]["mean"] if rand[metric]["mean"] > 0 else float("inf")
        print(f"  {metric.upper():8s}  TF-IDF = {tf:.3f}  |  vs Popularity: {pop_lift:5.2f}×  |  vs Random: {rand_lift:5.2f}×")
    print()


def save_json(all_runs: list[list[dict]], overall: dict, per_domain: dict,
              path: Path, seeds: list[int], sample_size: int):
    output = {
        "metadata": {
            "personas_count": len(PERSONAS),
            "sample_size_per_persona": sample_size,
            "k_values": K_VALUES,
            "seeds": seeds,
            "n_runs": len(seeds),
            "methodology": (
                "Multi-seed synthetic user profile testing. Per run we sample "
                f"{sample_size} likes from a target genre for each of {len(PERSONAS)} synthetic users, "
                "measure Precision@K, Recall@K, MRR@K against ground truth (remaining items of that genre), "
                f"then aggregate mean ± std across {len(seeds)} independent random seeds."
            ),
        },
        "overall": overall,
        "per_domain": per_domain,
        "raw_runs": [
            {"seed": s, "results": run}
            for s, run in zip(seeds, all_runs)
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Прогоняємо evaluation з {len(SEEDS)} різними seeds, SAMPLE_SIZE={SAMPLE_SIZE}...\n")

    all_runs = []
    for seed in SEEDS:
        print(f"  Seed {seed} — створюємо юзерів і evaluat'имо...")
        profiles = create_test_users_and_likes(seed)
        run_results = evaluate_once(profiles, seed)
        all_runs.append(run_results)
        # Quick sanity print
        avg_tf = sum(r["tfidf_p@10"] for r in run_results) / len(run_results)
        print(f"    → TF-IDF Precision@10 = {avg_tf:.3f}")

    # Залишаємо DB у відомому стані (seed=FINAL_SEED)
    if SEEDS[-1] != FINAL_SEED:
        print(f"\n  Відновлюємо DB-стан з seed={FINAL_SEED}...")
        create_test_users_and_likes(FINAL_SEED)

    # Aggregate
    overall    = aggregate_overall(all_runs)
    per_domain = aggregate_per_domain(all_runs)

    # Report
    print_report(overall, per_domain, SEEDS, SAMPLE_SIZE)

    # Persist
    out_path = Path(__file__).parent / "results.json"
    save_json(all_runs, overall, per_domain, out_path, SEEDS, SAMPLE_SIZE)
    print(f"✓ Результати (всі {len(SEEDS)} прогонів + agg) → {out_path}")


if __name__ == "__main__":
    main()
