"""Load published CSVs into the ignored local SQLite database."""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def main():
    processed = ROOT / "data/processed"
    panel = pd.read_csv(processed / "company_year_panel.csv", dtype={"cik": str, "sic": str})
    scores = pd.read_csv(processed / "model_scores.csv", dtype={"cik": str})
    if "scenario_score" not in scores:
        raise ValueError("Run Notebook 05 after Notebook 04 to produce scenario_score.")
    for frame in (panel, scores):
        if not frame.cik.str.fullmatch(r"\d{10}").all():
            raise ValueError("CIK must be a ten-character zero-padded string.")
    with sqlite3.connect(processed / "risk.db") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript((ROOT / "sql/create_tables.sql").read_text(encoding="utf-8"))
        # Refresh only the four generated tables; preserve other local content.
        for table in ("risk_scores", "financials", "macro_conditions", "companies"):
            connection.execute(f"DELETE FROM {table}")
        companies = panel.sort_values("fiscal_year").drop_duplicates("cik", keep="last")
        companies[["cik", "company_name", "sic", "sector"]].to_sql("companies", connection, if_exists="append", index=False)
        fields = [row[1] for row in connection.execute("PRAGMA table_info(financials)")]
        panel[fields].to_sql("financials", connection, if_exists="append", index=False)
        columns = ["fiscal_year", "fed_funds_rate", "cpi_inflation", "industrial_production_growth"]
        macro = panel[columns].drop_duplicates()
        if macro.fiscal_year.duplicated().any():
            raise ValueError("Macro values must be identical within each year.")
        macro.rename(columns={"fiscal_year": "year"}).to_sql("macro_conditions", connection, if_exists="append", index=False)
        scores.to_sql("risk_scores", connection, if_exists="append", index=False)
        print("Loaded data/processed/risk.db")
        for table in ("companies", "financials", "macro_conditions", "risk_scores"):
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count:,} rows")

if __name__ == "__main__":
    main()
