.PHONY: up down logs ps etl ml anomaly logistics all clean

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

etl:
	docker compose exec jupyterhub bash -lc 'cd /home/project && python etl/export_to_minio.py'

ml:
	docker compose exec jupyterhub bash -lc 'cd /home/project && python etl/train_flow_model.py'

anomaly:
	docker compose exec jupyterhub bash -lc 'cd /home/project && python etl/anomaly_failure_model.py'

logistics:
	docker compose exec jupyterhub bash -lc 'cd /home/project && python etl/logistics_analysis.py'

all:
	docker compose exec jupyterhub bash -lc 'cd /home/project && python etl/run_pipeline.py'

clean:
	rm -rf tmp artifacts
	docker compose down -v
