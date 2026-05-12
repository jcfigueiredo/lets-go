.DEFAULT_GOAL := help

.PHONY: help setup test

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Install Python deps via uv
	uv sync

test: ## Run pytest with 100% branch coverage enforced
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
