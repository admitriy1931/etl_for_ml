# Superset dashboard guide

Подключение базы данных в Superset:

```text
postgresql+psycopg2://etl_user:etl_password@postgres:5432/oil_analytics
```

## Дашборд 1. Аналитика добычи

| График | Dataset / SQL table | Тип визуализации | Поля |
|---|---|---|---|
| Добыча по времени | `mart_production_daily` | Line chart | X: `production_date`, Y: `total_oil_tons` |
| Топ скважин | `mart_well_kpi` | Bar chart | X: `well_name`, Y: `avg_flow_rate_tpd`, сортировка DESC |
| Давление vs дебит | `mart_pressure_flow_heatmap` | Heatmap | X: `pressure_bin`, Y: `temperature_bin`, metric: `avg_flow_rate_tpd` |

## Дашборд 2. Прогноз дебита

| График | Dataset / SQL table | Тип визуализации | Поля |
|---|---|---|---|
| Actual vs Predicted | `mart_flow_predictions` | Line chart | X: `target_date`, Y: `actual_flow_rate_tpd`, `predicted_flow_rate_tpd` |
| Ошибка модели по времени | `mart_flow_predictions` | Line chart | X: `target_date`, Y: `absolute_error` |
| Метрики модели | `ml_flow_metrics` | Table | `model_name`, `mae`, `rmse`, `rows_train`, `rows_test` |

## Дашборд 3. Аномалии и отказ оборудования

| График | Dataset / SQL table | Тип визуализации | Поля |
|---|---|---|---|
| Аномалии по времени | `mart_pump_anomalies` | Time-series scatter | X: `event_time`, Y: `vibration_mm_s`, group: `pump_id` |
| Рост вибрации перед отказом | `mart_pump_risk` + фильтр по `failure_within_7d` | Line chart | X: `event_time`, Y: `risk_score`, group: `pump_id` |
| Risk score по насосам | `mart_pump_risk` | Bar chart | X: `pump_id`, Y: max(`risk_score`) |

## Дашборд 4. Логистика и поставки

| График | Dataset / SQL table | Тип визуализации | Поля |
|---|---|---|---|
| Delay vs Weather | `mart_delivery_delay_weather` | Bar chart | X: `weather`, Y: `avg_delay_hours` |
| Cost vs Distance | `mart_delivery_cost_distance` | Scatter / Bar chart | X: `avg_distance_km`, Y: `avg_cost_rub`, group: `route` |
| KPI по водителям | `mart_driver_kpi` | Table / Bar chart | `driver_id`, `delayed_share`, `avg_cost_per_km`, `deliveries_count` |
