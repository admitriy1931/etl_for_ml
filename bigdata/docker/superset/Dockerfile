FROM apache/superset:4.1.1

USER root
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
COPY docker-entrypoint-local.sh /app/docker-entrypoint-local.sh
RUN chmod +x /app/docker-entrypoint-local.sh
USER superset
