# Target Definition

`next_year_financial_pressure` is an analytical label for the same company's actual next fiscal year, not observed default or a credit rating.

For a row with feature year `t`, label 1 requires at least two signals in year `t+1`:

| Signal | Rule |
|---|---|
| Negative operating margin | Operating income(t+1) / revenue(t+1) < 0 |
| Negative operating cash flow | Operating cash flow(t+1) / assets(t+1) < 0 |
| Revenue contraction | Revenue(t+1) / revenue(t) − 1 ≤ −10% |

All signals must be computable, with finite inputs and positive revenue and assets denominators. The next row must have the same CIK and fiscal year exactly `t+1`. Otherwise the label is unknown. When complete, fewer than two signals gives 0. The two-of-three rule and −10% threshold are fixed analytical choices, not tuned for model performance.

Growth necessarily uses revenue in both `t` and `t+1`. Features use `t` or earlier. Unknown labels are excluded from rate denominators, training and evaluation; they are never treated as No Pressure. Tableau heatmaps use `outcome_year = fiscal_year + 1` and known labels only.

Shared implementation: [analysis_helpers.py](../notebooks/analysis_helpers.py). The persistence baseline is separate: it counts current-year signals and uses no positive evidence for a missing current input. An incomplete target always remains unknown.

The fiscal-year ordering prevents cross-company and year-gap target errors. It does not establish point-in-time availability of annual filings or revised macro data. Scores support review prioritization only.
