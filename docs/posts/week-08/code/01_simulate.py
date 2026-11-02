"""Generate all Blog 8 data. No downloads; assumptions are in data/parameters.json."""

import csv
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / "data/parameters.json").read_text())
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
# Separate streams prevent bootstrap/coverage settings from changing the examples.
streams = np.random.SeedSequence(P["seed"]).spawn(6)
example_rng, bootstrap_rng, alternative_rng, null_rng = [
    np.random.default_rng(s) for s in streams[:4]
]
sigma = np.sqrt(np.log1p((P["population_sd"] / P["population_mean"]) ** 2))


def population(rng, mean, size):
    """Arithmetic mean is mean; log-scale shape sigma is fixed across scenarios."""
    return rng.lognormal(np.log(mean) - sigma**2 / 2, sigma, size=size)


def save(name, fields, rows):
    with (ROOT / name).open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        w.writerows(rows)


def bootstrap_means(sample, rng):
    # Each row is an independent, with-replacement sample of the same size.
    indices = rng.integers(0, len(sample), size=(P["bootstrap_reps"], len(sample)))
    return sample[indices].mean(axis=1)


sample = population(example_rng, P["population_mean"], P["example_n"])
boot = bootstrap_means(sample, bootstrap_rng)
lo, hi = np.quantile(boot, [0.025, 0.975])
save("data/example_deliveries.csv", ["order", "minutes"], enumerate(sample, 1))
save("results/bootstrap_means.csv", ["replicate", "mean_minutes"], enumerate(boot, 1))
metrics = {
    "example_mean": float(sample.mean()),
    "bootstrap_lower": float(lo),
    "bootstrap_upper": float(hi),
}

# New independent samples for every coverage experiment. Reuse their bootstrap
# draws across confidence levels so only the interval rule changes in that comparison.
coverage_rows, summaries = [], []
coverage_streams = streams[4].spawn(len(P["sample_sizes"]))
for n, stream in zip(P["sample_sizes"], coverage_streams):
    rng = np.random.default_rng(stream)
    endpoints = {level: [] for level in P["confidence_levels"]}
    for rep in range(P["coverage_reps"]):
        fresh_sample = population(rng, P["population_mean"], n)
        means = bootstrap_means(fresh_sample, rng)
        for level in P["confidence_levels"]:
            alpha = 1 - level
            low, high = np.quantile(means, [alpha / 2, 1 - alpha / 2])
            covered = low <= P["population_mean"] <= high
            endpoints[level].append((float(low), float(high), int(covered)))
            coverage_rows.append(
                [
                    n,
                    level,
                    rep + 1,
                    float(fresh_sample.mean()),
                    float(low),
                    float(high),
                    int(covered),
                ]
            )
    for level, intervals in endpoints.items():
        arr = np.array(intervals)
        coverage = arr[:, 2].mean()
        summaries.append(
            [
                n,
                level,
                P["coverage_reps"],
                float(coverage),
                float(np.mean(arr[:, 1] - arr[:, 0])),
                float(np.sqrt(coverage * (1 - coverage) / P["coverage_reps"])),
            ]
        )
    print(f"Finished n={n}", flush=True)
save(
    "results/coverage_intervals.csv",
    ["n", "confidence", "replicate", "sample_mean", "lower", "upper", "covered"],
    coverage_rows,
)
save(
    "results/coverage_summary.csv",
    ["n", "confidence", "experiments", "coverage", "mean_width", "mc_se"],
    summaries,
)
for n, level, _, coverage, width, mc_se in summaries:
    if level == 0.95:
        metrics[f"coverage_{n}"] = coverage
        metrics[f"width_{n}"] = width
        metrics[f"mc_se_{n}"] = mc_se

# A separately generated alternative sample tests a pre-specified 30-minute claim.
# Keeping sigma fixed scales SD from 15 (mean 30) to 16.5 (mean 33).
observed = population(alternative_rng, P["alternative_mean"], P["example_n"])
null_means = population(
    null_rng, P["population_mean"], (P["null_reps"], P["example_n"])
).mean(axis=1)
observed_mean = observed.mean()
left_count = int(np.sum(null_means <= observed_mean))
right_count = int(np.sum(null_means >= observed_mean))
left_p = (left_count + 1) / (len(null_means) + 1)
right_p = (right_count + 1) / (len(null_means) + 1)
p_value = min(1.0, 2 * min(left_p, right_p))
# Order-statistic cutoffs agree with the corrected rank p-value, including at edges.
ordered = np.sort(null_means)
k = int(np.floor(0.025 * (len(null_means) + 1)))
critical_lower, critical_upper = ordered[k - 1], ordered[-k]
reject = bool(p_value <= 0.05)
assert reject == bool(observed_mean < critical_lower or observed_mean > critical_upper)
save("data/test_deliveries.csv", ["order", "minutes"], enumerate(observed, 1))
save("results/null_means.csv", ["replicate", "mean_minutes"], enumerate(null_means, 1))
metrics.update(
    observed_mean=float(observed_mean),
    critical_lower=float(critical_lower),
    critical_upper=float(critical_upper),
    p_value=p_value,
    left_count=left_count,
    right_count=right_count,
    reject=int(reject),
)

# Repeat the whole test on fresh samples. When H0 is true, the 5% rule should
# reject about 5% of the time; when the mean is really 33, the rate is power.
rejection_rng = np.random.default_rng(streams[5])
rejection_rows = []
for label, true_mean in [
    ("null", P["population_mean"]),
    ("alternative", P["alternative_mean"]),
]:
    means = population(
        rejection_rng, true_mean, (P["rejection_reps"], P["example_n"])
    ).mean(axis=1)
    rejected = (means < critical_lower) | (means > critical_upper)
    rate = float(rejected.mean())
    metrics[f"reject_rate_{label}"] = rate
    metrics[f"reject_se_{label}"] = float(np.sqrt(rate * (1 - rate) / len(means)))
    rejection_rows.extend(
        [label, true_mean, i, float(m), int(r)]
        for i, (m, r) in enumerate(zip(means, rejected), 1)
    )
save(
    "results/test_rejections.csv",
    ["scenario", "true_mean", "replicate", "sample_mean", "rejected"],
    rejection_rows,
)
save("results/metrics.csv", ["metric", "value"], metrics.items())
print(json.dumps(metrics, indent=2))
