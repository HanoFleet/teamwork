.PHONY: up down logs check check-security acceptance grade

up:
	docker compose up --build -d --wait

down:
	docker compose down

logs:
	docker compose logs -f api

check:
	sh scripts/check.sh

check-security:
	python3 scripts/secret_scan.py
	cd frontend && npm audit --audit-level=high

acceptance:
	python3 scripts/acceptance.py

grade:
	sh scripts/grade.sh
