"""
generate_charts.py — cross-domain evaluation charts for the diploma.

Reads results.json (must be in the same folder) and produces:
  • chart_lift.png       — main headline: hybrid vs semantic vs random across 3 metrics @ K=5
  • chart_per_pair.png   — 6 domain-pair breakdown by raw semantic score @ K=5
  • chart_ranking.png    — score gradient by rank K (1, 5, 15): hybrid vs random

ЗАПУСКАТИ:
  cd backend
  python evaluation/cross_domain/generate_charts.py
"""
import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = Path(__file__).parent
data = json.load(open(THIS_DIR / "results.json", encoding="utf-8"))

ALGOS  = ["hybrid", "semantic", "random"]
LABELS = ["Hybrid (наш)", "Semantic only", "Random"]
COLORS = ["#06b6d4", "#a78bfa", "#94a3b8"]   


def chart_lift():
    metrics  = [("score", "Semantic score"),
                ("shared_tags", "Shared tags"),
                ("overlap_rate", "Overlap rate")]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    x = np.arange(len(ALGOS))
    width = 0.6

    for idx, (key, label) in enumerate(metrics):
        ax = axes[idx]
        means = [data["overall"][a][str(5)] [key]["mean"] if isinstance(data["overall"][a].get(5, None), dict) is False
                 else data["overall"][a][5][key]["mean"] for a in ALGOS]
        stds  = [data["overall"][a][5][key]["std"]  for a in ALGOS]
        bars = ax.bar(x, means, width, yerr=stds, color=COLORS,
                      edgecolor="black", linewidth=0.5, capsize=6)

        for b, m in zip(bars, means):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(stds) + (0.02 if key != "shared_tags" else 0.05),
                    f"{m:.3f}" if key != "overlap_rate" else f"{m:.1%}",
                    ha="center", va="bottom", fontsize=11, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=10)
        ax.set_ylabel(label, fontsize=11)
        ax.set_title(label, fontsize=13, fontweight="bold")
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.set_axisbelow(True)
        if key == "score":
            ax.set_ylim(0, 1.0)
        elif key == "overlap_rate":
            ax.set_ylim(0, 1.0)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        else:
            ax.set_ylim(0, max(means) * 1.4 + max(stds) * 2)

    fig.suptitle(
        f"Cross-domain evaluation @ K=5  ({data['metadata']['n_seeds']} seeds × "
        f"{data['metadata']['n_anchors_per_domain']} anchors/domain × 6 pairs, mean ± std)",
        fontsize=14, fontweight="bold", y=1.02,
    )
    plt.tight_layout()
    out = THIS_DIR / "chart_lift.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ {out.name}")


def chart_per_pair():
    pair_keys = list(data["per_pair"].keys())
    pair_labels = [p.replace("->", "→") for p in pair_keys]

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(pair_keys))
    width = 0.27

    for i, algo in enumerate(ALGOS):
        means = [data["per_pair"][p][algo][5]["score"]["mean"] for p in pair_keys]
        stds  = [data["per_pair"][p][algo][5]["score"]["std"]  for p in pair_keys]
        bars = ax.bar(x + (i - 1) * width, means, width, yerr=stds,
                      label=LABELS[i], color=COLORS[i],
                      edgecolor="black", linewidth=0.5, capsize=4)
        for b, m in zip(bars, means):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015,
                    f"{m:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(pair_labels, fontsize=11)
    ax.set_ylabel("Semantic score (raw cosine)", fontsize=11)
    ax.set_title(
        "Cross-domain score by direction pair @ K=5",
        fontsize=14, fontweight="bold",
    )
    ax.set_ylim(0, 1.0)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=11, framealpha=0.95)

    plt.tight_layout()
    out = THIS_DIR / "chart_per_pair.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ {out.name}")


def chart_ranking():
    ks = data["metadata"]["k_values"]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    hyb_means = [data["overall"]["hybrid"][k]["score"]["mean"] for k in ks]
    hyb_stds  = [data["overall"]["hybrid"][k]["score"]["std"]  for k in ks]
    sem_means = [data["overall"]["semantic"][k]["score"]["mean"] for k in ks]
    sem_stds  = [data["overall"]["semantic"][k]["score"]["std"]  for k in ks]
    rnd_means = [data["overall"]["random"][k]["score"]["mean"] for k in ks]
    rnd_stds  = [data["overall"]["random"][k]["score"]["std"]  for k in ks]

    ax.errorbar(ks, hyb_means, yerr=hyb_stds, marker="o", markersize=9, linewidth=2.5,
                color=COLORS[0], label="Hybrid (наш)", capsize=6)
    ax.errorbar(ks, sem_means, yerr=sem_stds, marker="s", markersize=8, linewidth=2,
                color=COLORS[1], label="Semantic only", capsize=6, linestyle="--")
    ax.errorbar(ks, rnd_means, yerr=rnd_stds, marker="^", markersize=8, linewidth=2,
                color=COLORS[2], label="Random", capsize=6, linestyle=":")

    for ks_, ms, color in [(ks, hyb_means, COLORS[0]), (ks, sem_means, COLORS[1]), (ks, rnd_means, COLORS[2])]:
        for k, m in zip(ks_, ms):
            ax.annotate(f"{m:.3f}", (k, m), textcoords="offset points", xytext=(8, 8), fontsize=9, color=color)

    ax.set_xticks(ks)
    ax.set_xlabel("Rank cutoff K", fontsize=11)
    ax.set_ylabel("Semantic score (raw cosine)", fontsize=11)
    ax.set_title(
        "Ranking discrimination — score gradient by rank K",
        fontsize=14, fontweight="bold",
    )
    ax.set_ylim(0, 1.0)
    ax.grid(alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", fontsize=11, framealpha=0.95)

    plt.tight_layout()
    out = THIS_DIR / "chart_ranking.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ {out.name}")


if __name__ == "__main__":
    chart_lift()
    chart_per_pair()
    chart_ranking()
    print("\nDone. PNG-файли готові для вставки у диплом.")
