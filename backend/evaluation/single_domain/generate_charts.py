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

metrics      = [("p@10", "Precision@10"), ("r@10", "Recall@10"), ("mrr@10", "MRR@10")]
domains      = ["game", "movie", "track"]
domain_labels = ["Ігри", "Фільми", "Треки"]
algos        = ["tfidf", "pop", "rand"]
algo_labels  = ["TF-IDF", "Popularity", "Random"]
colors       = ["#2563eb", "#fb923c", "#94a3b8"]


fig, axes = plt.subplots(1, 3, figsize=(15, 6.0))
x = np.arange(len(domains))
width = 0.26

for ax_idx, (key, label) in enumerate(metrics):
    ax = axes[ax_idx]
    means_per_algo = {}
    stds_per_algo = {}
    for i, algo in enumerate(algos):
        means = [data["per_domain"][d][algo][key]["mean"] for d in domains]
        stds  = [data["per_domain"][d][algo][key]["std"]  for d in domains]
        means_per_algo[algo] = means
        stds_per_algo[algo]  = stds
        bars = ax.bar(
            x + (i - 1) * width, means, width,
            yerr=stds, label=algo_labels[i],
            color=colors[i], capsize=5, edgecolor="black", linewidth=0.5,
        )
        for j, b in enumerate(bars):
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h + stds[j] + 0.02,
                    f"{means[j]:.2f} ±{stds[j]:.2f}",
                    ha="center", va="bottom", fontsize=8)

    tf_means  = means_per_algo["tfidf"]
    tf_stds   = stds_per_algo["tfidf"]
    pop_means = means_per_algo["pop"]
    rand_means = means_per_algo["rand"]
    for j in range(len(domains)):
        if pop_means[j] > 0 and rand_means[j] > 0:
            lp = tf_means[j] / pop_means[j]
            lr = tf_means[j] / rand_means[j]
            tf_top = tf_means[j] + tf_stds[j]
            ax.text(
                x[j] - width, tf_top + 0.07,
                f"{lp:.1f}×/{lr:.1f}×",
                ha="center", fontsize=8, fontweight="bold", color="#2563eb",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#e0e7ff",
                          edgecolor="#2563eb", linewidth=0.8),
            )

    ax.set_xticks(x)
    ax.set_xticklabels(domain_labels, fontsize=11)
    ax.set_ylabel(label, fontsize=11)
    ax.set_title(label, fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles, labels,
    loc="lower center", ncol=3, fontsize=12, framealpha=0.95,
    bbox_to_anchor=(0.5, 0.02),
)

fig.suptitle(
    f"Експериментальна оцінка системи рекомендацій  "
    f"({data['metadata']['n_runs']} прогонів × {data['metadata']['personas_count']} персон, mean ± std)",
    fontsize=14, fontweight="bold", y=1.00,
)
plt.tight_layout(rect=[0, 0.07, 1, 1])
out1 = THIS_DIR / "chart_overall.png"
plt.savefig(out1, dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ {out1.name}")


fig, ax = plt.subplots(figsize=(9.0, 5.5))
metric_keys = ["p@10", "r@10", "mrr@10"]
metric_labels_lift = ["Precision@10", "Recall@10", "MRR@10"]
tfidf  = data["overall"]["tfidf"]
pop    = data["overall"]["pop"]
rand   = data["overall"]["rand"]

x2 = np.arange(len(metric_keys))
width2 = 0.27
m_tfidf = [tfidf[k]["mean"] for k in metric_keys]
s_tfidf = [tfidf[k]["std"]  for k in metric_keys]
m_pop   = [pop[k]["mean"]   for k in metric_keys]
s_pop   = [pop[k]["std"]    for k in metric_keys]
m_rand  = [rand[k]["mean"]  for k in metric_keys]
s_rand  = [rand[k]["std"]   for k in metric_keys]

b1 = ax.bar(x2 - width2, m_tfidf, width2, yerr=s_tfidf, label="TF-IDF",
            color="#2563eb", capsize=5, edgecolor="black", linewidth=0.5)
b2 = ax.bar(x2,          m_pop,   width2, yerr=s_pop,   label="Popularity",
            color="#fb923c", capsize=5, edgecolor="black", linewidth=0.5)
b3 = ax.bar(x2 + width2, m_rand,  width2, yerr=s_rand,  label="Random",
            color="#94a3b8", capsize=5, edgecolor="black", linewidth=0.5)

for bars, means in [(b1, m_tfidf), (b2, m_pop), (b3, m_rand)]:
    for b, m in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.03,
                f"{m:.2f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

ax.set_xticks(x2)
ax.set_xticklabels(metric_labels_lift, fontsize=12)
ax.set_ylabel("Значення метрики", fontsize=12)
ax.set_title(
    "Загальне порівняння алгоритмів (усереднено по 15 персон × 5 посівів)",
    fontsize=13, fontweight="bold",
)
ax.set_ylim(0, 1.30)
ax.grid(axis="y", alpha=0.3, linestyle="--")
ax.set_axisbelow(True)

for i, k in enumerate(metric_keys):
    tf_v = tfidf[k]["mean"]
    pop_v = pop[k]["mean"]
    rand_v = rand[k]["mean"]
    if pop_v > 0 and rand_v > 0:
        ax.text(
            x2[i], 1.20,
            f"{tf_v/pop_v:.1f}× vs Pop\n{tf_v/rand_v:.1f}× vs Rand",
            ha="center", fontsize=9, fontweight="bold", color="#2563eb",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#e0e7ff",
                      edgecolor="#2563eb", linewidth=1),
        )

ax.legend(loc="lower center", ncol=3, fontsize=11, framealpha=0.95,
          bbox_to_anchor=(0.5, -0.18))

plt.tight_layout(rect=[0, 0.05, 1, 1])
out2 = THIS_DIR / "chart_lift.png"
plt.savefig(out2, dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ {out2.name}")
print("\nDone. PNG-файли готові для вставки у слайд.")
