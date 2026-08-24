# Automotive ECU Cybersecurity Lab
#
# Everything here runs on a clean checkout with nothing but Python 3.11+.
# `make check` is exactly what CI runs.

PYTHON     ?= python3
LABCTL_DIR := tools/labctl
LABCTL     := PYTHONPATH=$(LABCTL_DIR) $(PYTHON) -m labctl
PROJECT    ?=

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@printf '\n  \033[1mAutomotive ECU Cybersecurity Lab\033[0m\n\n'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@printf '\n  Build a project:  cd projects/<name> && claude   (then paste prompts/kickoff.md)\n\n'

.PHONY: status
status: ## What is specified, building and built
	@$(LABCTL) status

.PHONY: show
show: ## Detail for one project — make show PROJECT=can-secoc-demo
	@test -n "$(PROJECT)" || { echo "usage: make show PROJECT=<id>"; exit 2; }
	@$(LABCTL) show $(PROJECT)

.PHONY: validate
validate: ## Every repository consistency rule
	@$(LABCTL) validate

.PHONY: standards
standards: ## The standards register, and what needs re-checking
	@$(LABCTL) standards

.PHONY: render
render: ## Regenerate the documentation blocks from lab.toml
	@$(LABCTL) render

.PHONY: assets
assets: ## Regenerate every SVG in both themes
	@$(PYTHON) tools/assets/render_assets.py

.PHONY: test
test: ## Run the tooling's test suite
	@cd $(LABCTL_DIR) && $(PYTHON) -m pytest

.PHONY: lint
lint: ## Lint and format-check the tooling
	@cd $(LABCTL_DIR) && $(PYTHON) -m ruff check labctl tests
	@cd $(LABCTL_DIR) && $(PYTHON) -m ruff format --check labctl tests

# Keep this list in step with .github/workflows/ci.yml. A `check` that is
# missing something CI runs is worse than no `check` at all — it reports green
# on a tree CI will reject.
.PHONY: check
check: validate ## Everything CI runs
	@$(LABCTL) render --check
	@$(PYTHON) tools/assets/render_assets.py --check
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory test
	@printf '\n  \033[32mall checks passed\033[0m\n\n'

.PHONY: dev
dev: ## Install the tooling's development dependencies
	@$(PYTHON) -m pip install --quiet pytest ruff
	@echo "installed: pytest, ruff"
