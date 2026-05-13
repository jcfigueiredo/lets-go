.DEFAULT_GOAL := help

.PHONY: help setup test

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Install Python deps via uv (.env is managed by `make up`)
	uv sync

test: migrate-test ## Run pytest with 100% branch coverage enforced
	uv run pytest

.PHONY: up down db-shell clean

up: ## Start Postgres (polls until healthy) and rewrite .env with the assigned host port
	docker compose up -d
	@echo "Waiting for postgres to become healthy..."
	@i=0; while ! docker compose exec -T postgres pg_isready -U postgres -d lab >/dev/null 2>&1; do \
	  i=$$((i+1)); \
	  if [ $$i -ge 60 ]; then echo "Timed out waiting for postgres after 60s"; exit 1; fi; \
	  sleep 1; \
	done
	@port=$$(docker compose port postgres 5432 | cut -d: -f2); \
	  echo "Postgres healthy on host port $$port"; \
	  printf 'DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:%s/lab\nTEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:%s/lab_test\n' $$port $$port > .env

down: ## Stop Postgres
	docker compose down

db-shell: ## Open psql against the lab database
	docker compose exec postgres psql -U postgres -d lab

clean: ## Stop and remove the Postgres volume (DESTRUCTIVE — asks first)
	@read -p "This will destroy the lab Postgres volume. Continue? [y/N] " ans && [ "$$ans" = "y" ] || exit 1
	docker compose down -v

.PHONY: migrate migration migrate-down migrate-test

migrate: ## Apply pending migrations to the lab database
	uv run alembic upgrade head

migration: ## Generate a new migration revision; usage: make migration m="describe change"
	@test -n "$(m)" || (echo "Usage: make migration m=\"description\""; exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

migrate-down: ## Downgrade N revisions; usage: make migrate-down N=1
	@test -n "$(N)" || (echo "Usage: make migrate-down N=1"; exit 1)
	uv run alembic downgrade -$(N)

migrate-test: ## Apply migrations to the lab_test database (used by pytest setup)
	@docker compose exec -T postgres psql -U postgres -d postgres -c "CREATE DATABASE lab_test;" 2>/dev/null || true
	@set -a; . ./.env; set +a; DATABASE_URL="$$TEST_DATABASE_URL" uv run alembic upgrade head

.PHONY: seed start test-one coverage lint format

seed: ## Apply seed data to the lab database
	uv run python -m lab.seed

start: ## One-command bootstrap: up + migrate + seed
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) seed

test-one: ## Run a single test path; usage: make test-one T=tests/test_foo.py::test_bar
	@test -n "$(T)" || (echo "Usage: make test-one T=tests/path::test_name"; exit 1)
	uv run pytest $(T) -v --no-cov

coverage: migrate-test ## Run pytest and open the HTML coverage report
	uv run pytest --cov-report=html
	@command -v open >/dev/null 2>&1 && open htmlcov/index.html || echo "Open htmlcov/index.html manually"

lint: ## Lint with ruff
	uv run ruff check .

format: ## Format with ruff
	uv run ruff format .

.PHONY: load

load: ## Run DB load test; default N=100000. Override: make load N=1000000
	uv run python -m scripts.load_test --rows $${N:-100000}
