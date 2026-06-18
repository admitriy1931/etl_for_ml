from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

from common import ARTIFACTS_DIR, export_partitioned, get_engine, read_table, write_table


FEATURE_COLUMNS = ["avg_pressure_atm", "avg_temperature_c", "avg_power_kw", "pump_runtime_hours"]
TARGET_COLUMN = "actual_flow_rate_tpd"


def prepare_dataset(engine) -> pd.DataFrame:
    telemetry = read_table(engine, "telemetry")
    targets = read_table(engine, "well_targets")
    telemetry["event_time"] = pd.to_datetime(telemetry["event_time"])
    telemetry["target_date"] = telemetry["event_time"].dt.date
    targets["target_date"] = pd.to_datetime(targets["target_date"]).dt.date

    telemetry_daily = (
        telemetry.groupby(["well_id", "target_date"], as_index=False)
        .agg(
            avg_pressure_atm=("pressure_atm", "mean"),
            avg_temperature_c=("temperature_c", "mean"),
            avg_power_kw=("power_kw", "mean"),
            pump_runtime_hours=("pump_runtime_hours", "sum"),
        )
    )
    dataset = targets.merge(telemetry_daily, on=["well_id", "target_date"], how="inner")
    dataset = dataset.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN]).copy()
    return dataset


def train_and_predict(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_df, test_df = train_test_split(dataset, test_size=0.25, random_state=42)
    models = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=80, random_state=42, min_samples_leaf=3),
    }

    metric_rows = []
    best_model_name = None
    best_model = None
    best_rmse = float("inf")
    for model_name, model in models.items():
        model.fit(train_df[FEATURE_COLUMNS], train_df[TARGET_COLUMN])
        pred = model.predict(test_df[FEATURE_COLUMNS])
        mae = mean_absolute_error(test_df[TARGET_COLUMN], pred)
        rmse = float(np.sqrt(mean_squared_error(test_df[TARGET_COLUMN], pred)))
        metric_rows.append({"model_name": model_name, "mae": mae, "rmse": rmse, "rows_train": len(train_df), "rows_test": len(test_df)})
        if rmse < best_rmse:
            best_rmse = rmse
            best_model_name = model_name
            best_model = model

    assert best_model is not None and best_model_name is not None
    predictions = dataset.copy()
    predictions["predicted_flow_rate_tpd"] = best_model.predict(predictions[FEATURE_COLUMNS])
    predictions["absolute_error"] = (predictions[TARGET_COLUMN] - predictions["predicted_flow_rate_tpd"]).abs()
    predictions["model_name"] = best_model_name
    predictions["target_date"] = pd.to_datetime(predictions["target_date"])

    metrics = pd.DataFrame(metric_rows).sort_values("rmse").reset_index(drop=True)
    metrics["created_at"] = datetime.now(timezone.utc).isoformat()
    return predictions, metrics


def main() -> None:
    engine = get_engine()
    dataset = prepare_dataset(engine)
    predictions, metrics = train_and_predict(dataset)
    write_table(engine, predictions, "mart_flow_predictions")
    write_table(engine, metrics, "ml_flow_metrics")
    export_partitioned(predictions, "processed/mart_flow_predictions", "target_date")
    export_partitioned(metrics, "processed/ml_flow_metrics", None)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "flow_model_metrics.json").write_text(metrics.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "best_model": metrics.iloc[0]["model_name"], "rmse": float(metrics.iloc[0]["rmse"]), "mae": float(metrics.iloc[0]["mae"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
