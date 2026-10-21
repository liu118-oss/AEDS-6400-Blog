"""Generate both article figures from saved estimates."""

from pathlib import Path
import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/blog6-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

B = Path(__file__).resolve().parents[1]
r = pd.read_csv(B / "results/estimates.csv").set_index("model")
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
for keys, labels, title, subtitle, name in [
    (
        ["single", "average"],
        ["One year each", "Several years each"],
        "Does averaging change the estimate?",
        "Same mother–child pairs in both estimates",
        "01_averaging",
    ),
    (
        ["young", "older"],
        ["Child ages 25–29", "Child ages 35–39"],
        "When we measure earnings also matters",
        "Same children; the same maternal average in both estimates",
        "02_lifecycle",
    ),
]:
    s = r.loc[keys]
    fig, ax = plt.subplots(figsize=(8.4, 4.9))
    colors = ["#768a9e", "#226a86"]
    for i, (key, row) in enumerate(s.iterrows()):
        ax.errorbar(
            i,
            row.beta,
            yerr=1.96 * row.se,
            fmt="o",
            color=colors[i],
            markersize=10,
            capsize=7,
            elinewidth=2.2,
        )
        ax.annotate(
            f"{row.beta:.3f}",
            (i, row.upper),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontweight="bold",
            color=colors[i],
        )
    ax.axhline(0, color="#b4b4b4", lw=1)
    ax.set_xticks([0, 1], labels)
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylabel("Intergenerational earnings elasticity")
    ax.set_ylim(min(-0.025, s.lower.min() - 0.04), max(0.20, s.upper.max() + 0.085))
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    fig.suptitle(title, x=0.10, ha="left", fontsize=16, fontweight="bold", y=0.98)
    ax.set_title(subtitle, loc="left", fontsize=10, color="#555", pad=16)
    fig.text(
        0.10,
        0.025,
        f"N = {int(s.iloc[0]['n']):,} children; {int(s.iloc[0].mothers):,} mothers. Bars: 95% mother-clustered confidence intervals.\nSource: NLSY79 / Child and Young Adult, 1979–2018 files; author’s calculations.",
        fontsize=9,
        color="#555",
    )
    fig.subplots_adjust(left=0.12, right=0.96, top=0.80, bottom=0.20)
    fig.savefig(B / f"results/{name}.png", dpi=180, facecolor="white")
    plt.close(fig)
