# Analysis decisions fixed before evaluating test results

- Data: all tickers in the supplied class script plus SPY; Yahoo adjusted prices, January 2022–December 2025. No substitution or silent removal of failed tickers.
- Test: 2024–2025. Models frozen before 2024; no test-driven hyperparameter selection.
- Target: adjusted price at t+20 / adjusted price at t+1 - 1, exactly as in class (19 daily returns).
- Clean original baseline: all original numeric inputs and stated boosting settings; exclude labels ending on or after January 1, 2024. Python XGBoost reimplementation, not an identical R environment.
- Diagnostic original: original date-only split, allowing overlapping training labels, reported separately and never used for model selection.
- Improved inputs: conventional momentum at 5, 21, 63 and 126 observations with a one-day lag; lagged 21-day volatility, 21-day market-relative momentum, lagged daily excess return. No raw OHLC or volume levels.
- Candidate grid: depth {1,2}, child weight {30,100}, trees {100,300}; learning rate .03, row fraction .8, feature fraction 1, L2 penalty 10. Eight candidates, no expansion after test inspection.
- Validation: expanding training, validation signal dates in 2023 Q2, Q3 and Q4; exclude labels crossing each boundary and labels unavailable by 2024. Select lowest equally weighted mean fold MSE.
- Forecast benchmark: constant pooled mean of training targets. Main predictive scores use non-overlapping scheduled signal dates; daily-overlapping scores are supplemental.
- Portfolio: common top-ten positive-forecast-proportional weights, equal weights if none positive. Rebalance every 19 trading sessions, next-close execution, holding until the next execution. Same rule for both models. Fully invested, no leverage or shorts.
- Investment benchmarks: buy-and-hold SPY and periodically rebalanced equal-weight class universe, same dates. Costs 0, 10 and 25 basis points per dollar traded, including entry and final liquidation, with drifted pre-trade weights. Risk-free rate assumed zero and labeled explicitly.
- Report daily-path CAGR, volatility, zero-rate Sharpe, drawdown, turnover, annual returns and predictive accuracy. Include paired block-bootstrap forecast-loss uncertainty and sensitivity to costs. Do not treat individual stocks or overlapping daily targets as independent evidence.
- Preserve original script; document changes and limitations, especially retrospective universe selection, adjusted-price vintage and short test period.
