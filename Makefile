
.PHONY: generate-phase1 validate-phase1 docker-validate-phase1

generate-phase1:
	python scripts/generate_phase1_benchmarks.py

validate-phase1:
	python scripts/validate_phase1.py --check-fixtures

docker-validate-phase1:
	docker compose run --rm evaluator
