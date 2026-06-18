#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
docker compose up -d --build
docker compose exec jupyterhub bash -lc 'cd /home/project && python etl/run_pipeline.py'
