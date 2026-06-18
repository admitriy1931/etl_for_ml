import os

c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.authenticator_class = "dummyauthenticator.DummyAuthenticator"
c.DummyAuthenticator.password = os.getenv("JUPYTERHUB_PASSWORD", "student")
c.Authenticator.allowed_users = {os.getenv("JUPYTERHUB_USER", "student")}
c.Spawner.default_url = "/lab"
c.Spawner.notebook_dir = "/home/project"
c.Spawner.environment = {
    "POSTGRES_DB": os.getenv("POSTGRES_DB", "oil_analytics"),
    "POSTGRES_USER": os.getenv("POSTGRES_USER", "etl_user"),
    "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "etl_password"),
    "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "postgres"),
    "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
    "MINIO_ENDPOINT": os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "MINIO_BUCKET": os.getenv("MINIO_BUCKET", "oil-data"),
    "MINIO_ACCESS_KEY": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    "MINIO_SECRET_KEY": os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
}
