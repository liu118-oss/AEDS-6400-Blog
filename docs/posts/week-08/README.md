# Blog 8: Is the Average Delivery Time Really 30 Minutes?

## Reproduce

All data are simulated. No account, API key or download of observations is needed. From this folder, use Python 3.12+ and install dependencies (the recorded NumPy version may require a recent Python):

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python code/01_simulate.py
python code/02_make_figures.py
python code/03_validate.py
```

Simulation includes 3,000 outer experiments, each with 2,000 bootstrap replicates. Allow time for it to finish; progress prints after each sample size. Computation is performed one experiment at a time to bound memory usage. To reproduce only figures from saved outputs, run `02_make_figures.py`.

From the repository root, render using Quarto, R, knitr and rmarkdown:

```sh
quarto render posts/week-08/index.qmd
python3 -m http.server 8767 --directory docs
```

Preview http://127.0.0.1:8767/posts/week-08/ (use another port if occupied). Plotly JavaScript is bundled locally; the interactive chart does not require a server-side application or CDN. Do not upload a virtual environment.

## Files

- `index.qmd`: article; numeric results are read from results/metrics.csv.
- `data/parameters.json`: complete assumptions, sample sizes, repetitions and seed.
- `data/example_deliveries.csv`: 200 observations from mean-30 population.
- `data/test_deliveries.csv`: separate 200-observation sample from mean-33 population.
- `code/01_simulate.py`: sampling, bootstrap intervals, repeated coverage experiments and null simulation.
- `code/02_make_figures.py`: static bootstrap and test figures, interactive coverage figure.
- `code/03_validate.py`: arithmetic and consistency checks on saved outputs.
- `results/bootstrap_means.csv`: 2,000 means from resampling the one example sample.
- `results/coverage_intervals.csv`: all 9,000 intervals (3 sizes × 3 levels × 1,000 experiments).
- `results/coverage_summary.csv`: coverage, mean width and Monte Carlo standard error for each setting.
- `results/null_means.csv`: 10,000 null-distribution means.
- `results/test_rejections.csv`: 5,000 repeated tests under the null and 5,000 under the mean-33 alternative, with each reject decision.
- `results/metrics.csv`: article numbers.
- `results/`: figures, bundled Plotly JavaScript and validation results.

## Simulation design

Seed: 20261102, with NumPy SeedSequence child streams for the example sample, example bootstrap, alternative sample, null simulation, coverage experiments and repeated tests. Settings were fixed before examining results. Every observation is independent under the model; no company data are represented.

Let sigma = sqrt(log(1 + (15/30)^2)). Generate lognormal observations with log-location log(mean) - sigma^2/2. This yields arithmetic mean 30 and SD 15 in the baseline. Keeping sigma fixed at mean 33 makes the alternative SD 16.5, rather than 15. This is intentional: the hypothesis test treats the shape as specified. The code does not estimate the shape from the observed test sample.

Bootstrap: resample n observations with replacement 2,000 times; average each resample. The equal-tailed percentile interval uses quantiles [(1-level)/2, (1+level)/2], NumPy's default linear interpolation. Quantiles are recomputed for every new outer sample. Confidence levels within a sample share bootstrap draws; sample-size scenarios use separate streams. Larger n need not produce strictly increasing empirical coverage in a finite run.

Coverage: 1,000 independent samples per n from the mean-30 population. Coverage is mean(lower <= 30 <= upper). Monte Carlo SE = sqrt(coverage*(1-coverage)/1000). The graph shows the first 100 experiments without selecting hits or misses; its numerical summaries use all 1,000. The x-axis is fixed across settings. The finite-sample percentile method can under-cover; the observed coverage is reported without tuning seeds.

Null test: the observed sample is separately generated with true mean 33; H0 has mean 30 and known shape sigma. The statistic is the sample mean. From B=10,000 null means, count values <= and >= the observed mean. Corrected tail probabilities are (count+1)/(B+1); p = min(1, 2*min(lower_tail, upper_tail)). Reject at p <= 0.05. To match this rank rule, k=floor(0.025*(B+1))=250; the lower/upper critical values are the kth smallest/largest null means, with strict outside-boundary rejection. They approximate the 2.5th/97.5th percentiles. In this run the two decision rules agree. The right-hand panel shades the smaller observed tail and, more lightly, the same number of the most extreme null means on the opposite side; together they illustrate the doubled two-sided p. An inset zooms in on the observed tail.

Repeated tests: using the fixed critical values above, 5,000 fresh samples of 200 from the mean-30 population estimate the false-rejection rate (size), and 5,000 from the mean-33 population estimate power. Monte Carlo SE = sqrt(rate*(1-rate)/5000). These use the sixth SeedSequence child stream, so adding them does not change any earlier output.

The bootstrap interval and the parametric null test illustrate different procedures and use different observed samples. Do not interpret them as an inverted CI/test pair. The displayed sample mean is a statistic, not a single delivery time. A 95% procedure does not put 95% of delivery times inside its interval.

## Sources

Data: generated for this post on November 2, 2026, from explicit hypothetical assumptions. The CSVs are simulation outputs, not measured delivery records.

- UC Berkeley STAT 135, [Bootstrap percentile interval](https://stat135.berkeley.edu/fall-2026/Modules/12-Bootstrap.html).
- NIST/SEMATECH e-Handbook, [Confidence limits for the mean](https://itl.nist.gov/div898/handbook/eda/section3/eda352.htm).
- NIST/SEMATECH e-Handbook, [Critical values and p-values](https://itl.nist.gov/div898/handbook/prc/section1/prc131.htm).

These are method references; none supplied delivery observations.
