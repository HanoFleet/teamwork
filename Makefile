.PHONY: up down logs check acceptance grade

up:
	docker compose up --build -d --wait

down:
	docker compose down

logs:
	docker compose logs -f api

check:
	sh scripts/check.sh

acceptance:
	python3 scripts/acceptance.py

grade:
	sh scripts/grade.sh
