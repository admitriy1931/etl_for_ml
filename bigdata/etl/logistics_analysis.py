from __future__ import annotations

import json

import pandas as pd

from common import export_partitioned, get_engine, read_table, write_table


def main() -> None:
    engine = get_engine()
    deliveries = read_table(engine, "deliveries")
    deliveries["delivery_date"] = pd.to_datetime(deliveries["delivery_date"])
    deliveries["cost_per_km"] = deliveries["cost_rub"] / deliveries["distance_km"]
    deliveries["is_delayed"] = (deliveries["delay_hours"] > 2).astype(int)

    delay_weather = (
        deliveries.groupby("weather", as_index=False)
        .agg(avg_delay_hours=("delay_hours", "mean"), delayed_share=("is_delayed", "mean"), deliveries_count=("delivery_id", "count"))
        .sort_values("avg_delay_hours", ascending=False)
    )
    cost_distance = (
        deliveries.groupby("route", as_index=False)
        .agg(avg_distance_km=("distance_km", "mean"), avg_cost_rub=("cost_rub", "mean"), avg_cost_per_km=("cost_per_km", "mean"), deliveries_count=("delivery_id", "count"))
        .sort_values("avg_cost_per_km")
    )
    driver_kpi = (
        deliveries.groupby("driver_id", as_index=False)
        .agg(avg_delay_hours=("delay_hours", "mean"), delayed_share=("is_delayed", "mean"), avg_cost_per_km=("cost_per_km", "mean"), total_volume_tons=("volume_tons", "sum"), deliveries_count=("delivery_id", "count"))
        .sort_values(["delayed_share", "avg_cost_per_km"])
    )
    route_optimization = cost_distance.copy()
    route_optimization["recommendation"] = route_optimization["avg_cost_per_km"].rank(method="dense").astype(int)

    marts = {
        "mart_delivery_delay_weather": delay_weather,
        "mart_delivery_cost_distance": cost_distance,
        "mart_driver_kpi": driver_kpi,
        "mart_route_optimization": route_optimization,
    }
    for table_name, df in marts.items():
        write_table(engine, df, table_name)
        export_partitioned(df, f"processed/{table_name}", None)
    export_partitioned(deliveries, "processed/deliveries_enriched", "delivery_date")

    print(json.dumps({"status": "ok", "tables": list(marts.keys())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
