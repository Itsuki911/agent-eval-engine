
.PHONY: generate-phase1 validate-phase1 docker-validate-phase1 db-up db-migrate db-test db-shell phase3-dry-run phase3-test

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

phase3-dry-run:
	docker compose --profile engine run --rm engine python scripts/run_evaluation.py --benchmark benchmarks/generic/GEN-TOOL-001.yaml

phase3-test:
	docker compose --profile engine run --rm engine pytest -q tests/unit/test_phase3_config.py tests/unit/test_phase3_metrics.py tests/integration/test_phase3_workflow.py
