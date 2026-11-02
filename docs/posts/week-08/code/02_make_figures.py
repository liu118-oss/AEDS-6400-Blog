"""Make two static figures and one self-contained interactive coverage figure."""

import csv
import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
P = json.loads((ROOT / "data/parameters.json").read_text())


def read(name):
    with (OUT / name).open() as f:
        return list(csv.DictReader(f))


M = {r["metric"]: float(r["value"]) for r in read("metrics.csv")}
boot = np.array([float(r["mean_minutes"]) for r in read("bootstrap_means.csv")])
null = np.array([float(r["mean_minutes"]) for r in read("null_means.csv")])
BLUE, ORANGE = "#176d86", "#c15c28"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
    }
)

# Figure 1: the sample is held fixed; only its resampled observations change.
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.hist(boot, bins=40, color=BLUE, alpha=0.8, edgecolor="white", linewidth=0.4)
ax.axvspan(M["bootstrap_lower"], M["bootstrap_upper"], color=BLUE, alpha=0.10)
for bound in ["bootstrap_lower", "bootstrap_upper"]:
    ax.axvline(M[bound], color=ORANGE, linestyle="--", linewidth=2)
ax.axvline(
    M["example_mean"],
    color="#253444",
    linewidth=2,
    label=f"Sample mean: {M['example_mean']:.2f}",
)
ax.plot(
    [],
    [],
    color=ORANGE,
    linestyle="--",
    label=f"95% interval: {M['bootstrap_lower']:.2f}–{M['bootstrap_upper']:.2f}",
)
ax.set(
    title="One sample, many resampled means",
    xlabel="Bootstrap mean delivery time (minutes)",
    ylabel="Bootstrap replicates",
)
ax.legend(frameon=False, loc="upper right", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "01_bootstrap.png", dpi=180)
plt.close(fig)

# Figure 3: fixed 5% rejection tails and the observed-result tail are different.
DARK = "#253444"
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
bins = np.linspace(
    min(null.min(), M["observed_mean"]) - 0.2,
    max(null.max(), M["observed_mean"]) + 0.2,
    55,
)
for ax in axes:
    ax.hist(null, bins=bins, color="#d9e3e8", edgecolor="white", linewidth=0.3)
    ax.set(xlabel="Sample mean (minutes)")
# Extra headroom keeps the annotations above the histogram peak.
top = 1.3 * axes[0].get_ylim()[1]
axes[0].set_ylim(0, top)
axes[0].axvline(M["observed_mean"], color=DARK, linewidth=2)
# Stop the right-hand line below the inset, which repeats it at a readable scale.
axes[1].axvline(M["observed_mean"], ymax=0.27, color=DARK, linewidth=2)
axes[0].hist(
    null[(null < M["critical_lower"]) | (null > M["critical_upper"])],
    bins=bins,
    color=ORANGE,
)
for bound in ["critical_lower", "critical_upper"]:
    axes[0].axvline(M[bound], color=ORANGE, linestyle="--", linewidth=1.5)
    axes[0].text(
        M[bound] - 0.12,
        0.97 * top,
        f"{M[bound]:.2f}",
        ha="right",
        va="top",
        color=ORANGE,
        fontsize=10,
    )
axes[0].text(
    M["observed_mean"] + 0.12,
    0.80 * top,
    f"Observed\n{M['observed_mean']:.2f}",
    ha="left",
    va="top",
    fontsize=10,
)
axes[0].text(
    0.03,
    0.80,
    "Reject in either\norange tail\n(2.5% each)",
    transform=axes[0].transAxes,
    va="top",
    color=ORANGE,
    fontsize=10,
)
axes[0].set(title="Where would I reject?", ylabel="Simulated samples under the null")

# The p-value doubles the smaller tail, so shade an equally large opposite tail too.
ordered = np.sort(null)
k = int(min(M["left_count"], M["right_count"]))
upper_tail = M["right_count"] <= M["left_count"]
tail, mirror = (ordered[-k:], ordered[:k]) if upper_tail else (ordered[:k], ordered[-k:])
axes[1].hist(tail, bins=bins, color=BLUE)
axes[1].hist(mirror, bins=bins, color=BLUE, alpha=0.35)
axes[1].set(title="How unusual is this result?")
axes[1].text(
    0.03,
    0.97,
    f"Observed mean: {M['observed_mean']:.2f}\n"
    f"{k} of {len(null):,} null means ≥ {M['observed_mean']:.2f}\n"
    f"p = 2 × ({k} + 1) / ({len(null) + 1:,}) = {M['p_value']:.3f}",
    transform=axes[1].transAxes,
    va="top",
    fontsize=10,
)
axes[1].annotate(
    "Light: equal-size\nopposite tail",
    xy=(mirror.mean(), 0.03 * top),
    xytext=(mirror.mean(), 0.22 * top),
    ha="center",
    fontsize=9,
    color=BLUE,
    arrowprops=dict(arrowstyle="->", color=BLUE),
)
# Zoom in: the observed tail holds about 0.5% of the simulations and is hard to see.
inset = axes[1].inset_axes([0.64, 0.30, 0.34, 0.36])
zoom = bins[bins >= M["critical_upper"] - 0.3]
inset.hist(null, bins=zoom, color="#d9e3e8", edgecolor="white", linewidth=0.3)
inset.hist(tail, bins=zoom, color=BLUE)
inset.axvline(M["observed_mean"], color=DARK, linewidth=1.5)
inset.set_title("Zoom on the upper tail", fontsize=9, fontweight="normal")
inset.tick_params(labelsize=8)
fig.tight_layout()
fig.savefig(OUT / "03_null_test.png", dpi=180)
plt.close(fig)

# Figure 2: both menus read one shared state. Endpoints stay on a fixed scale.
rows = read("coverage_intervals.csv")
summaries = read("coverage_summary.csv")
scenarios = {}
all_bounds = []
for summary in summaries:
    n, level = int(summary["n"]), float(summary["confidence"])
    subset = [
        r
        for r in rows
        if int(r["n"]) == n
        and float(r["confidence"]) == level
        and int(r["replicate"]) <= P["display_intervals"]
    ]
    traces = []
    for covered, color, name in [
        (1, BLUE, "Contains true mean"),
        (0, ORANGE, "Misses true mean"),
    ]:
        group = [r for r in subset if int(r["covered"]) == covered]
        x, y = [], []
        for r in group:
            x.extend([float(r["lower"]), float(r["upper"]), None])
            y.extend([int(r["replicate"]), int(r["replicate"]), None])
        traces.append(
            dict(
                type="scatter",
                mode="lines",
                x=x,
                y=y,
                name=name,
                line=dict(color=color, width=2),
                hoverinfo="skip",
                showlegend=True,
            )
        )
        traces.append(
            dict(
                type="scatter",
                mode="markers",
                x=[float(r["sample_mean"]) for r in group],
                y=[int(r["replicate"]) for r in group],
                marker=dict(color=color, size=4),
                showlegend=False,
                customdata=[[float(r["lower"]), float(r["upper"])] for r in group],
                hovertemplate="Experiment %{y}<br>Mean: %{x:.2f}<br>Interval: [%{customdata[0]:.2f}, %{customdata[1]:.2f}]<extra></extra>",
            )
        )
    all_bounds.extend([float(r[k]) for r in subset for k in ["lower", "upper"]])
    scenarios[f"{n}-{round(level * 100)}"] = dict(
        traces=traces,
        coverage=float(summary["coverage"]),
        width=float(summary["mean_width"]),
        mc_se=float(summary["mc_se"]),
        experiments=int(summary["experiments"]),
    )
layout = dict(
    template="plotly_white",
    height=610,
    margin=dict(l=45, r=15, t=75, b=55),
    font=dict(family="Arial", size=12),
    xaxis=dict(
        title="Mean delivery time (minutes)",
        range=[int(np.floor(min(all_bounds))) - 1, int(np.ceil(max(all_bounds))) + 1],
    ),
    yaxis=dict(title="Experiment", range=[P["display_intervals"] + 1, 0], dtick=20),
    legend=dict(orientation="h", x=0, y=1.15),
    shapes=[
        dict(
            type="line",
            x0=P["population_mean"],
            x1=P["population_mean"],
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="#253444", dash="dash", width=2),
        )
    ],
)
fig = go.Figure(data=scenarios["200-95"]["traces"], layout=layout)
# Send Plotly.js its normalized layout (axis titles and template are objects).
layout = fig.layout.to_plotly_json()
controls = """<div class="controls"><div><label for="sample-size">Orders per sample</label><select id="sample-size"><option>50</option><option selected>200</option><option>500</option></select></div><div><label for="confidence">Confidence level</label><select id="confidence"><option value="90">90%</option><option value="95" selected>95%</option><option value="99">99%</option></select></div></div><p id="summary" aria-live="polite"></p><p class="note">Showing the first 100 experiments. Summary uses all 1,000. Dashed line: true mean = 30 minutes.</p>"""
style = """<meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0;color:#243547;font:15px system-ui}.controls{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:8px}label{display:block;font-weight:600;margin-bottom:6px}select{width:100%;font:inherit;padding:8px;background:white;border:1px solid #a6b7c0;border-radius:5px}#summary{margin:10px 8px;padding:12px;background:#eff5f7;border-radius:5px;line-height:1.5;min-height:46px}.note{font-size:13px;margin:8px;line-height:1.4}@media(max-width:450px){.controls{gap:8px}}</style>"""
script = (
    "const scenarios="
    + json.dumps(scenarios)
    + ";const fixedLayout="
    + json.dumps(layout)
    + ";"
    + """
function updateCoverage(){
 const n=document.getElementById('sample-size').value;
 const level=document.getElementById('confidence').value;
 const s=scenarios[n+'-'+level];
 Plotly.react('coverage',s.traces,fixedLayout,{responsive:true,displayModeBar:false,displaylogo:false});
 document.getElementById('summary').textContent='Coverage: '+(100*s.coverage).toFixed(1)+'% | Average width: '+s.width.toFixed(2)+' minutes | '+s.experiments.toLocaleString()+' experiments';
}
document.getElementById('sample-size').addEventListener('change',updateCoverage);
document.getElementById('confidence').addEventListener('change',updateCoverage);
updateCoverage();
"""
)
html = fig.to_html(
    full_html=True,
    include_plotlyjs="plotly.min.js",
    div_id="coverage",
    config=dict(responsive=True, displayModeBar=False, displaylogo=False),
    post_script=script,
)
html = html.replace("<head>", "<head>" + style).replace("<body>", "<body>" + controls)
(OUT / "02_coverage.html").write_text(html)
(OUT / "plotly.min.js").write_text(get_plotlyjs())
print("Saved three figures and nine interactive settings.")
