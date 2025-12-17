.PHONY: help install test clean format lint check release

.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[0;34m
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m# No Color

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-15s$(NC) %s\n", $$1, $$2}'

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

check: format-check lint test  ## Run all checks (format, lint, test)

pre-commit:  ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

release:  ## Create and push version tag (Usage: make release v1.0.0)
	@if [ -z "$(filter-out release,$(MAKECMDGOALS))" ]; then \
		echo "$(YELLOW)Usage: make release v1.0.0$(NC)"; \
		exit 1; \
	fi
	@VERSION="$(filter-out release,$(MAKECMDGOALS))"; \
	if git config user.signingkey >/dev/null 2>&1 && command -v gpg >/dev/null 2>&1; then \
		echo "$(BLUE)Creating GPG signed tag $$VERSION...$(NC)"; \
		if git tag -s $$VERSION -m "Release $$VERSION" 2>/dev/null; then \
			echo "$(GREEN)✓ Signed tag $$VERSION created successfully (Verified ✓)$(NC)"; \
		else \
			echo "$(YELLOW)⚠ GPG signing failed, using regular tag...$(NC)"; \
			git tag -a $$VERSION -m "Release $$VERSION"; \
			echo "$(GREEN)✓ Tag $$VERSION created successfully$(NC)"; \
		fi \
	else \
		echo "$(BLUE)Creating tag $$VERSION...$(NC)"; \
		git tag -a $$VERSION -m "Release $$VERSION"; \
		echo "$(GREEN)✓ Tag $$VERSION created successfully$(NC)"; \
		echo "$(YELLOW)💡 Tip: Configure GPG key to show Verified badge on GitHub$(NC)"; \
	fi; \
	echo "$(BLUE)Pushing tag to remote repository...$(NC)"; \
	git push origin $$VERSION; \
	echo "$(GREEN)✓ Release $$VERSION completed$(NC)"

# Allow version number as target
v%:
	@:
