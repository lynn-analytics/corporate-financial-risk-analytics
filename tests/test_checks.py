"""Key data, leakage, ranking and published-result checks."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
from analysis_helpers import (FEATURES, TIERS, assign_tiers, build_target,
                              capacity_metrics, prepare, ranking, read_panel)


class RuleChecks(unittest.TestCase):
    def test_target_requires_same_company_and_adjacent_year(self):
        frame = pd.DataFrame({
            "cik": ["0000000001"] * 3 + ["0000000002"] * 2,
            "fiscal_year": [2018, 2019, 2021, 2018, 2019],
            "revenue": [100, 80, 70, 100, 80], "total_assets": [100] * 5,
            "operating_income": [10, -10, -10, 10, np.nan],
            "operating_cash_flow": [10, -10, -10, 10, -10]})
        result = build_target(frame).next_year_financial_pressure
        self.assertEqual(result.iloc[0], 1)
        self.assertTrue(result.iloc[1:].isna().all())

    def test_preprocessing_does_not_learn_from_future(self):
        frame = read_panel()
        parts, _, prep = prepare(frame)
        altered = frame.copy()
        future = altered.fiscal_year.ge(2019)
        altered.loc[future, FEATURES] = 1e20
        altered.loc[future, "sector"] = "Unseen future sector"
        changed, _, new_prep = prepare(altered)
        for name in ("lo", "hi", "med"):
            pd.testing.assert_series_equal(prep[name], new_prep[name])
        self.assertEqual(prep["sectors"], new_prep["sectors"])
        pd.testing.assert_frame_equal(parts[0][0], changed[0][0])

    def test_ties_do_not_depend_on_input_order(self):
        frame = pd.DataFrame({"cik": [f"{i:010d}" for i in range(40)],
                              "feature_year": [2021] * 20 + [2022] * 20,
                              "predicted_score": [0.5] * 40,
                              "actual_label": [0, 1] * 20})
        shuffled = frame.sample(frac=1, random_state=32)
        pd.testing.assert_frame_equal(ranking(frame), ranking(shuffled))
        pd.testing.assert_series_equal(assign_tiers(frame), assign_tiers(shuffled).reindex(frame.index))
        self.assertEqual(capacity_metrics(frame), capacity_metrics(shuffled))
        self.assertEqual(list(frame.loc[assign_tiers(frame).eq(TIERS[0]), "cik"]),
                         [f"{i:010d}" for i in (0, 1, 20, 21)])

    def test_annual_queue_is_reproducible_and_matches_capacity(self):
        scores = pd.read_csv(ROOT / "data/processed/model_scores.csv", dtype={"cik": str})
        pd.testing.assert_series_equal(scores.risk_tier, assign_tiers(scores), check_names=False)
        for _, group in scores.groupby("feature_year"):
            self.assertEqual(group.risk_tier.eq(TIERS[0]).sum(), int(np.ceil(len(group) * 0.10)))
            self.assertEqual(group.risk_tier.ne(TIERS[2]).sum(), int(np.ceil(len(group) * 0.15)))
        shuffled = scores.sample(frac=1, random_state=4)
        pd.testing.assert_series_equal(assign_tiers(scores), assign_tiers(shuffled).reindex(scores.index))

    def test_seven_tableau_exports(self):
        required = {
            "page1_kpi.csv": {"metric", "value", "display_value"},
            "page1_pressure_heatmap.csv": {"sector", "outcome_year", "pressure_rate", "known_company_years"},
            "page1_sector_trend.csv": {"sector", "feature_year", "operating_margin"},
            "page1_scatter.csv": {"cik", "feature_year", "outcome_year", "outcome_label"},
            "page2_model_comparison.csv": {"model", "recall_at_15", "precision_at_15"},
            "page2_risk_scores.csv": {"cik", "feature_year", "risk_tier", "predicted_score", "operating_margin", "operating_cash_flow_to_assets", "liabilities_to_assets"},
            "page2_tier_distribution.csv": {"feature_year", "risk_tier", "n_company_years", "share"},
        }
        directory = ROOT / "dashboard/data"
        self.assertEqual({p.name for p in directory.glob("*.csv")}, set(required))
        for name, fields in required.items():
            frame = pd.read_csv(directory / name, dtype={"cik": str})
            self.assertFalse(frame.empty)
            self.assertTrue(fields.issubset(frame.columns))
            self.assertFalse(np.isinf(frame.select_dtypes("number")).any().any())
            if "cik" in frame:
                self.assertTrue(frame.cik.str.fullmatch(r"\d{10}").all())
            if "risk_tier" in frame:
                self.assertTrue(frame.risk_tier.isin(TIERS).all())
        heat = pd.read_csv(directory / "page1_pressure_heatmap.csv")
        self.assertTrue(heat.pressure_rate.between(0, 1).all())
        self.assertFalse(heat.outcome_year.eq(2025).any())
        self.assertEqual(int(heat.known_company_years.sum()), int(read_panel().next_year_financial_pressure.notna().sum()))
        scatter = pd.read_csv(directory / "page1_scatter.csv")
        self.assertTrue(scatter.loc[scatter.next_year_financial_pressure.isna(), "outcome_label"].eq("Unknown").all())

    def test_readme_results_match_exports(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        panel = read_panel()
        self.assertIn(f"{panel.cik.nunique():,}", readme)
        self.assertIn(f"{len(panel):,}", readme)
        comparison = pd.read_csv(ROOT / "dashboard/data/page2_model_comparison.csv")
        for row in comparison.itertuples():
            expected = f"| {row.model} | {row.pr_auc:.1%} | {row.roc_auc:.1%} | {row.precision:.1%} | {row.recall:.1%} | {row.recall_at_15:.1%} | {row.precision_at_15:.1%} |"
            self.assertIn(expected, readme)


if __name__ == "__main__":
    unittest.main()
