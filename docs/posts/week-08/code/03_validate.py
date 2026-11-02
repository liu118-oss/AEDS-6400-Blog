"""Validate saved numerical outputs independently of the figure-building script."""

import csv
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / "data/parameters.json").read_text())


def read(name):
    with (ROOT / name).open() as f:
        return list(csv.DictReader(f))


def column(name, key):
    return np.array([float(r[key]) for r in read(name)])


M = {r["metric"]: float(r["value"]) for r in read("results/metrics.csv")}
example = column("data/example_deliveries.csv", "minutes")
observed = column("data/test_deliveries.csv", "minutes")
boot = column("results/bootstrap_means.csv", "mean_minutes")
null = column("results/null_means.csv", "mean_minutes")
assert len(example) == len(observed) == P["example_n"]
assert np.all(example > 0) and np.all(observed > 0)
assert len(boot) == P["bootstrap_reps"] and len(null) == P["null_reps"]
assert np.isclose(example.mean(), M["example_mean"])
assert np.isclose(observed.mean(), M["observed_mean"])
assert np.allclose(
    np.quantile(boot, [0.025, 0.975]), [M["bootstrap_lower"], M["bootstrap_upper"]]
)
rows = read("results/coverage_intervals.csv")
summaries = read("results/coverage_summary.csv")
assert (
    len(rows)
    == len(P["sample_sizes"]) * len(P["confidence_levels"]) * P["coverage_reps"]
)
for s in summaries:
    group = [r for r in rows if r["n"] == s["n"] and r["confidence"] == s["confidence"]]
    assert len(group) == P["coverage_reps"]
    assert {int(r["replicate"]) for r in group} == set(range(1, P["coverage_reps"] + 1))
    low = np.array([float(r["lower"]) for r in group])
    high = np.array([float(r["upper"]) for r in group])
    hits = (low <= P["population_mean"]) & (P["population_mean"] <= high)
    assert np.all(low <= high)
    assert np.array_equal(hits.astype(int), [int(r["covered"]) for r in group])
    assert np.isclose(hits.mean(), float(s["coverage"]))
    assert np.isclose(np.mean(high - low), float(s["mean_width"]))
    assert np.isclose(
        np.sqrt(hits.mean() * (1 - hits.mean()) / len(group)), float(s["mc_se"])
    )
for n in P["sample_sizes"]:
    for rep in range(1, P["coverage_reps"] + 1):
        group = sorted(
            [r for r in rows if int(r["n"]) == n and int(r["replicate"]) == rep],
            key=lambda r: float(r["confidence"]),
        )
        assert len({r["sample_mean"] for r in group}) == 1
        assert np.all(np.diff([float(r["lower"]) for r in group]) <= 0)
        assert np.all(np.diff([float(r["upper"]) for r in group]) >= 0)
left = (np.count_nonzero(null <= observed.mean()) + 1) / (len(null) + 1)
right = (np.count_nonzero(null >= observed.mean()) + 1) / (len(null) + 1)
assert np.isclose(min(1, 2 * min(left, right)), M["p_value"])
assert bool(M["reject"]) == (M["p_value"] <= 0.05)
assert bool(M["reject"]) == (
    observed.mean() < M["critical_lower"] or observed.mean() > M["critical_upper"]
)
tests = read("results/test_rejections.csv")
for label in ["null", "alternative"]:
    group = [r for r in tests if r["scenario"] == label]
    assert len(group) == P["rejection_reps"]
    means = np.array([float(r["sample_mean"]) for r in group])
    rejected = (means < M["critical_lower"]) | (means > M["critical_upper"])
    assert np.array_equal(rejected.astype(int), [int(r["rejected"]) for r in group])
    assert np.isclose(rejected.mean(), M[f"reject_rate_{label}"])
    assert np.isclose(
        np.sqrt(rejected.mean() * (1 - rejected.mean()) / len(group)),
        M[f"reject_se_{label}"],
    )
report = {
    "status": "passed",
    "coverage_intervals_checked": len(rows),
    "scenarios_checked": len(summaries),
    "checks": [
        "sample sizes and positive times",
        "sample means and bootstrap quantiles",
        "coverage and widths",
        "Monte Carlo errors",
        "nested confidence intervals",
        "corrected p-value and rejection rule",
        "repeated-test rejection rates",
    ],
}
(ROOT / "results/validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
