.DEFAULT_GOAL := help

.PHONY: help setup test

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Install Python deps via uv; copy .env.example to .env if missing
	uv sync
	@test -f .env || cp .env.example .env

test: ## Run pytest with 100% branch coverage enforced
	uv run pytest
