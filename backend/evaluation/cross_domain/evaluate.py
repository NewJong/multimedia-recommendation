import os
import sys
import json
import math
import random
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

import psycopg2
import psycopg2.extras

from routers.cross import (
    TABLE, TAG_FIELDS, SHARED_TAG_BONUS, MAX_TAG_BONUS, POOL_MULT,
    _collect_tags,
)


SEEDS = [42, 100, 200, 300, 400]
N_ANCHORS_PER_DOMAIN = 25
K_VALUES = [1, 5, 15]

DOMAIN_PAIRS = [
    ("track", "movie"), ("track", "game"),
    ("movie", "track"), ("movie", "game"),
    ("game",  "track"), ("game",  "movie"),
]

DOMAIN_TITLE = {"track": "TRACKS", "movie": "MOVIES", "game": "GAMES"}


def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)


def fetch_items(cur, item_type: str) -> list[dict]:
    cur.execute(f"SELECT * FROM {TABLE[item_type]} WHERE embedding IS NOT NULL")
    return [dict(r) for r in cur.fetchall()]


def cross_rec_hybrid(cur, anchor: dict, anchor_type: str, other_type: str, k: int):
    other_table = TABLE[other_type]
    cur.execute(f"""
        SELECT *, 1 - (embedding <=> %s::vector) AS _sem
        FROM {other_table}
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (anchor["embedding"], anchor["embedding"], k * POOL_MULT))
    pool = [dict(r) for r in cur.fetchall()]

    anchor_tags = _collect_tags(anchor, anchor_type)
    scored = []
    for r in pool:
        sem = float(r["_sem"])
        r_tags = _collect_tags(r, other_type)
        shared = anchor_tags & r_tags
        bonus = min(MAX_TAG_BONUS, len(shared) * SHARED_TAG_BONUS)
        hybrid = min(1.0, sem + bonus)
        scored.append((r, hybrid, sem, shared))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


def cross_rec_semantic_only(cur, anchor: dict, anchor_type: str, other_type: str, k: int):
    other_table = TABLE[other_type]
    cur.execute(f"""
        SELECT *, 1 - (embedding <=> %s::vector) AS _sem
        FROM {other_table}
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (anchor["embedding"], anchor["embedding"], k))
    anchor_tags = _collect_tags(anchor, anchor_type)
    out = []
    for r in cur.fetchall():
        row = dict(r)
        sem = float(row["_sem"])
        shared = anchor_tags & _collect_tags(row, other_type)
        out.append((row, sem, sem, shared))
    return out


def cross_rec_random(cur, anchor: dict, anchor_type: str, other_type: str,
                     other_pool: list[dict], k: int, rng: random.Random):
    sampled = rng.sample(other_pool, min(k, len(other_pool)))
    sampled_ids = [r["id"] for r in sampled]

    cur.execute(f"""
        SELECT id, 1 - (embedding <=> %s::vector) AS _sem
        FROM {TABLE[other_type]}
        WHERE id = ANY(%s)
    """, (anchor["embedding"], sampled_ids))
    sem_by_id = {r["id"]: float(r["_sem"]) for r in cur.fetchall()}

    anchor_tags = _collect_tags(anchor, anchor_type)
    out = []
    for r in sampled:
        sem = sem_by_id.get(r["id"], 0.0)
        shared = anchor_tags & _collect_tags(r, other_type)
        out.append((r, sem, sem, shared))
    return out


def avg_score(scored: list, score_idx: int) -> float:
    if not scored: return 0.0
    return sum(s[score_idx] for s in scored) / len(scored)


def avg_shared_tags(scored: list) -> float:
    if not scored: return 0.0
    return sum(len(s[3]) for s in scored) / len(scored)


def fraction_with_overlap(scored: list) -> float:
    if not scored: return 0.0
    return sum(1 for s in scored if len(s[3]) > 0) / len(scored)


def evaluate_once(seed: int, items_by_type: dict[str, list[dict]]) -> dict:
    rng = random.Random(seed)
    conn = get_conn()
    result: dict = {}

    try:
        with conn.cursor() as cur:
            for anchor_type, other_type in DOMAIN_PAIRS:
                anchors = rng.sample(items_by_type[anchor_type], min(N_ANCHORS_PER_DOMAIN, len(items_by_type[anchor_type])))
                other_pool = items_by_type[other_type]

                pair_key = f"{anchor_type}->{other_type}"
                result[pair_key] = {algo: {k: defaultdict(list) for k in K_VALUES} for algo in ("hybrid", "semantic", "random")}

                for anchor in anchors:
                    hybrid_top   = cross_rec_hybrid(cur, anchor, anchor_type, other_type, max(K_VALUES))
                    semantic_top = cross_rec_semantic_only(cur, anchor, anchor_type, other_type, max(K_VALUES))
                    random_top   = cross_rec_random(cur, anchor, anchor_type, other_type, other_pool, max(K_VALUES), rng)

                    for k in K_VALUES:
                        for algo_name, top in (("hybrid", hybrid_top), ("semantic", semantic_top), ("random", random_top)):
                            slice_ = top[:k]
                            result[pair_key][algo_name][k]["score"].append(avg_score(slice_, 2))
                            result[pair_key][algo_name][k]["hybrid_score"].append(avg_score(slice_, 1))
                            result[pair_key][algo_name][k]["shared_tags"].append(avg_shared_tags(slice_))
                            result[pair_key][algo_name][k]["overlap_rate"].append(fraction_with_overlap(slice_))
    finally:
        conn.close()
    return result


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values: return 0.0, 0.0
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return m, math.sqrt(var)


def aggregate(all_runs: list[dict]) -> dict:
    metrics = ("score", "hybrid_score", "shared_tags", "overlap_rate")
    out: dict = {}
    for pair_key in all_runs[0].keys():
        out[pair_key] = {}
        for algo in ("hybrid", "semantic", "random"):
            out[pair_key][algo] = {}
            for k in K_VALUES:
                out[pair_key][algo][str(k)] = {}
                for metric in metrics:
                    per_seed_means = [
                        sum(run[pair_key][algo][k][metric]) / len(run[pair_key][algo][k][metric])
                        for run in all_runs
                    ]
                    m, s = mean_std(per_seed_means)
                    out[pair_key][algo][str(k)][metric] = {"mean": round(m, 4), "std": round(s, 4)}
    return out


def aggregate_overall(per_pair: dict) -> dict:
    metrics = ("score", "hybrid_score", "shared_tags", "overlap_rate")
    out: dict = {}
    for algo in ("hybrid", "semantic", "random"):
        out[algo] = {}
        for k in K_VALUES:
            out[algo][str(k)] = {}
            for metric in metrics:
                vals = [per_pair[p][algo][str(k)][metric]["mean"] for p in per_pair]
                stds = [per_pair[p][algo][str(k)][metric]["std"]  for p in per_pair]
                m = sum(vals) / len(vals)
                s = sum(stds) / len(stds)
                out[algo][str(k)][metric] = {"mean": round(m, 4), "std": round(s, 4)}
    return out

def fmt(m, s): return f"{m:.3f} ± {s:.3f}"


def print_report(per_pair: dict, overall: dict, n_seeds: int):
    sep = "=" * 102
    print(f"\n{sep}")
    print(f"  CROSS-DOMAIN EVALUATION — mean ± std across {n_seeds} seeds, "
          f"{N_ANCHORS_PER_DOMAIN} anchors/domain")
    print(sep)

    print(f"\n-- PER-PAIR BREAKDOWN @ K=5 " + "-" * 75)
    print(f"  {'Pair':<22}  {'Algo':<10}  {'sem_score':>13}  {'shared_tags':>13}  {'overlap_rate':>13}")
    print(f"  {'-'*22}  {'-'*10}  {'-'*13}  {'-'*13}  {'-'*13}")
    for pair_key, pair_data in per_pair.items():
        for algo in ("hybrid", "semantic", "random"):
            d = pair_data[algo]["5"]
            label_pair = pair_key.replace("->", " -> ") if algo == "hybrid" else ""
            print(
                f"  {label_pair:<22}  {algo:<10}  "
                f"{fmt(d['score']['mean'], d['score']['std']):>13}  "
                f"{fmt(d['shared_tags']['mean'], d['shared_tags']['std']):>13}  "
                f"{fmt(d['overlap_rate']['mean'], d['overlap_rate']['std']):>13}"
            )
        print()

    print(f"\n-- OVERALL @ K=5 (averaged over 6 domain-pairs x {n_seeds} seeds) " + "-" * 30)
    print(f"  {'Algorithm':<14}  {'sem_score':>14}  {'shared_tags':>14}  {'overlap_rate':>14}")
    print(f"  {'-'*14}  {'-'*14}  {'-'*14}  {'-'*14}")
    for algo in ("hybrid", "semantic", "random"):
        d = overall[algo]["5"]
        print(
            f"  {algo:<14}  "
            f"{fmt(d['score']['mean'], d['score']['std']):>14}  "
            f"{fmt(d['shared_tags']['mean'], d['shared_tags']['std']):>14}  "
            f"{fmt(d['overlap_rate']['mean'], d['overlap_rate']['std']):>14}"
        )

    print(f"\n-- LIFT @ K=5 (Hybrid / Random) " + "-" * 60)
    hyb  = overall["hybrid"]["5"]
    sem  = overall["semantic"]["5"]
    rnd  = overall["random"]["5"]
    print(f"  Semantic score      Hybrid={hyb['score']['mean']:.3f}  vs Random={rnd['score']['mean']:.3f}  -> "
          f"{(hyb['score']['mean'] / rnd['score']['mean']) if rnd['score']['mean'] > 0 else float('inf'):.2f}x lift")
    print(f"  Shared tags         Hybrid={hyb['shared_tags']['mean']:.3f}  vs Random={rnd['shared_tags']['mean']:.3f}  -> "
          f"{(hyb['shared_tags']['mean'] / rnd['shared_tags']['mean']) if rnd['shared_tags']['mean'] > 0 else float('inf'):.2f}x lift")
    print(f"  Overlap rate        Hybrid={hyb['overlap_rate']['mean']:.1%}  vs Random={rnd['overlap_rate']['mean']:.1%}  -> "
          f"{(hyb['overlap_rate']['mean'] / rnd['overlap_rate']['mean']) if rnd['overlap_rate']['mean'] > 0 else float('inf'):.2f}x lift")

    print(f"\n-- HYBRID vs PURE SEMANTIC (tag-bonus contribution) " + "-" * 45)
    print(f"  Semantic score      Hybrid={hyb['score']['mean']:.3f}  vs Sem={sem['score']['mean']:.3f}  -> "
          f"delta={(hyb['score']['mean'] - sem['score']['mean']):.3f}")
    print(f"  Shared tags         Hybrid={hyb['shared_tags']['mean']:.3f}  vs Sem={sem['shared_tags']['mean']:.3f}  -> "
          f"delta={(hyb['shared_tags']['mean'] - sem['shared_tags']['mean']):.3f}")

    print(f"\n-- RANKING DISCRIMINATION (Hybrid semantic-score by rank) " + "-" * 40)
    print(f"  {'K':>4}  {'Mean score':>14}  {'Delta vs Random':>16}")
    for k in K_VALUES:
        h = overall["hybrid"][str(k)]["score"]["mean"]
        r = overall["random"][str(k)]["score"]["mean"]
        print(f"  {k:>4}  {h:>14.4f}  {(h - r):>16.4f}")
    print()


def save_json(per_pair: dict, overall: dict, seeds: list, n_anchors: int, out_path: Path):
    payload = {
        "metadata": {
            "seeds": seeds,
            "n_seeds": len(seeds),
            "n_anchors_per_domain": n_anchors,
            "k_values": K_VALUES,
            "domain_pairs": [f"{a}->{b}" for a, b in DOMAIN_PAIRS],
        },
        "overall": overall,
        "per_pair": per_pair,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    print("Loading items with embeddings...")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            items_by_type = {t: fetch_items(cur, t) for t in TABLE}
    finally:
        conn.close()

    counts = ", ".join(f"{t}={len(v)}" for t, v in items_by_type.items())
    print(f"  -> {counts}")
    if any(len(v) < N_ANCHORS_PER_DOMAIN + 5 for v in items_by_type.values()):
        print(f"  Warning: one domain has < {N_ANCHORS_PER_DOMAIN + 5} items with embedding.")

    print(f"\nRunning evaluation with {len(SEEDS)} seeds, "
          f"{N_ANCHORS_PER_DOMAIN} anchors/domain x 2 other-domains = "
          f"{N_ANCHORS_PER_DOMAIN * 6} pairs per seed...\n")

    all_runs = []
    for seed in SEEDS:
        print(f"  Seed {seed}...", end=" ", flush=True)
        result = evaluate_once(seed, items_by_type)
        all_runs.append(result)
        hyb_means = []
        for pair_key in result:
            vals = result[pair_key]["hybrid"][5]["score"]
            hyb_means.append(sum(vals) / len(vals))
        print(f"hybrid sem@5 = {sum(hyb_means)/len(hyb_means):.3f}")

    per_pair = aggregate(all_runs)
    overall  = aggregate_overall(per_pair)

    print_report(per_pair, overall, len(SEEDS))

    out_path = Path(__file__).parent / "results.json"
    save_json(per_pair, overall, SEEDS, N_ANCHORS_PER_DOMAIN, out_path)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
