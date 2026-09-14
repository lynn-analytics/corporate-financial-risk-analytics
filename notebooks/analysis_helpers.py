"""Small shared functions for the five notebooks and rule checks."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
    "log_assets", "log_revenue", "revenue_growth", "change_in_revenue_growth",
    "operating_margin", "net_margin", "change_in_operating_margin",
    "operating_cash_flow_to_assets", "cash_to_assets", "liabilities_to_assets",
    "current_ratio", "asset_turnover", "capex_to_revenue",
    "three_year_operating_margin_volatility", "fed_funds_rate", "cpi_inflation",
    "industrial_production_growth",
]
TRAIN_YEARS, VAL_YEARS, TEST_YEARS = (2014, 2018), (2019, 2020), (2021, 2022)
TIERS = ["High Review Priority", "Medium Review Priority", "Routine Monitoring"]


def read_panel():
    return pd.read_csv(ROOT / "data/processed/company_year_panel.csv", dtype={"cik": str, "sic": str})


def build_target(frame):
    """Use only the same company's actual t+1; incomplete signals stay unknown."""
    df = frame.sort_values(["cik", "fiscal_year"]).reset_index(drop=True).copy()
    if df.duplicated(["cik", "fiscal_year"]).any():
        raise ValueError("Duplicate company-year observations")
    cols = ["fiscal_year", "revenue", "operating_income", "operating_cash_flow", "total_assets"]
    nxt = df.groupby("cik")[cols].shift(-1)
    valid = (nxt.fiscal_year.eq(df.fiscal_year + 1)
             & np.isfinite(nxt[cols]).all(axis=1)
             & nxt.revenue.gt(0) & nxt.total_assets.gt(0)
             & np.isfinite(df.revenue) & df.revenue.gt(0))
    signals = ((nxt.operating_income / nxt.revenue < 0).astype(int)
               + (nxt.operating_cash_flow / nxt.total_assets < 0).astype(int)
               + (nxt.revenue / df.revenue - 1 <= -0.10).astype(int))
    df["next_year_financial_pressure"] = (signals >= 2).astype(float).where(valid)
    return df


def rolling_margin_std(frame):
    """Population SD of current and up to two preceding consecutive years; min 2."""
    result = pd.Series(np.nan, index=frame.index)
    for _, group in frame.sort_values(["cik", "fiscal_year"]).groupby("cik"):
        years = group.fiscal_year.to_numpy()
        margins = group.operating_margin.to_numpy()
        for i, idx in enumerate(group.index):
            start = i
            while start > max(0, i - 2) and years[start - 1] == years[start] - 1:
                start -= 1
            values = margins[start:i + 1]
            if len(values) >= 2 and np.isfinite(values).all():
                result.loc[idx] = np.std(values, ddof=0)
    return result


def fit_preprocessor(train):
    """Learn continuous bounds, clipped medians and sector vocabulary from train."""
    numeric = train[FEATURES].replace([np.inf, -np.inf], np.nan)
    lo, hi = numeric.quantile(0.01), numeric.quantile(0.99)
    med = numeric.clip(lo, hi, axis=1).median()
    if med.isna().any():
        raise ValueError("A training feature has no usable values")
    return {"lo": lo, "hi": hi, "med": med,
            "sectors": sorted(train.sector.dropna().unique())}


def transform(frame, prep):
    x = frame[FEATURES].replace([np.inf, -np.inf], np.nan)
    x = x.clip(prep["lo"], prep["hi"], axis=1).fillna(prep["med"])
    # First training category is the reference; unseen sectors use that encoding.
    for sector in prep["sectors"][1:]:
        x["sector_" + sector] = frame.sector.eq(sector).astype(float)
    return x


def prepare(panel):
    known = panel.loc[panel.next_year_financial_pressure.notna()].copy()
    frames = [known.loc[known.fiscal_year.between(*years)].sort_values(
        ["fiscal_year", "cik"]).reset_index(drop=True)
        for years in (TRAIN_YEARS, VAL_YEARS, TEST_YEARS)]
    prep = fit_preprocessor(frames[0])
    parts = [(transform(f, prep), f.next_year_financial_pressure.astype(int)) for f in frames]
    return parts, frames, prep


def fit_models(panel):
    parts, frames, prep = prepare(panel)
    (xtr, ytr), (xva, yva), (xte, yte) = parts
    candidates, validation = [], []
    for weight in (None, "balanced"):
        model = make_pipeline(StandardScaler(), LogisticRegression(
            max_iter=1000, random_state=0, class_weight=weight))
        model.fit(xtr, ytr)
        candidates.append(model)
        validation.append(average_precision_score(yva, model.predict_proba(xva)[:, 1]))
    selected = int(validation[1] > validation[0])  # an exact tie keeps unweighted LR
    tree = DecisionTreeClassifier(max_depth=4, min_samples_leaf=50, random_state=0).fit(xtr, ytr)
    return {"parts": parts, "frames": frames, "prep": prep,
            "lr": candidates[selected], "tree": tree, "validation_ap": validation,
            "class_weight": (None, "balanced")[selected]}


def persistence_score(frame):
    # Missing current signals contribute no positive evidence; documented fallback.
    return ((frame.operating_margin.lt(0).astype(int)
             + frame.operating_cash_flow_to_assets.lt(0).astype(int)
             + frame.revenue_growth.le(-0.10).astype(int)) >= 2).astype(float).to_numpy()


def ranking(frame):
    """Deterministic ranking: year ascending, score descending, zero-padded CIK ascending."""
    if frame.duplicated(["feature_year", "cik"]).any():
        raise ValueError("Ranking requires one row per company-year")
    if not np.isfinite(frame.predicted_score).all():
        raise ValueError("Ranking requires finite scores")
    return frame.sort_values(["feature_year", "predicted_score", "cik"],
                             ascending=[True, False, True], kind="mergesort")


def assign_tiers(frame):
    result = pd.Series(TIERS[2], index=frame.index, dtype=object)
    for _, group in ranking(frame).groupby("feature_year", sort=True):
        high = int(np.ceil(len(group) * 0.10))
        review = int(np.ceil(len(group) * 0.15))
        result.loc[group.index[:high]] = TIERS[0]
        result.loc[group.index[high:review]] = TIERS[1]
    return result


def capacity_metrics(frame, capacity=0.15):
    reviewed = pd.concat([g.head(int(np.ceil(len(g) * capacity)))
                         for _, g in ranking(frame).groupby("feature_year")])
    tp, positives = reviewed.actual_label.sum(), frame.actual_label.sum()
    return {"recall": float(tp / positives) if positives else 0.0,
            "precision": float(tp / len(reviewed)), "reviewed": len(reviewed)}


def metrics(y, score):
    prediction = (np.asarray(score) >= 0.5).astype(int)
    return {"accuracy": accuracy_score(y, prediction),
            "precision": precision_score(y, prediction, zero_division=0),
            "recall": recall_score(y, prediction, zero_division=0),
            "f1": f1_score(y, prediction, zero_division=0),
            "roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score)}


def score_table(bundle):
    test = bundle["frames"][2]
    xte, yte = bundle["parts"][2]
    frame = test[["cik", "fiscal_year"]].rename(columns={"fiscal_year": "feature_year"}).copy()
    frame["actual_label"] = yte.to_numpy()
    frame["predicted_score"] = bundle["lr"].predict_proba(xte)[:, 1]
    frame["risk_tier"] = assign_tiers(frame)
    return frame


def model_comparison(bundle):
    xte, yte = bundle["parts"][2]
    base = score_table(bundle)
    scores = {"Majority": np.zeros(len(yte)),
              "Persistence": persistence_score(bundle["frames"][2]),
              "Logistic Regression": base.predicted_score.to_numpy(),
              "Decision Tree": bundle["tree"].predict_proba(xte)[:, 1]}
    rows = []
    for name, score in scores.items():
        row = {"model": name, **metrics(yte, score)}
        for capacity in (0.10, 0.15, 0.20):
            cap = capacity_metrics(base.assign(predicted_score=score), capacity)
            suffix = str(int(capacity * 100))
            row.update({"recall_at_" + suffix: cap["recall"],
                        "precision_at_" + suffix: cap["precision"],
                        "reviewed_at_" + suffix: cap["reviewed"]})
        rows.append(row)
    return pd.DataFrame(rows)
