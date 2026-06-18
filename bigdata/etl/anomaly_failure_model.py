from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

from common import ARTIFACTS_DIR, export_partitioned, get_engine, read_table, write_table

SENSOR_FEATURES = ["vibration_mm_s", "temperature_c", "current_a", "rpm"]


def add_zscores(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for col in SENSOR_FEATURES:
        mean = result.groupby("pump_id")[col].transform("mean")
        std = result.groupby("pump_id")[col].transform("std").replace(0, np.nan)
        result[f"z_{col}"] = ((result[col] - mean) / std).fillna(0)
    result["is_anomaly"] = (result[[f"z_{col}" for col in SENSOR_FEATURES]].abs() > 3).any(axis=1).astype(int)
    return result


def add_failure_label(sensors: pd.DataFrame, failures: pd.DataFrame) -> pd.DataFrame:
    df = sensors.copy()
    df["failure_within_7d"] = 0
    failures = failures.copy()
    failures["failure_time"] = pd.to_datetime(failures["failure_time"])
    for _, failure in failures.iterrows():
        mask = (
            (df["pump_id"] == failure["pump_id"])
            & (df["event_time"] <= failure["failure_time"])
            & (df["event_time"] >= failure["failure_time"] - pd.Timedelta(days=7))
        )
        df.loc[mask, "failure_within_7d"] = 1
    return df


def train_failure_model(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_cols = SENSOR_FEATURES + [f"z_{col}" for col in SENSOR_FEATURES] + ["is_anomaly"]
    model_df = df.dropna(subset=feature_cols + ["failure_within_7d"]).copy()
    train_df, test_df = train_test_split(model_df, test_size=0.25, random_state=42, stratify=model_df["failure_within_7d"])
    model = RandomForestClassifier(n_estimators=100, random_state=42, min_samples_leaf=3, class_weight="balanced")
    model.fit(train_df[feature_cols], train_df["failure_within_7d"])
    proba = model.predict_proba(model_df[feature_cols])[:, 1]
    model_df["risk_score"] = proba
    test_pred = model.predict(test_df[feature_cols])
    test_proba = model.predict_proba(test_df[feature_cols])[:, 1]
    metrics = pd.DataFrame(
        [
            {
                "model_name": "random_forest_classifier",
                "accuracy": accuracy_score(test_df["failure_within_7d"], test_pred),
                "roc_auc": roc_auc_score(test_df["failure_within_7d"], test_proba) if test_df["failure_within_7d"].nunique() > 1 else None,
                "rows_train": len(train_df),
                "rows_test": len(test_df),
            }
        ]
    )
    return model_df, metrics


def main() -> None:
    engine = get_engine()
    sensors = read_table(engine, "pump_sensors")
    failures = read_table(engine, "pump_failures")
    sensors["event_time"] = pd.to_datetime(sensors["event_time"])
    sensors = add_zscores(sensors)
    sensors = add_failure_label(sensors, failures)
    risk, metrics = train_failure_model(sensors)

    anomalies = risk[risk["is_anomaly"] == 1].copy()
    anomaly_columns = ["pump_id", "well_id", "event_time", "vibration_mm_s", "temperature_c", "current_a", "rpm", "is_anomaly", "failure_within_7d", "risk_score"]
    risk_columns = ["pump_id", "well_id", "event_time", "risk_score", "failure_within_7d", "is_anomaly"]
    write_table(engine, anomalies[anomaly_columns], "mart_pump_anomalies")
    write_table(engine, risk[risk_columns], "mart_pump_risk")
    write_table(engine, metrics, "ml_failure_metrics")

    export_partitioned(anomalies[anomaly_columns].assign(event_date=anomalies["event_time"].dt.date), "processed/mart_pump_anomalies", "event_date")
    export_partitioned(risk[risk_columns].assign(event_date=risk["event_time"].dt.date), "processed/mart_pump_risk", "event_date")
    export_partitioned(metrics, "processed/ml_failure_metrics", None)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "failure_model_metrics.json").write_text(metrics.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "anomalies": int(len(anomalies)), "metrics": metrics.to_dict(orient="records")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
