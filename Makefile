
.PHONY: generate-phase1 validate-phase1 docker-validate-phase1 db-up db-migrate db-test db-shell

generate-phase1:
	python scripts/generate_phase1_benchmarks.py

validate-phase1:
	python scripts/validate_phase1.py --check-fixtures

docker-validate-phase1:
	docker compose run --rm evaluator

db-up:
	docker compose up -d db

db-migrate:
	docker compose run --rm db-tools alembic upgrade head

db-test:
	docker compose run --rm db-tools

db-shell:
	docker compose exec db psql -U agent_eval -d agent_eval
