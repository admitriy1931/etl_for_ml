-- Superset SQL Lab helper queries

SELECT production_date, total_oil_tons, avg_flow_rate_tpd
FROM mart_production_daily
ORDER BY production_date;

SELECT well_name, avg_flow_rate_tpd, downtime_pct, total_oil_tons
FROM mart_well_kpi
ORDER BY avg_flow_rate_tpd DESC;

SELECT pressure_bin, temperature_bin, avg_flow_rate_tpd, observations
FROM mart_pressure_flow_heatmap;

SELECT target_date, well_id, actual_flow_rate_tpd, predicted_flow_rate_tpd, absolute_error
FROM mart_flow_predictions
ORDER BY target_date, well_id;

SELECT event_time, pump_id, vibration_mm_s, temperature_c, current_a, rpm, risk_score
FROM mart_pump_anomalies
ORDER BY event_time;

SELECT weather, avg_delay_hours, delayed_share, deliveries_count
FROM mart_delivery_delay_weather
ORDER BY avg_delay_hours DESC;

SELECT driver_id, delayed_share, avg_cost_per_km, total_volume_tons, deliveries_count
FROM mart_driver_kpi
ORDER BY delayed_share, avg_cost_per_km;
