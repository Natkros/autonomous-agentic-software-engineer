.PHONY: api-install api-test api-dev web-install web-build web-dev up down logs

api-install:
	cd apps/api && python -m venv .venv && . .venv/Scripts/activate && pip install -r requirements-dev.txt

api-test:
	cd apps/api && . .venv/Scripts/activate && python -m pytest -v

api-dev:
	cd apps/api && . .venv/Scripts/activate && uvicorn app.main:app --reload

web-install:
	cd apps/web && npm install

web-build:
	cd apps/web && npm run build

web-dev:
	cd apps/web && npm run dev

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f
