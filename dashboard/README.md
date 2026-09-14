# Tableau Decision Support

Open [corporate_risk_dashboard.twbx](corporate_risk_dashboard.twbx) locally in Tableau Desktop. The packaged workbook includes all seven CSV sources and two fixed **1600 × 900** dashboards. It does not require access to the original computer's files.

## Corporate Financial Resilience

![Corporate Financial Resilience](../images/corporate-financial-resilience.png)

Five indicators describe the supplied panel: **2,767 companies**, **21,990 company-years**, **13.1% financial pressure among known labels**, **6.7% median operating margin**, and **8.2% median operating cash flow/assets**. Ratio medians use available observations. These are full-panel indicators, not filtered scatter statistics.

The heatmap groups known next-year labels by **outcome year** (feature year + 1). Unknown labels are excluded from its denominator. The line chart shows sector median operating margin by **feature year**. The panel covers 2012–2024, but 2024 has only 280 observations and is incomplete.

The scatter compares liabilities/assets with operating cash flow/assets for feature years 2021–2022. Its 3,823 source rows include known and unknown outcomes; 2,937 company-years have both plotted ratios. Missing coordinates are not plotted. Gray marks represent **Unknown**, rather than No Pressure. Tooltips identify the company, CIK, feature year, outcome year and plotted ratios.

**Filter scope:** Sector and Feature Year affect the scatter only. KPI cards, the heatmap and the sector trend retain their full-panel scope, as stated on the dashboard. All sectors and both scatter years are selected by default.

## Early Warning & Decision Support

![Early Warning and Decision Support](../images/early-warning-decision-support.png)

The default view covers **all 3,305 test company-years from 2021–2022**. The model table compares ranking performance; PR-AUC is average precision. At 15% annual review capacity:

| Model | PR-AUC (AP) | ROC-AUC | Recall | Precision |
|---|---:|---:|---:|---:|
| Persistence | 0.4756 | 0.7778 | 58.8% | 66.2% |
| Logistic Regression | 0.6964 | 0.8836 | 59.8% | 67.4% |
| Decision Tree | 0.5937 | 0.8467 | 59.3% | 66.8% |

Logistic Regression supplies the queue scores. Within each test feature year, scores sort descending, with ten-character CIK ascending as a reproducible tie-breaker. High receives the first `ceil(10% × n)` rows; High plus Medium receives the first `ceil(15% × n)`. Across the two years there are **331 High**, **166 Medium**, and **2,808 Routine** observations. The 497 High-plus-Medium reviews identify 335 of 560 known pressure cases. Annual rounding makes coverage slightly greater than 15%.

The High Review Priority table shows company, sector, feature year, score and three financial ratios. It orders years ascending and uses the exported annual review rank within each year. The scrollable table contains all 331 High observations; the static image shows its first rows. Company names may recur in different years. Scores and ratios display three decimal places, while sorting uses full precision.

**Filter scope:** The Feature Year selector defaults to **All** and affects only the review queue. Selecting 2021 or 2022 narrows that table. Model metrics, tier counts and the native sector box plot continue to summarize both test years, as stated on the dashboard. Pre-aggregated model metrics should not be presented as single-year results.

The risk score is a screening/ranking signal, not a probability of default, credit rating or automatic decision. Four suggested actions emphasize reviewing High and Medium cases, checking filings and cash flow, retaining persistence as a benchmark, and treating scenario changes as sensitivity analysis.

## Sources and Display Conventions

[Notebook 05](../notebooks/05_scenario_and_decision_analysis.ipynb) regenerates these seven files after verifying agreement with [Notebook 04](../notebooks/04_risk_modeling.ipynb).

| CSV | Rows | Scope and purpose |
|---|---:|---|
| [page1_kpi.csv](data/page1_kpi.csv) | 5 | Full-panel indicator values and display labels |
| [page1_pressure_heatmap.csv](data/page1_pressure_heatmap.csv) | 48 | Sector × outcome year; known-label denominators and pressure counts |
| [page1_sector_trend.csv](data/page1_sector_trend.csv) | 52 | Sector × feature year; available-value ratio medians |
| [page1_scatter.csv](data/page1_scatter.csv) | 3,823 | 2021–2022 financial ratios, identifiers and outcome labels |
| [page2_model_comparison.csv](data/page2_model_comparison.csv) | 3 | Persistence, Logistic Regression and Decision Tree metrics |
| [page2_risk_scores.csv](data/page2_risk_scores.csv) | 3,305 | Known-label test rows, scores, stable ranks, baseline and sensitivity tiers |
| [page2_tier_distribution.csv](data/page2_tier_distribution.csv) | 6 | Annual baseline tier counts and shares |

High Review Priority uses dark red (`#8B1E2D`), Medium Review Priority amber (`#D79B28`), and Routine Monitoring blue-gray (`#617D8A`). Pressure is dark red in the scatter; Unknown is neutral gray. Percentages use one decimal place and counts are integers.

For space, some sheet labels shorten Energy / Capital-intensive to Energy, Industrial / Manufacturing to Industrial, and Technology / Software / Electronics to Technology. These are display aliases for the same source sectors, not new groups.

Both PNGs were exported with Tableau's Export Image command. The workbook was saved as a package, closed and reopened locally, and its filters and embedded sources were checked. If the Python exports change, reconnect the seven workbook sources to the updated CSVs in `dashboard/data/`, save the package, and re-export both images. See the [project README](../README.md), [data dictionary](../data_dictionary/variables.md) and [limitations](../methodology/limitations.md) for analytical context.
