#!/usr/bin/env bash
set -euo pipefail

superset db upgrade
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME:-admin}" \
  --firstname Admin \
  --lastname User \
  --email "${SUPERSET_ADMIN_EMAIL:-admin@example.com}" \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true
superset init
superset run -h 0.0.0.0 -p 8088
