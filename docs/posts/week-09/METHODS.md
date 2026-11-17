# Methods and audit notes

## Scope of reproduction

The original R script is preserved unchanged. Its comment describes 100 companies; the vector actually contains 95. We use all 95 and SPY, with no missing trading dates in the downloaded snapshot. Yahoo's OHLC fields are used as downloaded; adjusted close supplies returns. Historical adjustments are current-vintage, not point-in-time data.

This is a Python implementation of the intended class XGBoost specification, not an exact reproduction of the original R libraries or classroom results. We explicitly set histogram trees, squared-error objective, seed 123, two threads and the training mean as the initial base score. XGBoost version and R/Python engine defaults can cause differences. The main original model keeps the specified 300 trees, depth 5, learning rate .05, minimum child weight 10 and gamma 0, with unit row/feature sampling and L2 penalty 1.

The original recipe includes every numeric input, not only the engineered indicators: OHLC, volume, adjusted price, daily return, SPY daily return, three inverse momentum ratios, lagged volatility, inverse five-day return and current excess return. Date and symbol remain identifiers. Original `slide_dbl(.before=21)` covers 22 observations and is reproduced as such. Feature rows use shared complete-case support, starting one day later than the original alone because the improved 126-day momentum needs 127 past rows. Thus even the diagnostic is not represented as a byte-for-byte R rerun.

## Forecast timing and split

Signals use information available at the signal day's close. Entry is the following trading day's close. The target is `adjusted[t+20] / adjusted[t+1] - 1`, containing 19 daily returns. No target is included unless both endpoint prices exist. Training labels must end before 2024-01-01. The ordinary date-only split is reproduced as a separately labeled unpurged diagnostic, never used to choose a model.

The fixed test window is 2024–2025. Main scheduled signals begin on January 2, 2024 and repeat every 19 trading sessions, retaining only full target windows. The last exit is December 22, 2025. Holding periods join at the same close, so all strategies have exactly matched exposure dates. We deliberately replace monthly rebalance dates with a fixed trading-session schedule to match the original prediction target. Other rebalance offsets are not tested; sensitivity to that choice remains a limitation.

## Improved features and tuning

All improved features are known at least one trading day before the signal closes:

- Momentum at k=5,21,63,126: `P[t-1] / P[t-k-1] - 1`.
- Volatility: sample standard deviation of 21 daily returns ending at t-1.
- Relative momentum: the stock's 21-day momentum less SPY's corresponding momentum.
- Excess lag: stock daily return less SPY daily return at t-1.

Eight candidates combine depths {1,2}, minimum child weights {30,100} and tree counts {100,300}, with learning rate .03, row subsampling .8, feature sampling 1 and L2 penalty 10. Validation quarters start April 1, July 1 and October 1, 2023. Training uses expanding history with target endpoints strictly before the quarter; validation labels must end before the following quarter. The score is the equally weighted mean of the three fold MSEs. There is no random row split and no test-driven early stopping. Overlapping validation labels are used for selection, not for naive standard-error calculations.

The final training mean provides a constant forecast benchmark. The name “Improved” identifies the attempted procedure, not a claim that it improves every outcome.

## Predictive metrics and uncertainty

Main accuracy metrics use 26 non-overlapping signal dates and 95 stocks per date. RMSE and MAE are expressed in percentage points. Out-of-sample R² is `1 - SSE_model / SSE_training_mean`. Direction accuracy compares positive-return indicators. Mean rank IC averages date-level Spearman correlations and is undefined for the constant forecast. Supplemental metrics include all daily forecasts and explicitly flag their overlapping labels.

Loss uncertainty aggregates squared-error differences across all stocks at each signal date, then uses a circular moving-block bootstrap with block length 3, 5,000 draws and seed 123. The intervals are percentile intervals for the mean difference, not a probability that a strategy will profit. The limited 26-date sample and untested block-length sensitivity restrict interpretation.

## Corrected portfolios

Both models use the same intended class allocation: top ten forecasts, negative values truncated to zero, and weights proportional to positive forecasts; equal weights if all selected forecasts are nonpositive. Ties break alphabetically by symbol. Casting scores to float64 before normalization avoids float32 budget-rounding drift. Weights sum to one; there is no leverage, shorting, leverage financing or discretionary risk overlay.

The simple investment benchmarks are equal-weight holdings of all 95 stocks, rebalanced on the same schedule, and SPY buy-and-hold. The scalar historical-mean forecast cannot rank stocks, which is why its natural investment counterpart is equal weighting rather than an arbitrarily chosen top ten.

Between rebalances, shares are held fixed in adjusted-price equivalents. Current weights drift with realized returns. Costs of 0, 10 or 25 basis points apply to dollars bought plus sold. At a rebalance, the retained wealth fraction v solves `v = 1 - c * sum(abs(v*w_target - w_drift))`; this charges costs consistently without spending more than available capital. Initial cash-to-portfolio purchase and final liquidation are included. Taxes, slippage beyond the stated cost assumption, market impact, capacity, lending/borrowing and execution failures are excluded. Price adjustments approximate reinvested distributions.

## Risk and return calculations

- Final wealth is compounded actual strategy wealth, net of specified costs.
- CAGR uses elapsed calendar days / 365.25.
- Annual volatility is sample standard deviation of daily returns times sqrt(252).
- The reported Sharpe uses daily mean / daily standard deviation times sqrt(252), with **zero assumed risk-free rate**. It is not a Treasury-adjusted excess-return ratio.
- Maximum drawdown uses the daily path against its previous peak, including the initial value of 1.
- Traded notional counts purchases and sales; it is not the half-turnover convention. Entry and exit are included.
- Calendar-year results cover only the available test window: January 3–December 31, 2024 and the available 2025 dates through December 22. Costs charged on a shared rebalance close enter that date's daily return.

We do not claim statistically established CAPM alpha. Higher realized returns may reflect risk exposures, concentrated winners or chance, and the available history cannot settle those explanations. `stock_contributions.csv` sums per-period arithmetic contributions descriptively; these sums are not additive decompositions of terminal compounded wealth.

## Original-code issues separated from model changes

1. **Overlapping training labels:** a December signal can include January outcomes. Main models purge these rows.
2. **Scalar R `ifelse`:** `ifelse(sum(p)==0,1/n,p/sum(p))` has a length-one test and returns only one element. Grouped mutate repeats it. The normalized intended weights are implemented in the fair comparison; `class_bookkeeping_diagnostic.csv` separately reconstructs the invalid behavior from the unpurged Python model. The R semantics were verified directly using `p=c(.10,.05,.02)`.
3. **Mismatched holding windows:** target returns span 19 trading returns while SPY uses within-month returns, omitting the preceding month-end to first-day interval. The main backtest aligns actual entry/exit dates.
4. **Mismatched cumulative origins:** SPY compounds from 2022 before joining to test months. Main paths start together at $1.
5. **Incorrect annualization:** approximately monthly returns are scaled by sqrt(252) for Sharpe and 252 for alpha. Main risk statistics use daily paths with daily annualization. No invalid alpha is reported as evidence.
6. **Inverse momentum formulas:** these are reproduced for the baseline, but clearly redefined for the improved model. They are not intrinsically unusable tree inputs.
7. **Stale “current” rankings:** dropping rows without future target labels before prediction means the latest ranking is already about 20 sessions old. This project evaluates historical predictions, not live recommendations.

The diagnostic pseudo-wealth and incorrectly annualized Sharpe are saved only to expose implementation behavior. They are not valid portfolio results and are not mixed with the fair investment table.

## Executed verification

`analyze.py` verifies the snapshot checksum, unique symbol/date keys, positive adjusted prices, complete common calendar, all train/validation label boundaries, complete test cross-sections, target/holding-price identity and weight budgets. `audit.py` independently recalculates every gross holding return from saved weights and prices, verifies cost monotonicity, checks SPY against its direct adjusted-price ratio and rechecks every portfolio budget. Reports appear in `results/*verification.txt`.

## Remaining limits

The class universe is retrospectively selected; omitted failed or delisted stocks cannot be recovered from this list. Current-vintage adjustments, the small training span, only two test years, one rebalance offset and no genuine prospective trading all limit external validity. Equal-weighting the same universe improves comparison but does not remove universe-selection bias. No claim about the exact original classroom outcome is made.
