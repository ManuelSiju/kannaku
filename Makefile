# Kanakku — one place for all routine work. Run `make` to see every target.

SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV    := .venv
PY      := $(abspath $(VENV)/bin/python)
SERVER  := server
HOST    ?= 0.0.0.0
PORT    ?= 8000
LAN_IP  := $(shell ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($$i=="src") print $$(i+1)}')
# Where the app reaches the server. Default: this laptop on Wi-Fi. USB=1 -> phone uses adb reverse tunnel.
ifeq ($(USB),1)
API_URL ?= http://127.0.0.1:$(PORT)
else
API_URL ?= http://$(LAN_IP):$(PORT)
endif

# Read LLM_MODEL from .env (fallback to the dev default) for the ollama targets.
LLM_MODEL ?= $(shell grep -E '^LLM_MODEL=' .env 2>/dev/null | cut -d= -f2 | cut -d' ' -f1)
ifeq ($(LLM_MODEL),)
LLM_MODEL := qwen2.5:7b-instruct
endif

.PHONY: help setup setup-system env doctor run-server health llm-up llm-down llm-pull llm-list \
        check-models test test-fast smoke lint fmt clean run-mcp seed-demo reset-demo run-app demo commit-phase \
        lan-url firewall-open phone-devices phone-usb phone-usb-off

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
run-server: ## Start the API on :8000 (reachable from phone on same Wi-Fi), auto-reload
	@echo "Server for phone: http://$(LAN_IP):$(PORT)   (health: http://$(LAN_IP):$(PORT)/health)"
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

smoke: ## Full local check: tests + lint + model check + start server, hit /health, stop
	$(MAKE) --no-print-directory test-fast
	$(MAKE) --no-print-directory lint
	$(MAKE) --no-print-directory check-models
	@cd $(SERVER) && { $(PY) -m uvicorn app.main:app --port $(PORT) >/tmp/kanakku-smoke.log 2>&1 & echo $$! > /tmp/kanakku-smoke.pid; }
	@for i in $$(seq 1 30); do curl -fs localhost:$(PORT)/health >/dev/null && break; sleep 0.5; done
	@curl -fsS localhost:$(PORT)/health | $(PY) -c 'import json,sys; d=json.load(sys.stdin)["providers"]; \
	  [print("  %s %-4s %s  %s" % ("✔" if v["reachable"] else "✘", k, v["provider"], v.get("error",""))) for k,v in d.items()]' \
	  && echo "✔ smoke done" ; kill $$(cat /tmp/kanakku-smoke.pid) 2>/dev/null; rm -f /tmp/kanakku-smoke.pid

lint: ## Ruff lint
	cd $(SERVER) && $(PY) -m ruff check .

fmt: ## Ruff auto-fix + format
	cd $(SERVER) && $(PY) -m ruff check --fix . && $(PY) -m ruff format .

clean: ## Remove caches (keeps .venv and .env)
	find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rm -rf $(SERVER)/.pytest_cache $(SERVER)/.ruff_cache

# ---------------------------------------------------------------- phone
lan-url: ## Print the URLs to open on your phone (same Wi-Fi)
	@echo "Laptop IP : $(LAN_IP)"
	@echo "Health    : http://$(LAN_IP):$(PORT)/health   <- open in phone browser"
	@echo "API docs  : http://$(LAN_IP):$(PORT)/docs"

firewall-open: ## Allow port 8000 through ufw so the phone can reach the server (sudo)
	sudo ufw allow $(PORT)/tcp

phone-devices: ## List phones/emulators adb + flutter can see
	adb devices -l
	flutter devices

phone-usb: ## USB phone: tunnel phone's localhost:8000 to this laptop (no Wi-Fi/firewall needed)
	adb reverse tcp:$(PORT) tcp:$(PORT) && echo "✔ phone http://127.0.0.1:$(PORT) -> laptop:$(PORT)"

phone-usb-off: ## Remove the USB tunnel
	adb reverse --remove tcp:$(PORT)

# ---------------------------------------------------------------- later phases
run-mcp: ## [phase 3] Start the MCP server (stdio)
	@echo "run-mcp: arrives in phase 3"

seed-demo: ## [phase 3] Seed the fictional demo family
	@echo "seed-demo: arrives in phase 3"

reset-demo: ## [phase 3] Wipe DB and re-seed the demo family
	@echo "reset-demo: arrives in phase 3"

run-app: ## [phase 5] Run app on connected phone (Wi-Fi URL; USB=1 for usb tunnel; DEVICE=id)
	@test -f app/pubspec.yaml || { echo "run-app: Flutter app arrives in phase 5"; exit 0; }; \
	  echo "App -> server at $(API_URL)"; \
	  cd app && flutter run $(if $(DEVICE),-d $(DEVICE),) --dart-define=API_URL=$(API_URL)

demo: ## [phase 6] Reset demo, start server, print demo questions
	@echo "demo: arrives in phase 6"

# ---------------------------------------------------------------- git
commit-phase: ## Test, then commit everything: make commit-phase P=2 M="numbers and engines"
	@test -n "$(P)" || { echo 'usage: make commit-phase P=<n> M="<summary>"'; exit 1; }
	$(MAKE) test
	git add -A && git commit -m "phase $(P): $(M)"
