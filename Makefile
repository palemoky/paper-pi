.PHONY: help test lint format clean dev build deploy install-dev

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	uv sync

install-dev:  ## Install development dependencies
	uv sync --extra dev
	uv run pre-commit install

test:  ## Run tests
	uv run pytest tests/ -v --cov=src --cov-report=term-missing

test-fast:  ## Run tests without coverage
	uv run pytest tests/ -v

lint:  ## Run linters
	uv run ruff check src/ tests/ mocks/
	uv run mypy src/ --ignore-missing-imports

format:  ## Format code
	uv run ruff format src/ tests/ mocks/
	uv run ruff check --fix src/ tests/ mocks/

format-check:  ## Check code formatting
	uv run ruff format --check src/ tests/ mocks/

clean:  ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/

dev:  ## Run in development mode (screenshot mode)
	uv run python -m src.main

mock-all:  ## Generate all mock images
	uv run python -m mocks.generate --all

mock-dashboard:  ## Generate dashboard mock image
	uv run python -m mocks.generate --mode dashboard

mock-holiday:  ## Generate holiday mock image
	uv run python -m mocks.generate --mode holiday

mock-quote:  ## Generate quote mock image
	uv run python -m mocks.generate --mode quote

mock-poetry:  ## Generate poetry mock image
	uv run python -m mocks.generate --mode poetry

docker-build:  ## Build Docker image
	docker build -t paper-pi .

docker-run:  ## Run Docker container
	docker run --rm -it --env-file .env paper-pi

docker-dev:  ## Run Docker container in development mode
	docker run --rm -it --env-file .env -v $(PWD)/data:/app/data paper-pi

check:  ## Run all checks (format, lint, test)
	@echo "Running format check..."
	@make format-check
	@echo "\nRunning linters..."
	@make lint
	@echo "\nRunning tests..."
	@make test

pre-commit:  ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files
