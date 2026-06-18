CREATE TABLE IF NOT EXISTS wells (
    well_id TEXT PRIMARY KEY,
    well_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    region TEXT NOT NULL,
    start_date DATE NOT NULL,
    status TEXT NOT NULL,
    depth_m NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS production (
    production_id BIGSERIAL PRIMARY KEY,
    well_id TEXT NOT NULL REFERENCES wells(well_id),
    production_date DATE NOT NULL,
    flow_rate_tpd NUMERIC(12, 3),
    oil_tons NUMERIC(12, 3),
    water_cut_pct NUMERIC(6, 2),
    downtime_hours NUMERIC(6, 2),
    UNIQUE (well_id, production_date)
);

CREATE TABLE IF NOT EXISTS telemetry (
    telemetry_id BIGSERIAL PRIMARY KEY,
    well_id TEXT NOT NULL REFERENCES wells(well_id),
    event_time TIMESTAMP NOT NULL,
    pressure_atm NUMERIC(10, 3),
    temperature_c NUMERIC(10, 3),
    power_kw NUMERIC(10, 3),
    pump_runtime_hours NUMERIC(10, 3),
    energy_kwh NUMERIC(12, 3)
);

CREATE TABLE IF NOT EXISTS well_targets (
    target_id BIGSERIAL PRIMARY KEY,
    well_id TEXT NOT NULL REFERENCES wells(well_id),
    target_date DATE NOT NULL,
    actual_flow_rate_tpd NUMERIC(12, 3) NOT NULL,
    UNIQUE (well_id, target_date)
);

CREATE TABLE IF NOT EXISTS pump_sensors (
    sensor_id BIGSERIAL PRIMARY KEY,
    pump_id TEXT NOT NULL,
    well_id TEXT NOT NULL REFERENCES wells(well_id),
    event_time TIMESTAMP NOT NULL,
    vibration_mm_s NUMERIC(10, 3),
    temperature_c NUMERIC(10, 3),
    current_a NUMERIC(10, 3),
    rpm NUMERIC(10, 3)
);

CREATE TABLE IF NOT EXISTS pump_failures (
    failure_id BIGSERIAL PRIMARY KEY,
    pump_id TEXT NOT NULL,
    well_id TEXT NOT NULL REFERENCES wells(well_id),
    failure_time TIMESTAMP NOT NULL,
    failure_type TEXT NOT NULL,
    repair_hours NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id BIGSERIAL PRIMARY KEY,
    delivery_date DATE NOT NULL,
    route TEXT NOT NULL,
    driver_id TEXT NOT NULL,
    volume_tons NUMERIC(12, 3) NOT NULL,
    distance_km NUMERIC(12, 3) NOT NULL,
    cost_rub NUMERIC(14, 2) NOT NULL,
    delay_hours NUMERIC(10, 3) NOT NULL,
    weather TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_production_date ON production(production_date);
CREATE INDEX IF NOT EXISTS idx_production_well ON production(well_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry(event_time);
CREATE INDEX IF NOT EXISTS idx_telemetry_well ON telemetry(well_id);
CREATE INDEX IF NOT EXISTS idx_pump_sensors_time ON pump_sensors(event_time);
CREATE INDEX IF NOT EXISTS idx_deliveries_date ON deliveries(delivery_date);
