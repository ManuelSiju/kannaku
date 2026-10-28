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
make setup-system   # tesseract (+Malayalam), ffmpeg — needs sudo
make llm-up         # start Ollama
make llm-pull       # pull the model in .env (default qwen2.5:7b-instruct)
make check-models   # PASS/FAIL per provider
make run-server     # API on :8000
make health
make test
```

Run `make` to see every target.

## Models

All models sit behind provider interfaces chosen by `.env`:

| Role | Local (now) | Later |
|---|---|---|
| LLM (text + vision) | Ollama / llama.cpp, OpenAI-compatible `/v1` | Meta Model API (`https://api.meta.ai/v1`, `muse-spark-1.3`) |
| Speech-to-text | faster-whisper | Muse Voice Transcribe |
| Text-to-speech | on-device (flutter_tts) | — |
| OCR | Tesseract eng + mal | — |

Switching LLM = editing `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` in `.env`. No code changes.

## Layout

```
server/app/      FastAPI app, providers, engines, pipeline, db, MCP server
server/tests/    tests
app/             Flutter app (phase 5)
```

_Full docs arrive in phase 6._
