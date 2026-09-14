# Data Dictionary — `company_year_panel.csv`

One row = one company × one fiscal year.

## Identifiers (excluded from model features)

| Column | Description |
|--------|-------------|
| `cik` | SEC Central Index Key: ten-character zero-padded text, excluded from model features |
| `company_name` | Registrant name as filed |
| `sic` | Standard Industrial Classification code |
| `sector` | Simplified sector group (see below) |
| `fiscal_year` | Fiscal year of the reported period |

## Raw financial fields (from SEC 10-K filings, USD)

| Column | Description |
|--------|-------------|
| `revenue` | Total revenue |
| `operating_income` | Operating income (loss) |
| `net_income` | Net income (loss) |
| `total_assets` | Total assets (year-end) |
| `total_liabilities` | Total liabilities (year-end) |
| `current_assets` | Current assets (year-end) |
| `current_liabilities` | Current liabilities (year-end) |
| `cash_and_equivalents` | Cash and cash equivalents (year-end) |
| `operating_cash_flow` | Net cash from operating activities (full year) |
| `capex` | Capital expenditure (full year) |

## Engineered financial features

| Column | Formula | Concept |
|--------|---------|---------|
| `log_assets` | ln(1 + total_assets) | Size |
| `log_revenue` | ln(1 + revenue) | Size |
| `revenue_growth` | revenue / prior revenue − 1 | Growth |
| `change_in_revenue_growth` | revenue_growth − prior revenue_growth | Growth change |
| `operating_margin` | operating_income / revenue | Profitability |
| `net_margin` | net_income / revenue | Profitability |
| `change_in_operating_margin` | operating_margin − prior operating_margin | Profitability trend |
| `operating_cash_flow_to_assets` | operating_cash_flow / total_assets | Cash flow |
| `cash_to_assets` | cash_and_equivalents / total_assets | Liquidity |
| `liabilities_to_assets` | total_liabilities / total_assets | Leverage |
| `current_ratio` | current_assets / current_liabilities | Liquidity |
| `asset_turnover` | revenue / total_assets | Efficiency |
| `capex_to_revenue` | capex / revenue | Investment |
| `three_year_operating_margin_volatility` | Population SD (ddof=0) of current and up to two preceding consecutive years; at least two complete margins; missing if any value in that window is missing | Volatility |

## Macro variables (contemporaneous annual values, not lagged)

| Column | Description |
|--------|-------------|
| `fed_funds_rate` | Federal Funds Effective Rate (annual average) |
| `cpi_inflation` | Percent change between adjacent calendar-year average CPI levels |
| `industrial_production_growth` | Percent change between adjacent calendar-year average production levels |

## Target

| Column | Description |
|--------|-------------|
| `next_year_financial_pressure` | 1 if at least two of three signals in the same company’s actual next year; 0 if complete and fewer than two; blank if unknown |

## Sector mapping

Four simplified groups derived from SIC:

| Sector | SIC ranges (indicative) |
|--------|------------------------|
| Industrial / Manufacturing | 15–17 and 20–39, except 35–36 |
| Energy / Capital-intensive | 10–14, 49 (selected) |
| Consumer / Retail | 50–59 |
| Technology / Software / Electronics | 35–36, 73 |

Financials (banks, insurers, REITs) are excluded.

## Data conventions

`fiscal_year` and `feature_year` identify model-input years; `outcome_year` is the actual following fiscal year for known targets. All growth/change fields require the same company's adjacent year; growth change requires two adjacent growth rates. Sector reflects each company-year's SIC, so the same company may change groups.

Financial amounts are USD, with annual flows and year-end stocks. Financial ratios and model metrics are decimal fractions; multiply by 100 only for display. FRED interest rates and growth rates are already in percent units (2 means 2%). CIK and SIC are identifiers, not continuous measurements. Blank financial ratios remain missing in the published panel; the model alone imputes using training medians. Percentile clipping applies to numeric model features, not target construction.

## Model and dashboard exports

`model_scores.csv` has CIK, feature year, actual label, predicted score, baseline risk tier and combined sensitivity score. Scores range from 0 to 1 and are screening/ranking signals, not default probabilities.

`page2_risk_scores.csv` adds same-year company name, sector, ratios, outcome year, sensitivity tier and within-year review rank. `page2_model_comparison.csv` uses average precision for `pr_auc`, threshold 0.5 for standard metrics, and pooled counts from annual top-k queues for capacity metrics. `page2_tier_distribution.csv` counts company-years by feature year; `share` is within that year.

`page1_pressure_heatmap.csv` contains known-label denominators and pressure cases by sector/outcome year. `page1_scatter.csv` covers test feature years and retains Unknown outcome labels explicitly. KPI values and sector trend medians use the raw processed panel; KPI cards are global summaries. [Dashboard source guide](../dashboard/README.md).
