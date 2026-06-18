from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from common import ARTIFACTS_DIR, add_indexes, export_partitioned, get_engine, read_table, write_table


def clean_production(production: pd.DataFrame) -> pd.DataFrame:
    df = production.copy()
    df["production_date"] = pd.to_datetime(df["production_date"])
    df["water_cut_pct"] = df.groupby("well_id")["water_cut_pct"].transform(lambda s: s.fillna(s.median()))
    df["flow_rate_tpd"] = df.groupby("well_id")["flow_rate_tpd"].transform(lambda s: s.fillna(s.median()))

    def remove_iqr_outliers(group: pd.DataFrame) -> pd.DataFrame:
        q1 = group["flow_rate_tpd"].quantile(0.25)
        q3 = group["flow_rate_tpd"].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return group
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return group[(group["flow_rate_tpd"] >= lower) & (group["flow_rate_tpd"] <= upper)]

    df = df.groupby("well_id", group_keys=False).apply(remove_iqr_outliers).reset_index(drop=True)
    df["downtime_hours"] = df["downtime_hours"].clip(lower=0, upper=24)
    df["oil_tons"] = df["oil_tons"].fillna(df["flow_rate_tpd"] * 0.9)
    return df


def clean_telemetry(telemetry: pd.DataFrame) -> pd.DataFrame:
    df = telemetry.copy()
    df["event_time"] = pd.to_datetime(df["event_time"])
    for col in ["pressure_atm", "temperature_c", "power_kw", "pump_runtime_hours", "energy_kwh"]:
        df[col] = df.groupby("well_id")[col].transform(lambda s: s.fillna(s.median()))
    df = df[(df["temperature_c"].between(20, 130)) & (df["pressure_atm"].between(40, 220))].copy()
    df["pump_runtime_hours"] = df["pump_runtime_hours"].clip(lower=0, upper=24)
    df["event_date"] = df["event_time"].dt.date
    return df


def build_production_marts(production: pd.DataFrame, telemetry: pd.DataFrame, wells: pd.DataFrame) -> dict[str, pd.DataFrame]:
    daily = (
        production.groupby("production_date", as_index=False)
        .agg(
            total_oil_tons=("oil_tons", "sum"),
            avg_flow_rate_tpd=("flow_rate_tpd", "mean"),
            total_downtime_hours=("downtime_hours", "sum"),
            active_wells=("well_id", "nunique"),
        )
        .sort_values("production_date")
    )

    well_kpi = (
        production.groupby("well_id", as_index=False)
        .agg(
            avg_flow_rate_tpd=("flow_rate_tpd", "mean"),
            total_oil_tons=("oil_tons", "sum"),
            downtime_hours=("downtime_hours", "sum"),
            days_count=("production_date", "nunique"),
        )
        .merge(wells[["well_id", "well_name", "field_name", "region", "status"]], on="well_id", how="left")
    )
    well_kpi["downtime_pct"] = well_kpi["downtime_hours"] / (well_kpi["days_count"] * 24) * 100
    well_kpi = well_kpi.sort_values("avg_flow_rate_tpd", ascending=False)

    ranking = well_kpi.copy()
    ranking["rank_by_flow"] = ranking["avg_flow_rate_tpd"].rank(method="dense", ascending=False).astype(int)
    ranking["well_group"] = np.where(ranking["rank_by_flow"] <= 3, "best", np.where(ranking["rank_by_flow"] > len(ranking) - 3, "worst", "middle"))

    telemetry_daily = (
        telemetry.groupby(["well_id", "event_date"], as_index=False)
        .agg(
            avg_pressure_atm=("pressure_atm", "mean"),
            avg_temperature_c=("temperature_c", "mean"),
            avg_power_kw=("power_kw", "mean"),
            pump_runtime_hours=("pump_runtime_hours", "sum"),
            avg_energy_kwh=("energy_kwh", "mean"),
        )
        .rename(columns={"event_date": "production_date"})
    )
    telemetry_daily["production_date"] = pd.to_datetime(telemetry_daily["production_date"])

    features = production.merge(telemetry_daily, on=["well_id", "production_date"], how="left")
    features["downtime_ratio"] = features["downtime_hours"] / 24
    features = features.merge(wells[["well_id", "field_name", "region"]], on="well_id", how="left")

    heatmap = features.copy()
    heatmap["pressure_bin"] = pd.cut(heatmap["avg_pressure_atm"], bins=6).astype(str)
    heatmap["temperature_bin"] = pd.cut(heatmap["avg_temperature_c"], bins=6).astype(str)
    heatmap = (
        heatmap.groupby(["pressure_bin", "temperature_bin"], as_index=False)
        .agg(avg_flow_rate_tpd=("flow_rate_tpd", "mean"), observations=("well_id", "count"))
        .sort_values(["pressure_bin", "temperature_bin"])
    )

    return {
        "clean_production": production,
        "clean_telemetry": telemetry,
        "mart_production_daily": daily,
        "mart_well_kpi": well_kpi,
        "mart_well_ranking": ranking,
        "features_well_daily": features,
        "mart_pressure_flow_heatmap": heatmap,
    }


def main() -> None:
    engine = get_engine()
    wells = read_table(engine, "wells")
    production_raw = read_table(engine, "production")
    telemetry_raw = read_table(engine, "telemetry")
    deliveries_raw = read_table(engine, "deliveries")
    pump_sensors_raw = read_table(engine, "pump_sensors")

    production = clean_production(production_raw)
    telemetry = clean_telemetry(telemetry_raw)
    marts = build_production_marts(production, telemetry, wells)

    uploaded = []
    raw_exports = {
        "raw/wells": (wells, None),
        "raw/production": (production_raw.assign(production_date=pd.to_datetime(production_raw["production_date"])), "production_date"),
        "raw/telemetry": (telemetry_raw.assign(event_date=pd.to_datetime(telemetry_raw["event_time"]).dt.date), "event_date"),
        "raw/deliveries": (deliveries_raw.assign(delivery_date=pd.to_datetime(deliveries_raw["delivery_date"])), "delivery_date"),
        "raw/pump_sensors": (pump_sensors_raw.assign(event_date=pd.to_datetime(pump_sensors_raw["event_time"]).dt.date), "event_date"),
    }
    for dataset_name, (df, partition_col) in raw_exports.items():
        uploaded.extend(export_partitioned(df, dataset_name, partition_col, file_format="parquet"))

    for table_name, df in marts.items():
        write_table(engine, df, table_name)
        partition_col = None
        if "production_date" in df.columns:
            partition_col = "production_date"
        elif "event_date" in df.columns:
            partition_col = "event_date"
        uploaded.extend(export_partitioned(df, f"processed/{table_name}", partition_col, file_format="parquet"))

    add_indexes(engine)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_objects": uploaded,
        "tables_written_to_postgres": list(marts.keys()),
    }
    (ARTIFACTS_DIR / "minio_export_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
