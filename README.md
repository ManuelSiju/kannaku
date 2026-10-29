# Kanakku

Voice-first money adviser for ordinary Indian families. Ask a money question by voice or text (optionally
show a brochure, loan offer or stock tip); a council of AI specialists — **Alfii** (curator), **Sankz**
(banking), **Dani** (mutual funds), **Vick** (stocks) — answers with a red / yellow / green verdict, one plain
sentence and up to three "ask him this" questions.

Every number comes from deterministic code, never from the LLM. Decision support, not investment advice.

Built for the Meta AI Developer Hackathon (Oct 27 – Nov 4 2026).

## Quick start (dev)

```bash
make setup          # .venv (Python 3.11) + deps + .env
make setup-system   # tesseract (English), ffmpeg — needs sudo
make llm-up         # start Ollama
make llm-pull       # pull the model in .env (default qwen2.5:7b-instruct)
make check-models   # PASS/FAIL per provider
make run-server     # API on :8000
make health
make test
```

Run `make` to see every target.

## Test on your laptop (server) and phone

```bash
# laptop — once
make setup && make setup-system && make llm-up && make llm-pull
make smoke              # tests + lint + model check + /health, all in one

# laptop — every time
make llm-up
make run-server         # prints the URL your phone should use

# phone on the same Wi-Fi
make lan-url            # open the printed /health URL in the phone browser
make firewall-open      # only if the phone cannot connect (ufw)

# phone over USB instead (no Wi-Fi needed; enable USB debugging)
make phone-devices      # phone must be listed
make phone-usb          # tunnel phone 127.0.0.1:8000 -> laptop

# the app (from phase 5)
make run-app            # Wi-Fi: app talks to http://<laptop-ip>:8000
make run-app USB=1      # USB tunnel: app talks to http://127.0.0.1:8000
```

## Models

All models sit behind provider interfaces chosen by `.env`:

| Role | Local (now) | Later |
|---|---|---|
| LLM (text + vision) | Ollama / llama.cpp, OpenAI-compatible `/v1` | Meta Model API (`https://api.meta.ai/v1`, `muse-spark-1.3`) |
| Speech-to-text | faster-whisper | Muse Voice Transcribe |
| Text-to-speech | on-device (flutter_tts) | — |
| OCR | Tesseract eng (Malayalam later) | — |

Switching LLM = editing `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` in `.env`. No code changes.

## Layout

```
server/app/      FastAPI app, providers, engines, pipeline, db, MCP server
server/tests/    tests
app/             Flutter app (phase 5)
```

_Full docs arrive in phase 6._
