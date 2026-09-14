-- Schema for the corporate financial risk early-warning database.
-- Loaded from data/processed/*.csv by sql/load_data.py.

CREATE TABLE IF NOT EXISTS companies (
    cik          TEXT PRIMARY KEY,
    company_name TEXT,
    sic          TEXT,
    sector       TEXT
);

-- One row per company per fiscal year. Contains raw fields, engineered ratios,
-- and the target label.
CREATE TABLE IF NOT EXISTS financials (
    cik                           TEXT,
    fiscal_year                   INTEGER,
    sector                        TEXT,
    company_name                  TEXT,
    sic                           TEXT,
    revenue                       REAL,
    operating_income              REAL,
    net_income                    REAL,
    total_assets                  REAL,
    total_liabilities             REAL,
    current_assets                REAL,
    current_liabilities           REAL,
    cash_and_equivalents          REAL,
    operating_cash_flow           REAL,
    capex                         REAL,
    -- engineered ratios
    log_assets                    REAL,
    revenue_growth                REAL,
    operating_margin              REAL,
    operating_cash_flow_to_assets REAL,
    liabilities_to_assets         REAL,
    current_ratio                 REAL,
    -- target
    next_year_financial_pressure  INTEGER,
    PRIMARY KEY (cik, fiscal_year),
    FOREIGN KEY (cik) REFERENCES companies(cik),
    CHECK (length(cik) = 10),
    CHECK (next_year_financial_pressure IN (0, 1) OR next_year_financial_pressure IS NULL)
);

CREATE TABLE IF NOT EXISTS macro_conditions (
    year                         INTEGER PRIMARY KEY,
    fed_funds_rate               REAL,
    cpi_inflation                REAL,
    industrial_production_growth REAL
);

CREATE TABLE IF NOT EXISTS risk_scores (
    cik             TEXT,
    feature_year    INTEGER,
    actual_label    INTEGER,
    predicted_score REAL,
    risk_tier       TEXT,
    scenario_score  REAL,
    PRIMARY KEY (cik, feature_year),
    FOREIGN KEY (cik, feature_year) REFERENCES financials(cik, fiscal_year),
    CHECK (actual_label IN (0, 1)),
    CHECK (predicted_score BETWEEN 0 AND 1),
    CHECK (scenario_score BETWEEN 0 AND 1),
    CHECK (risk_tier IN ('High Review Priority', 'Medium Review Priority', 'Routine Monitoring'))
);
