# Secure Boot Chain Simulator
#
# `make check` is exactly what .github/workflows/secboot.yml runs.

PYTHON  ?= python3
SECBOOT := PYTHONPATH=src $(PYTHON) -m secboot
PYTEST  := PYTHONPATH=src $(PYTHON) -m pytest

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@printf '\n  \033[1mSecure Boot Chain Simulator\033[0m\n\n'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
	@printf '\n'

.PHONY: setup
setup: ## Install runtime and development dependencies
	@$(PYTHON) -m pip install --quiet --upgrade pip
	@$(PYTHON) -m pip install --quiet "cryptography>=42" "typer>=0.12" "rich>=13" \
		"pytest>=8.0" "pytest-cov>=5.0" "ruff>=0.6" "mypy>=1.10"
	@echo "ready — run: make demo"

.PHONY: demo
demo: ## The eight scenarios, narrated
	@$(SECBOOT) demo

.PHONY: lint
lint: ## Lint and format-check
	@$(PYTHON) -m ruff check src tests
	@$(PYTHON) -m ruff format --check src tests

.PHONY: types
types: ## Strict type check
	@$(PYTHON) -m mypy --strict src/secboot

.PHONY: test
test: ## Tests with the coverage floor
	@$(PYTEST) --cov=secboot --cov-report=term-missing --cov-fail-under=85

.PHONY: check
check: lint types test ## Everything CI runs
	@printf '\n  \033[32mall checks passed\033[0m\n\n'

.PHONY: clean
clean: ## Remove runtime state and caches
	@rm -rf state images .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "clean"
