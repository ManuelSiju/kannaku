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
make run-server     # API on :8013 (foreground); make up runs it in the background
make health
make test
```

Run `make` to see every target.

## Run it: laptop server + phone

```bash
# laptop — once
make setup && make setup-system
make smoke              # tests + lint + make up (local) + model check + /health + make down

# laptop — every time
make up                 # asks for a Meta Model API key (hidden). Enter = local models.
make up PROVIDER=local  # or PROVIDER=meta: skip the question
make status · make provider · make logs · make down
make forget-key         # delete the saved Meta key from .env.local
```

`make up` chooses the model provider in this order: `PROVIDER=meta|local` on the command line; a saved
`META_API_KEY` (environment or `.env.local`); a hidden prompt in a terminal; otherwise (CI, `make smoke`) local.
A Meta key is checked with one call first (10 s). If it is rejected or there is no internet, `make up` says so and
offers the local models; it never starts half-configured. A typed key can be saved in `.env.local` (gitignored,
mode 600). The key is never printed or logged, and never appears in a trace, an error, `/health` or the app.

At the end `make up` prints the provider, models, cache, spend guard, the laptop and phone URLs, and the **access
token** to type into the app's Settings (every request except `/health` needs `Authorization: Bearer <token>`).

With Meta: identical prompts are answered from a SQLite cache, and `META_MAX_CALLS_PER_DAY` (default 300) caps the calls
(warning at 80 %). At the cap an ask fails with a clear message, or, with `LLM_FALLBACK=local`, the local models answer
and the answer carries a "local fallback" badge. Speech-to-text stays on local faster-whisper until a Meta speech
endpoint is confirmed.

```bash
# phone on the same Wi-Fi
make lan-url            # open the printed /health URL in the phone browser
make firewall-open      # only if the phone cannot connect (ufw)

# phone over USB instead (no Wi-Fi needed; enable USB debugging)
make phone-devices && make phone-usb

# the app
make run-app            # Wi-Fi
make run-app USB=1      # USB tunnel
```

## API and reliability

- Versioned under `/v1` (old unversioned paths stay as aliases until the app switches). `GET /health` (liveness and
  providers), `GET /ready` (database and LLM reachable).
- One error format: `{"error": {"code", "message", "request_id"}}`. Every response carries `X-Request-ID`, which is
  also in every log line (`run/server.log`, JSON, rotated 10 MB × 5) and in the case trace.
- Limits: audio 10 MB, images 8 MB each, PDF 15 MB, at most 5 files, types checked by content; 20 asks a minute
  per device; request timeout. `Idempotency-Key` on `POST /v1/cases` makes a resend safe.
- Provider calls retry once with backoff on timeouts, 429 and 5xx, within the 4-call budget per ask.
- SQLite in WAL mode with numbered migrations (`server/app/db/migrations`); a daily copy goes to `run/backups`
  (newest 3 kept). Shutdown waits up to 15 s for running asks.
- CI (`.github/workflows/ci.yml`): server tests and lint on every push; `flutter analyze` and `flutter test` once
  the app exists.

## Models

| Role | Local | Meta (chosen at `make up`) |
|---|---|---|
| LLM (text + vision) | Ollama / llama.cpp, OpenAI-compatible `/v1` (see docs/model_setup.md) | Meta Model API (`https://api.meta.ai/v1`, `muse-spark-1.3`), vision on |
| Speech-to-text | faster-whisper | faster-whisper (Meta speech endpoint not confirmed yet) |
| Text-to-speech | on-device (flutter_tts) | on-device |
| OCR | Tesseract eng | Tesseract eng |

## Layout

```
server/app/      FastAPI app, providers, engines, pipeline, db, MCP server
server/tests/    tests
app/             Flutter app (phase 5)
```

_Full docs arrive in phase 6._
