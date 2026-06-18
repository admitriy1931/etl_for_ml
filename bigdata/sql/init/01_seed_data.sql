INSERT INTO wells (well_id, well_name, field_name, region, start_date, status, depth_m)
SELECT
    'well_' || lpad(gs::text, 3, '0') AS well_id,
    'Скважина ' || gs AS well_name,
    CASE WHEN gs <= 4 THEN 'Северное' WHEN gs <= 8 THEN 'Южное' ELSE 'Восточное' END AS field_name,
    CASE WHEN gs % 3 = 0 THEN 'ХМАО' WHEN gs % 3 = 1 THEN 'ЯНАО' ELSE 'Татарстан' END AS region,
    DATE '2021-01-01' + (gs * 17) AS start_date,
    CASE WHEN gs IN (11, 12) THEN 'maintenance' ELSE 'active' END AS status,
    1800 + gs * 95 AS depth_m
FROM generate_series(1, 12) gs
ON CONFLICT (well_id) DO NOTHING;

INSERT INTO production (well_id, production_date, flow_rate_tpd, oil_tons, water_cut_pct, downtime_hours)
SELECT
    w.well_id,
    d::date AS production_date,
    ROUND((70 + (substring(w.well_id from 6)::int * 4) + 10 * sin(extract(doy from d) / 8.0) + (random() * 8 - 4))::numeric, 3) AS flow_rate_tpd,
    ROUND(((70 + (substring(w.well_id from 6)::int * 4) + 10 * sin(extract(doy from d) / 8.0) + (random() * 8 - 4)) * (0.88 + random() * 0.08))::numeric, 3) AS oil_tons,
    ROUND((18 + substring(w.well_id from 6)::int * 1.4 + random() * 6)::numeric, 2) AS water_cut_pct,
    ROUND((CASE WHEN random() < 0.08 THEN 4 + random() * 10 ELSE random() * 1.2 END)::numeric, 2) AS downtime_hours
FROM wells w
CROSS JOIN generate_series(DATE '2026-01-01', DATE '2026-04-30', INTERVAL '1 day') d
ON CONFLICT (well_id, production_date) DO NOTHING;

-- Добавлены контролируемые NULL и выбросы для обязательной очистки данных в pandas.
UPDATE production SET water_cut_pct = NULL WHERE production_id % 97 = 0;
UPDATE production SET flow_rate_tpd = flow_rate_tpd * 4 WHERE production_id % 173 = 0;

INSERT INTO telemetry (well_id, event_time, pressure_atm, temperature_c, power_kw, pump_runtime_hours, energy_kwh)
SELECT
    w.well_id,
    ts AS event_time,
    ROUND((95 + substring(w.well_id from 6)::int * 2.2 + 6 * sin(extract(epoch from ts) / 86400 / 4.0) + (random() * 5 - 2.5))::numeric, 3) AS pressure_atm,
    ROUND((54 + substring(w.well_id from 6)::int * 0.9 + 4 * cos(extract(epoch from ts) / 86400 / 7.0) + (random() * 3 - 1.5))::numeric, 3) AS temperature_c,
    ROUND((34 + substring(w.well_id from 6)::int * 1.8 + random() * 7)::numeric, 3) AS power_kw,
    ROUND((5.5 + random() * 0.5)::numeric, 3) AS pump_runtime_hours,
    ROUND(((34 + substring(w.well_id from 6)::int * 1.8 + random() * 7) * (5.5 + random() * 0.5))::numeric, 3) AS energy_kwh
FROM wells w
CROSS JOIN generate_series(TIMESTAMP '2026-01-01 00:00:00', TIMESTAMP '2026-04-30 18:00:00', INTERVAL '6 hour') ts;

UPDATE telemetry SET pressure_atm = NULL WHERE telemetry_id % 151 = 0;
UPDATE telemetry SET temperature_c = temperature_c * 2 WHERE telemetry_id % 211 = 0;

INSERT INTO well_targets (well_id, target_date, actual_flow_rate_tpd)
SELECT well_id, production_date, COALESCE(flow_rate_tpd, oil_tons) AS actual_flow_rate_tpd
FROM production
ON CONFLICT (well_id, target_date) DO NOTHING;

INSERT INTO pump_sensors (pump_id, well_id, event_time, vibration_mm_s, temperature_c, current_a, rpm)
SELECT
    'pump_' || right(w.well_id, 3) AS pump_id,
    w.well_id,
    ts AS event_time,
    ROUND((2.5 + substring(w.well_id from 6)::int * 0.08 + random() * 0.7 + CASE WHEN extract(day from ts)::int IN (12, 13) THEN 3.2 ELSE 0 END)::numeric, 3) AS vibration_mm_s,
    ROUND((58 + random() * 8 + CASE WHEN extract(day from ts)::int IN (12, 13) THEN 12 ELSE 0 END)::numeric, 3) AS temperature_c,
    ROUND((42 + random() * 6 + CASE WHEN extract(day from ts)::int IN (12, 13) THEN 8 ELSE 0 END)::numeric, 3) AS current_a,
    ROUND((2860 + random() * 160 - CASE WHEN extract(day from ts)::int IN (12, 13) THEN 280 ELSE 0 END)::numeric, 3) AS rpm
FROM wells w
CROSS JOIN generate_series(TIMESTAMP '2026-01-01 00:00:00', TIMESTAMP '2026-04-30 23:00:00', INTERVAL '12 hour') ts;

INSERT INTO pump_failures (pump_id, well_id, failure_time, failure_type, repair_hours)
SELECT 'pump_003', 'well_003', TIMESTAMP '2026-02-14 09:00:00', 'vibration_overlimit', 7.5
UNION ALL SELECT 'pump_007', 'well_007', TIMESTAMP '2026-03-14 11:00:00', 'overheat', 5.0
UNION ALL SELECT 'pump_010', 'well_010', TIMESTAMP '2026-04-14 08:30:00', 'current_spike', 6.0
ON CONFLICT DO NOTHING;

INSERT INTO deliveries (delivery_date, route, driver_id, volume_tons, distance_km, cost_rub, delay_hours, weather)
SELECT
    d::date AS delivery_date,
    CASE WHEN gs % 4 = 0 THEN 'Северный склад — НПЗ' WHEN gs % 4 = 1 THEN 'Южный куст — терминал' WHEN gs % 4 = 2 THEN 'Восточный куст — НПЗ' ELSE 'ЦПС — терминал' END AS route,
    'driver_' || lpad(((gs % 8) + 1)::text, 2, '0') AS driver_id,
    ROUND((90 + random() * 160)::numeric, 3) AS volume_tons,
    ROUND((120 + random() * 520)::numeric, 3) AS distance_km,
    ROUND(((120 + random() * 520) * (120 + random() * 35) + 4000 + random() * 3000)::numeric, 2) AS cost_rub,
    ROUND((CASE WHEN gs % 9 = 0 THEN 5 + random() * 9 WHEN gs % 5 = 0 THEN 2 + random() * 4 ELSE random() * 1.5 END)::numeric, 3) AS delay_hours,
    CASE WHEN gs % 9 = 0 THEN 'snow' WHEN gs % 5 = 0 THEN 'rain' WHEN gs % 7 = 0 THEN 'fog' ELSE 'clear' END AS weather
FROM generate_series(DATE '2026-01-01', DATE '2026-04-30', INTERVAL '1 day') d
CROSS JOIN generate_series(1, 4) gs;
