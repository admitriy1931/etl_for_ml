from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import boto3
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = PROJECT_ROOT / "tmp" / "exports"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def postgres_url() -> str:
    user = os.getenv("POSTGRES_USER", "etl_user")
    password = os.getenv("POSTGRES_PASSWORD", "etl_password")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "oil_analytics")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_engine() -> Engine:
    return create_engine(postgres_url(), pool_pre_ping=True)


def read_table(engine: Engine, table_name: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {table_name}", engine)


def write_table(engine: Engine, df: pd.DataFrame, table_name: str) -> None:
    df.to_sql(table_name, engine, if_exists="replace", index=False, method="multi", chunksize=1000)


def execute_sql(engine: Engine, statements: Iterable[str]) -> None:
    with engine.begin() as conn:
        for statement in statements:
            if statement.strip():
                conn.execute(text(statement))


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
        region_name="us-east-1",
    )


def ensure_bucket(bucket: str) -> None:
    client = get_s3_client()
    existing = [item["Name"] for item in client.list_buckets().get("Buckets", [])]
    if bucket not in existing:
        client.create_bucket(Bucket=bucket)


def upload_file(local_path: Path, s3_key: str, bucket: str | None = None) -> None:
    bucket = bucket or os.getenv("MINIO_BUCKET", "oil-data")
    ensure_bucket(bucket)
    get_s3_client().upload_file(str(local_path), bucket, s3_key)


def export_partitioned(
    df: pd.DataFrame,
    dataset_name: str,
    partition_column: str | None = None,
    file_format: str = "parquet",
) -> list[str]:
    """Save DataFrame to local tmp and upload it to MinIO with date partitioning."""
    bucket = os.getenv("MINIO_BUCKET", "oil-data")
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    uploaded_keys: list[str] = []

    if df.empty:
        return uploaded_keys

    if partition_column and partition_column in df.columns:
        work = df.copy()
        work[partition_column] = pd.to_datetime(work[partition_column]).dt.date
        groups = work.groupby(partition_column, dropna=False)
        for partition_value, part in groups:
            date_value = str(partition_value)
            partition_dir = f"{dataset_name}/{partition_column}={date_value}"
            filename = f"part-00000.{file_format}"
            local_path = TMP_DIR / dataset_name / f"{partition_column}={date_value}" / filename
            local_path.parent.mkdir(parents=True, exist_ok=True)
            _write_dataframe(part, local_path, file_format)
            s3_key = f"{partition_dir}/{filename}"
            upload_file(local_path, s3_key, bucket=bucket)
            uploaded_keys.append(s3_key)
    else:
        local_path = TMP_DIR / dataset_name / f"data.{file_format}"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        _write_dataframe(df, local_path, file_format)
        s3_key = f"{dataset_name}/data.{file_format}"
        upload_file(local_path, s3_key, bucket=bucket)
        uploaded_keys.append(s3_key)

    return uploaded_keys


def _write_dataframe(df: pd.DataFrame, path: Path, file_format: str) -> None:
    if file_format == "parquet":
        df.to_parquet(path, index=False)
    elif file_format == "csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")


def add_indexes(engine: Engine) -> None:
    execute_sql(
        engine,
        [
            "CREATE INDEX IF NOT EXISTS idx_mart_production_daily_date ON mart_production_daily(production_date)",
            "CREATE INDEX IF NOT EXISTS idx_mart_well_kpi_well ON mart_well_kpi(well_id)",
            "CREATE INDEX IF NOT EXISTS idx_mart_flow_predictions_date ON mart_flow_predictions(target_date)",
            "CREATE INDEX IF NOT EXISTS idx_mart_pump_anomalies_time ON mart_pump_anomalies(event_time)",
            "CREATE INDEX IF NOT EXISTS idx_mart_driver_kpi_driver ON mart_driver_kpi(driver_id)",
        ],
    )
