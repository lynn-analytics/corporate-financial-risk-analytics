-- Business queries for the corporate financial risk early-warning database.
-- Each query answers a business question, not just a syntax demonstration.

-- 1. Next-year financial-pressure rate by outcome year and sector (known labels only)
SELECT f.fiscal_year + 1 AS outcome_year,
       f.sector,
       COUNT(*)                                   AS known_company_years,
       ROUND(AVG(f.next_year_financial_pressure), 3) AS pressure_rate
FROM financials f
JOIN companies c ON f.cik = c.cik
WHERE f.next_year_financial_pressure IS NOT NULL
GROUP BY f.fiscal_year, f.sector
ORDER BY f.fiscal_year, f.sector;

-- 2. Average operating margin by sector
SELECT f.sector,
       COUNT(*) AS n,
       ROUND(AVG(f.operating_margin), 4) AS avg_operating_margin
FROM financials f
JOIN companies c ON f.cik = c.cik
WHERE f.operating_margin IS NOT NULL
GROUP BY f.sector
ORDER BY avg_operating_margin DESC;

-- 3. Companies with two consecutive years of negative operating cash flow
--    (adjacent fiscal years, verified by year difference = 1)
WITH cfo AS (
    SELECT cik, fiscal_year, operating_cash_flow,
           LAG(operating_cash_flow) OVER (PARTITION BY cik ORDER BY fiscal_year) AS prev_cfo,
           LAG(fiscal_year) OVER (PARTITION BY cik ORDER BY fiscal_year) AS prev_year
    FROM financials
)
SELECT cik, fiscal_year, operating_cash_flow, prev_cfo
FROM cfo
WHERE operating_cash_flow < 0 AND prev_cfo < 0 AND fiscal_year = prev_year + 1
ORDER BY cik, fiscal_year;

-- 4. Most leveraged companies within each sector-year (top by liabilities-to-assets)
SELECT *
FROM (
    SELECT f.sector,
           f.fiscal_year,
           f.cik,
           f.liabilities_to_assets,
           RANK() OVER (PARTITION BY f.sector, f.fiscal_year
                        ORDER BY f.liabilities_to_assets DESC) AS leverage_rank
    FROM financials f
    JOIN companies c ON f.cik = c.cik
    WHERE f.liabilities_to_assets IS NOT NULL
)
WHERE leverage_rank <= 3
ORDER BY sector, fiscal_year, leverage_rank;

-- 5. Complete three-consecutive-year average margin, including the current year.
-- A missing year or margin makes the result NULL; windows do not skip missing data.
WITH margins AS (
    SELECT cik, fiscal_year,
           COUNT(operating_margin) OVER w AS complete_margins,
           MIN(fiscal_year) OVER w AS first_year,
           AVG(operating_margin) OVER w AS mean_margin
    FROM financials
    WINDOW w AS (PARTITION BY cik ORDER BY fiscal_year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
)
SELECT cik, fiscal_year,
       CASE WHEN complete_margins = 3 AND first_year = fiscal_year - 2
            THEN ROUND(mean_margin, 4) END AS rolling_3yr_avg_margin
FROM margins ORDER BY cik, fiscal_year;

-- 6. Complete three-consecutive-year mean of sector-year mean margins.
WITH sector_avg AS (
    SELECT sector, fiscal_year, AVG(operating_margin) AS avg_margin
    FROM financials GROUP BY sector, fiscal_year
), rolling AS (
    SELECT sector, fiscal_year, COUNT(avg_margin) OVER w AS complete_years,
           MIN(fiscal_year) OVER w AS first_year, AVG(avg_margin) OVER w AS mean_margin
    FROM sector_avg
    WINDOW w AS (PARTITION BY sector ORDER BY fiscal_year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
)
SELECT sector, fiscal_year,
       CASE WHEN complete_years = 3 AND first_year = fiscal_year - 2
            THEN ROUND(mean_margin, 4) END AS rolling_3yr_sector_avg_margin
FROM rolling ORDER BY sector, fiscal_year;

-- 7. Companies with the largest year-over-year drop in operating margin
--    (adjacent fiscal years, verified by year difference = 1)
WITH margin_change AS (
    SELECT cik, fiscal_year, operating_margin,
           operating_margin - LAG(operating_margin) OVER (PARTITION BY cik ORDER BY fiscal_year) AS margin_change,
           fiscal_year - LAG(fiscal_year) OVER (PARTITION BY cik ORDER BY fiscal_year) AS year_gap
    FROM financials
)
SELECT cik, fiscal_year, operating_margin, ROUND(margin_change, 4) AS margin_change
FROM margin_change
WHERE margin_change IS NOT NULL AND year_gap = 1
ORDER BY margin_change ASC
LIMIT 20;

-- 8. Contemporaneous annual macro values vs. next-year pressure (association only)
SELECT f.fiscal_year AS feature_year, f.fiscal_year + 1 AS outcome_year,
       f.sector,
       ROUND(AVG(f.next_year_financial_pressure), 3) AS pressure_rate,
       m.fed_funds_rate,
       m.cpi_inflation,
       m.industrial_production_growth
FROM financials f
JOIN companies c ON f.cik = c.cik
JOIN macro_conditions m ON f.fiscal_year = m.year
WHERE f.next_year_financial_pressure IS NOT NULL
GROUP BY f.fiscal_year, f.sector
ORDER BY f.fiscal_year, f.sector;

-- 9. Company-year tier shares within each sector and test feature year
SELECT r.feature_year, f.sector,
       r.risk_tier,
       COUNT(*) AS n_company_years,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY r.feature_year, f.sector), 1) AS pct_of_sector
FROM risk_scores r
JOIN companies c ON r.cik = c.cik
JOIN financials f ON r.cik = f.cik AND r.feature_year = f.fiscal_year
GROUP BY r.feature_year, f.sector, r.risk_tier
ORDER BY r.feature_year, f.sector, r.risk_tier;

-- 10. High-priority review queue (test period), with key risk signals
SELECT r.cik,
       f.company_name,
       f.sector,
       r.feature_year,
       ROUND(r.predicted_score, 4)          AS risk_score,
       f.operating_cash_flow_to_assets,
       f.operating_margin,
       f.liabilities_to_assets
FROM risk_scores r
JOIN companies c ON r.cik = c.cik
JOIN financials f ON r.cik = f.cik AND r.feature_year = f.fiscal_year
WHERE r.risk_tier = 'High Review Priority'
ORDER BY r.feature_year, r.predicted_score DESC, r.cik;

-- 11. Companies whose risk score rises most under the combined scenario
SELECT r.cik,
       f.company_name,
       f.sector,
       r.feature_year,
       r.risk_tier                                        AS baseline_tier,
       ROUND(r.predicted_score, 4)                        AS baseline_score,
       ROUND(r.scenario_score, 4)                         AS scenario_score,
       ROUND(r.scenario_score - r.predicted_score, 4)     AS score_change
FROM risk_scores r
JOIN companies c ON r.cik = c.cik
JOIN financials f ON r.cik = f.cik AND r.feature_year = f.fiscal_year
WHERE r.scenario_score > r.predicted_score
ORDER BY (r.scenario_score - r.predicted_score) DESC, r.feature_year, r.cik
LIMIT 20;

-- 12. Distribution of company-year observations across leverage deciles
--     (NTILE on liabilities-to-assets)
SELECT leverage_decile,
       COUNT(*) AS n_company_years
FROM (
    SELECT cik,
           NTILE(10) OVER (ORDER BY liabilities_to_assets, fiscal_year, cik) AS leverage_decile
    FROM financials
    WHERE liabilities_to_assets IS NOT NULL
)
GROUP BY leverage_decile
ORDER BY leverage_decile;
