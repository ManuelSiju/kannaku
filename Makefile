# Kanakku — one place for all routine work. Run `make` to see every target.

SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV    := .venv
PY      := $(abspath $(VENV)/bin/python)
SERVER  := server
HOST    ?= 0.0.0.0
PORT    ?= 8000
API_URL ?= http://10.0.2.2:$(PORT)

# Read LLM_MODEL from .env (fallback to the dev default) for the ollama targets.
LLM_MODEL ?= $(shell grep -E '^LLM_MODEL=' .env 2>/dev/null | cut -d= -f2 | cut -d' ' -f1)
ifeq ($(LLM_MODEL),)
LLM_MODEL := qwen2.5:7b-instruct
endif

.PHONY: help setup setup-system env doctor run-server health llm-up llm-down llm-pull llm-list \
        check-models test test-fast lint fmt clean run-mcp seed-demo reset-demo run-app demo commit-phase

help: ## Show this list
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- setup
setup: env ## Create .venv (Python 3.11) and install server + dev deps
	@command -v uv >/dev/null || { echo "uv missing: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	test -x $(PY) || uv venv --python 3.11 $(VENV)
	uv pip install --python $(PY) -e "$(SERVER)[dev]"
	@echo "✔ setup done. Next: make doctor"

env: ## Copy .env.example to .env if .env does not exist
	@test -f .env || { cp .env.example .env; echo "✔ created .env from .env.example"; }

setup-system: ## Install OS packages: tesseract (English), ffmpeg (needs sudo)
	sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-eng ffmpeg

doctor: ## Show which tools are installed
	@for t in uv python3 tesseract ffmpeg ollama llama-server flutter; do \
	  if command -v $$t >/dev/null; then printf "  ✔ %-13s %s\n" $$t "$$(command -v $$t)"; \
	  else printf "  ✘ %-13s missing\n" $$t; fi; done
	@test -x $(PY) && echo "  ✔ venv          $$($(PY) --version)" || echo "  ✘ venv          run: make setup"
	@test -f .env && echo "  ✔ .env" || echo "  ✘ .env          run: make env"
	@command -v tesseract >/dev/null && echo "  tesseract langs: $$(tesseract --list-langs 2>/dev/null | tail -n +2 | tr '\n' ' ')" || true

# ---------------------------------------------------------------- run
run-server: ## Start the API on :8000 with auto-reload
	cd $(SERVER) && $(PY) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

health: ## Call GET /health on the running server
	@curl -fsS http://localhost:$(PORT)/health | $(PY) -m json.tool

# ---------------------------------------------------------------- local LLM (Ollama)
llm-up: ## Start the Ollama server in the background
	@curl -fsS http://localhost:11434/api/version >/dev/null 2>&1 && echo "ollama already running" || \
	  { nohup ollama serve >/tmp/kanakku-ollama.log 2>&1 & sleep 2; echo "✔ ollama started (log /tmp/kanakku-ollama.log)"; }

llm-down: ## Stop the Ollama server
	-pkill -f "ollama serve" && echo "✔ ollama stopped"

llm-pull: ## Download the model named in .env LLM_MODEL (override: make llm-pull LLM_MODEL=...)
	ollama pull $(LLM_MODEL)

llm-list: ## List local Ollama models
	ollama list

# ---------------------------------------------------------------- checks
check-models: ## Call each provider once (LLM, vision, STT, OCR) and print PASS/FAIL
	cd $(SERVER) && $(PY) scripts/check_models.py

test: ## Run all server tests
	cd $(SERVER) && $(PY) -m pytest

test-fast: ## Run tests, stop at first failure
	cd $(SERVER) && $(PY) -m pytest -x -q

lint: ## Ruff lint
	cd $(SERVER) && $(PY) -m ruff check .

fmt: ## Ruff auto-fix + format
	cd $(SERVER) && $(PY) -m ruff check --fix . && $(PY) -m ruff format .

clean: ## Remove caches (keeps .venv and .env)
	find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rm -rf $(SERVER)/.pytest_cache $(SERVER)/.ruff_cache

# ---------------------------------------------------------------- later phases
run-mcp: ## [phase 3] Start the MCP server (stdio)
	@echo "run-mcp: arrives in phase 3"

seed-demo: ## [phase 3] Seed the fictional demo family
	@echo "seed-demo: arrives in phase 3"

reset-demo: ## [phase 3] Wipe DB and re-seed the demo family
	@echo "reset-demo: arrives in phase 3"

run-app: ## [phase 5] Run the Flutter app (API_URL=... to override)
	@test -f app/pubspec.yaml && { cd app && flutter run --dart-define=API_URL=$(API_URL); } || echo "run-app: arrives in phase 5"

demo: ## [phase 6] Reset demo, start server, print demo questions
	@echo "demo: arrives in phase 6"

# ---------------------------------------------------------------- git
commit-phase: ## Test, then commit everything: make commit-phase P=2 M="numbers and engines"
	@test -n "$(P)" || { echo 'usage: make commit-phase P=<n> M="<summary>"'; exit 1; }
	$(MAKE) test
	git add -A && git commit -m "phase $(P): $(M)"
