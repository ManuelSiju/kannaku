# Kanakku — one place for all routine work. Run `make` to see every target.

SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV    := .venv
PY      := $(abspath $(VENV)/bin/python)
SERVER  := server
ENV_GET  = $(shell grep -E '^$(1)=' .env 2>/dev/null | tail -n1 | cut -d= -f2- | sed -E 's/[[:space:]]+\#.*$$//; s/[[:space:]]+$$//')
HOST    ?= $(or $(call ENV_GET,HOST),0.0.0.0)
PORT    ?= $(or $(call ENV_GET,PORT),8013)
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
        check-models test test-fast smoke lint fmt clean run-mcp seed-demo reset-demo demo-assets run-app demo commit-phase \
        reliability reliability-framing reliability-vision lan-url firewall-open phone-devices phone-usb phone-usb-off up down status logs app-release app-ios provider forget-key app-test start stop phone app-fixtures app-goldens app-integration meta-check

help: ##! Show this list (owner commands first)
	@echo "Start here (docs/OWNER_GUIDE.md):"
	@grep -hE '^[a-zA-Z_-]+:.*?##! ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?##! "}; {printf "  \033[32m%-14s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Developer commands (docs/GUIDE.md):"
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- owner commands
doctor: ##! Check everything; each problem comes with the command that fixes it
	@scripts/doctor.sh

start: ##! Start Kanakku (asks for a Meta key; press Enter for the local AI) and show the phone settings
	@PROVIDER="$(PROVIDER)" scripts/start.sh

stop: ##! Stop Kanakku
	@scripts/down.sh

phone: ##! Build the app and put it on the phone (USB), or show the file to send to the phone
	@scripts/phone.sh

demo: ##! Reset the demo family and show the 4 demo questions
	@scripts/demo.sh

# ---------------------------------------------------------------- setup
setup: env ##! One-time setup: Python, the server parts and the settings file
	@command -v uv >/dev/null || { echo "uv missing: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	test -x $(PY) || uv venv --python 3.11 $(VENV)
	uv pip install --python $(PY) -e "$(SERVER)[dev]"
	@cd app 2>/dev/null && command -v flutter >/dev/null && flutter pub get >/dev/null && echo "✔ app packages ready" || true
	@echo "✔ setup done. Next: make doctor"

env: ## Copy .env.example to .env if .env does not exist
	@test -f .env || { cp .env.example .env; echo "✔ created .env from .env.example"; }

setup-system: ## Install OS packages: tesseract (English + Malayalam), ffmpeg, adb (needs sudo)
	sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-mal ffmpeg adb

# ---------------------------------------------------------------- run
up: ## Choose provider (PROVIDER=meta|local), start LLM backend if local + API server; prints phone URL + token
	@PROVIDER="$(PROVIDER)" scripts/up.sh

provider: ## Show the provider the server uses (and what the next make up would choose)
	@scripts/provider.sh

forget-key: ## Delete the saved Meta API key from .env.local
	@scripts/forget_key.sh

down: ## Stop the server, and the LLM backend only if make up started it
	@scripts/down.sh

status: ## What is running, ports, health
	@scripts/status.sh

logs: ## Follow the background server log, JSON lines (Ctrl-C to quit)
	@test -f run/server.log && tail -n 50 -f run/server.log || echo "no run/server.log yet — make up"

run-server: ## Start the API in the foreground on PORT (reachable from phone on same Wi-Fi), auto-reload
	@echo "Server for phone: http://$(LAN_IP):$(PORT)   (health: http://$(LAN_IP):$(PORT)/health)"
	cd $(SERVER) && $(PY) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

health: ## Call GET /health on the running server
	@curl -fsS http://localhost:$(PORT)/health | $(PY) -m json.tool

# ---------------------------------------------------------------- local LLM (Ollama)
llm-up: ## Start the Ollama server in the background
	@curl -fsS --max-time 3 http://$${OLLAMA_HOST:-localhost:11434}/api/version >/dev/null 2>&1 && echo "ollama already running" || \
	  { nohup ollama serve >/tmp/kanakku-ollama.log 2>&1 & sleep 2; echo "✔ ollama started (log /tmp/kanakku-ollama.log)"; }

llm-down: ## Stop the Ollama server
	-pkill -f "ollama serve" && echo "✔ ollama stopped"

llm-pull: llm-up ## Download the model named in .env LLM_MODEL (override: make llm-pull LLM_MODEL=...)
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

smoke: ## Full local check: tests + lint + make up + model check + /health + make down
	$(MAKE) --no-print-directory test-fast
	$(MAKE) --no-print-directory lint
	@if [ -f run/server.pid ] && kill -0 $$(cat run/server.pid) 2>/dev/null; then \
	  echo "server already up — smoke checks it and leaves it running"; \
	  $(MAKE) --no-print-directory check-models && scripts/status.sh; \
	else \
	  had_llm=$$(test -f run/llm.pid && echo 1); \
	  scripts/up.sh && $(MAKE) --no-print-directory check-models; rc=$$?; \
	  if [ -z "$$had_llm" ]; then scripts/down.sh; else scripts/down.sh --server-only; fi; \
	  [ $$rc -eq 0 ] && echo "✔ smoke done" || { echo "✘ smoke failed"; exit 1; }; \
	fi

lint: ## Ruff lint
	cd $(SERVER) && $(PY) -m ruff check .

fmt: ## Ruff auto-fix + format
	cd $(SERVER) && $(PY) -m ruff check --fix . && $(PY) -m ruff format .

clean: ## Remove caches (keeps .venv and .env)
	find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rm -rf $(SERVER)/.pytest_cache $(SERVER)/.ruff_cache

reliability: ## Real-model run: 5 cases x RUNS (default 5) -> docs/reliability.md (needs make up / llm-up)
	cd $(SERVER) && $(PY) scripts/reliability.py --runs $(or $(RUNS),5)

reliability-framing: ## Real-model framing test: 3 framings x RUNS (default 3) -> docs/reliability_framing.md
	cd $(SERVER) && $(PY) scripts/reliability.py --framing --runs $(or $(RUNS),3)

reliability-vision: ## Endowment from brochure PHOTOS with LLM_VISION_MODEL -> docs/reliability_vision.md
	cd $(SERVER) && $(PY) scripts/reliability.py --vision --runs $(or $(RUNS),3)

# ---------------------------------------------------------------- phone
lan-url: ## Print the URLs to open on your phone (same Wi-Fi)
	@echo "Laptop IP : $(LAN_IP)"
	@echo "Health    : http://$(LAN_IP):$(PORT)/health   <- open in phone browser"
	@echo "API docs  : http://$(LAN_IP):$(PORT)/docs"

firewall-open: ## Allow PORT (8013) through ufw so the phone can reach the server (sudo)
	sudo ufw allow $(PORT)/tcp

phone-devices: ## List phones/emulators adb + flutter can see
	adb devices -l
	flutter devices

phone-usb: ## USB phone: tunnel the phone's localhost:PORT to this laptop (no Wi-Fi/firewall needed)
	adb reverse tcp:$(PORT) tcp:$(PORT) && echo "✔ phone http://127.0.0.1:$(PORT) -> laptop:$(PORT)"

phone-usb-off: ## Remove the USB tunnel
	adb reverse --remove tcp:$(PORT)

# ---------------------------------------------------------------- app builds
app-release: ## Bump build no., build release APK -> dist/, install if phone connected (BUMP=patch|minor, API_URL=)
	@scripts/app_release.sh android

app-ios: ## Same as app-release for iOS (needs macOS + Xcode)
	@scripts/app_release.sh ios

# ---------------------------------------------------------------- later phases
run-mcp: ## Start the MCP server on stdio (for MCP clients; Ctrl-C to stop)
	cd $(SERVER) && $(PY) -m app.mcp_server.server

seed-demo: ## Add the fictional demo family (safe to repeat)
	cd $(SERVER) && $(PY) -m app.db.seed_demo

reset-demo: ## Wipe the database and re-seed the demo family
	cd $(SERVER) && $(PY) -m app.db.seed_demo --reset

demo-assets: ## Regenerate fictional brochure PDF/PNGs, ZEPHYRX tip + price CSV
	cd $(SERVER) && $(PY) scripts/make_demo_assets.py

run-app: ## Run the app on a connected phone (Wi-Fi URL; USB=1 for usb tunnel; DEVICE=id); passes the LAN token
	@echo "App -> server at $(API_URL)"; \
	  token=$$(grep -E '^KANAKKU_TOKEN=' .env.local 2>/dev/null | cut -d= -f2-); \
	  [ -n "$$token" ] || echo "! no access token yet: run make up first (or type it in the app's Settings)"; \
	  cd app && flutter run $(if $(DEVICE),-d $(DEVICE),) --dart-define=API_URL=$(API_URL) --dart-define=API_TOKEN=$$token

app-test: ## flutter analyze + flutter test
	cd app && flutter analyze && flutter test

app-fixtures: ## Re-export the app test fixtures from the real pipeline (offline)
	cd $(SERVER) && $(PY) scripts/export_app_fixtures.py

app-goldens: ## Re-draw the app screenshots (app/test/goldens -> docs/screens)
	cd app && flutter test test/screens_test.dart --update-goldens
	@mkdir -p docs/screens && cp app/test/goldens/*.png docs/screens/ && echo "✔ docs/screens"

app-integration: ## On-device tests against the real server + screen recording (emulator or USB phone)
	@scripts/app_integration.sh

meta-check: ## One endowment case against the real Meta API (only if META_API_KEY is set)
	cd $(SERVER) && $(PY) scripts/meta_live_check.py

# ---------------------------------------------------------------- git
commit-phase: ## Test, then commit everything: make commit-phase P=2 M="numbers and engines"
	@test -n "$(P)" || { echo 'usage: make commit-phase P=<n> M="<summary>"'; exit 1; }
	$(MAKE) test
	git add -A && git commit -m "phase $(P): $(M)"
