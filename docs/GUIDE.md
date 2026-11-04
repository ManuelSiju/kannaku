# Kanakku — technical guide

Everything here is written from the code in this repository; every command is a real Makefile target or script.
For a non-technical walkthrough see [OWNER_GUIDE.md](OWNER_GUIDE.md).

## 1. What Kanakku is

Kanakku is a voice-first money adviser for ordinary Indian families. "Amma" (60+, not a finance person) asks a money
question by voice or text, optionally showing a brochure, loan offer or stock-tip message. A council of AI
specialists answers with a red / yellow / green verdict, one plain sentence, up to three questions to ask the seller,
and each specialist's short spoken line. Every number comes from deterministic code, never from the model.
Decision support, not investment advice.

**Demo story.** An agent tells Lakshmi a plan is "guaranteed to give 15 lakh". She photographs the brochure and asks.
Alfii calls Dani and Sankz; code reads the brochure twice, computes the real yearly return (3.75 % at the lower bonus
rate, below a 7 % fixed deposit), sees that only 7.5 lakh is guaranteed, and the council says **Stop** — with the
questions to ask the agent, a note only on her screen about what the premium means for her budget, and an alert to her
son Arun, who leaves her a note.

## 2. Architecture

```
 Flutter app (Android/iOS)                         laptop (one machine, no cloud services)
 ┌───────────────────────┐   HTTP + Bearer token   ┌────────────────────────────────────────────────────────┐
 │ Home · Working · Verdict│ ────────────────────▶ │ FastAPI  /v1/...  (request id, limits, errors, auth)   │
 │ Council · Why · Details │ ◀─── JSON + SSE ───── │   │                                                    │
 │ Guardian · Settings     │                       │   ▼  pipeline (server/app/pipeline/run.py)             │
 └───────────────────────┘                         │  ingest → scam_rules → case_builder → verify_terms →   │
                                                   │  compute → router → council → evidence → debate →      │
                                                   │  consensus → privacy → explainer → questions → save    │
                                                   │   │                 │                                  │
                                                   │   ▼                 ▼                                  │
                                                   │ engines/ (finance, tip_signals, compare)   providers/  │
                                                   │ mcp_server/tools.py (same functions as      llm  ──────┼─▶ Ollama / llama.cpp
                                                   │   the MCP server)                           stt (whisper)  or Meta Model API
                                                   │   │                                         ocr (tesseract)
                                                   │   ▼                                                    │
                                                   │ SQLite (WAL, migrations, daily backups)                │
                                                   └────────────────────────────────────────────────────────┘
```

| folder | what it holds |
|---|---|
| `server/app/main.py` | FastAPI app: lifespan (settings check, logging, migrations, backups, graceful shutdown), `/v1` routers + old aliases |
| `server/app/api/` | endpoints (`cases`, `families`, `items`, `alerts`, `health`), `middleware.py` (request id, token, limits), `errors.py`, `uploads.py` |
| `server/app/pipeline/` | the ask pipeline, one file per step; `questions.py` (question bank), `vick.py`, `templates.py` (en/ml/hi code-written lines) |
| `server/app/engines/` | deterministic maths: `finance.py`, `tip_signals.py`, `compare.py`, `fact.py` (the Fact model) |
| `server/app/numbers/` | Indian number parser (lakh, crore, ₹1,50,000) |
| `server/app/providers/` | `llm.py` (OpenAI-compatible client, budget, retries), `guard.py` (Meta cache + daily cap), `stt.py`, `ocr.py`, `tts.py` |
| `server/app/mcp_server/` | FastMCP server over the same tools (`make run-mcp`) |
| `server/app/db/` | `repo.py`, `migrations/NNNN_*.sql`, `migrate.py`, `backup.py`, `seed_demo.py` (fictional family) |
| `server/app/prompts/` | all prompts (short; inputs are compact JSON) |
| `server/tests/` | 400+ offline tests; `fakes/` (scripted LLM, fake Meta server) |
| `server/scripts/` | `reliability.py`, `export_app_fixtures.py`, `meta_key.py`, `meta_live_check.py`, `check_models.py` |
| `app/lib/` | Flutter app: `core/` (API client, models, speech, pickers), `state/` (providers), `screens/`, `widgets/` |
| `app/test/`, `app/integration_test/` | widget + screenshot tests (fixtures from the real pipeline), on-device tests |
| `scripts/` | shell scripts behind the Makefile (`up.sh`, `doctor.sh`, `start.sh`, `phone.sh`, `app_integration.sh`, …) |
| `docs/` | this guide, the owner guide, reliability reports, screenshots (`docs/screens/`), `demo_run.mp4` |

## 3. Requirements

| | needed | notes |
|---|---|---|
| OS | Linux (tested: Linux Mint 22.3 / Ubuntu 24.04 base) | macOS works for the server; `setup-system` uses apt |
| Python | 3.11 (installed by `uv` into `.venv`) | `make start` |
| uv | any recent | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Ollama | 0.24+ | `curl -fsSL https://ollama.com/install.sh \| sh`; model `qwen2.5:7b-instruct` (4.7 GB) |
| Tesseract | with `eng` (+ `mal` optional) | `make start` |
| ffmpeg, adb | | `make start` |
| Flutter | 3.41 stable | only to build the app; includes Dart |
| Android SDK + adb | platform 35 | for `make phone` and the emulator tests |
| Disk | 10 GB free | model 4.7 GB, Flutter build cache, whisper model ~1.5 GB |
| RAM / GPU | 16 GB RAM; GPU with ≥ 6 GB VRAM recommended | measured on an RTX 5050 8 GB: text model on GPU at 25 tok/s; see `docs/model_setup.md` |

## 4. First-time setup

```bash
git clone <repo> kanakku && cd kanakku
make start            # runs scripts/setup.sh, then starts; see below
make doctor           # in a second terminal: every line ✔ (· lines are optional)
```

`scripts/setup.sh` (run by every `make start`, under 2 s when nothing changed): creates `.env`; installs `uv` if missing;
creates `.venv` and installs the server when `.venv` is missing or the hash of `server/pyproject.toml` differs from
`run/setup.stamp`; installs missing system packages (tesseract + eng + mal, ffmpeg, adb; "you may be asked for your
password once"). A refused install is remembered in `run/system.declined` and not asked again until the list changes;
Malayalam is optional, the others stop the start. With the local provider `up.sh` installs Ollama if missing and
downloads the model if missing, saying its size.

## 5. Daily use

```bash
make start                  # foreground: setup check, provider choice, AI, server, adb reverse, QR + box, live log
                            # Ctrl+C or closing the terminal stops the server, the AI if we started it, adb reverse
make start PROVIDER=local   # no question (PROVIDER=meta: saved key, or asks once)
make start BG=1             # background (developers); make stop stops it
make up                     # background, no setup check or QR
make status                 # server / health / LLM / phone URL
make provider               # which provider runs, Meta calls today
make stop                   # safety net: stops a foreground make start from another terminal, or a background server
```

The live log is `scripts/log_view.py` following `run/server.log` (JSON lines, rotated): time, level, request id,
message, in colour on a terminal. A second `make start` while one runs says so and shows the box again. The QR code
holds `kanakku://connect?url=…&token=…`; Settings → Scan code reads it.

Order in which `make up` picks the provider: `PROVIDER=` on the command line → a saved `META_API_KEY`
(environment or `.env.local`) → a hidden prompt in a terminal → local (CI, `make smoke`). A Meta key is checked with one
`GET /v1/models` (10 s). Rejected / offline → it says so and asks "Use local models instead? [Y/n]"; it never starts
half-configured. `make up` also creates the LAN access token (`KANAKKU_TOKEN` in `.env.local`, mode 600) and prints it.

## 6. Phone

- **Wi-Fi:** phone and laptop on the same network. App → Settings → Server address `http://<laptop-ip>:8013`
  and Access token, both in the `make start` box, or Settings → Scan code on its QR code. "Save and test connection"
  shows the provider and the server version.
- **Firewall:** `make firewall-open` (ufw) if the phone cannot connect.
- **USB instead of Wi-Fi:** `make start` sets up `adb reverse` for connected phones; the server address is then
  `http://127.0.0.1:8013` (`make phone-usb` does it by hand).
- **Install:** `make phone` (builds a versioned release APK, installs it on the USB phone, copies the demo brochure
  to Download) or send `dist/kanakku-v*.apk` to the phone and allow "Install unknown apps".
- **Settings fields:** server address, access token (stored with flutter_secure_storage), language, "I use
  earphones", guardian view; app version, server version and model provider are shown.

## 7. Switching to Meta

1. Get a Meta Model API key from the Meta developer console of the hackathon.
2. `make start` (or `make up PROVIDER=meta`) and paste the key when asked (hidden). Say `y` to "Save this key for next
   time?" to store it in `.env.local`.
3. What changes: `LLM_BASE_URL=https://api.meta.ai/v1`, `LLM_MODEL=muse-spark-1.3`, vision on; the local Ollama is not
   started. What does not change: the pipeline, the engines, every check, speech-to-text (local faster-whisper until a
   Meta speech endpoint is confirmed), OCR, the app.
4. Spend protection (Meta only): identical prompts are answered from a SQLite cache (`LLM_CACHE=true`), and
   `META_MAX_CALLS_PER_DAY` (default 300) caps calls; at 80 % the log warns; at the cap an ask fails with
   `429 daily_limit` ("restart with: make up PROVIDER=local"), or — with `LLM_FALLBACK=local` — the local models answer
   and the answer shows a "local fallback" badge and an `llm_provider` trace step.
5. `make forget-key` deletes the saved key. `make meta-check` runs one endowment case against Meta when a key is
   present ("Meta live check skipped: no key" otherwise).

## 8. The ask flow end to end

| # | step | model call? | what happens |
|---|---|---|---|
| 1 | ingest | — | audio → faster-whisper transcript; photos → OCR; PDF/DOCX → text; evidence quotes stored with ids (`q12`); Aadhaar/PAN/account numbers stripped |
| 2 | scam_rules | — | OTP / KYC / "pay to receive" signals → red at once, no model call |
| 3 | case_builder | **1** | case type, terms with their exact words, seller claims, stock ticker (vision model when photos and vision are on; OCR fallback after 60 s, labelled "read once") |
| 4 | verify_terms | — | each term must be found in the evidence; unverified terms are excluded from maths and become questions |
| 5 | compute | — | facts from code (`engines/`, via `mcp_server/tools.py`): returns, FD comparison, EMI, effective rate, affordability, pump signals; `cmp_*` comparison facts |
| 6 | router | — | which specialists (table in §9); `unknown` → one clarifying question |
| 7 | council | **2** | one batched call for all called agents: stance, strength, ≤2 arguments each with `{fact_id}` placeholders |
| 8 | evidence | — | every argument: known placeholders only, no raw digits, comparison words need a matching `cmp_*` fact, Vick must cite a pump signal; failures are dropped with the reason |
| 9 | debate | **3** (only if D > 0.4) | one rebuttal round |
| 10 | consensus | — | weighted vote S = Σ w·s·c / Σ w (voters); S < −0.2 red, > 0.2 green; then overrides (code beats the vote): scam → red; savings cover < 1 month → red, < 3 → at most yellow; EMIs > 60 % → red, > 40 % → at most yellow; monthly shortfall → red; "guaranteed" not in the document → at least yellow; unverified required terms → at most yellow |
| 11 | privacy | — | DISCREET (default) unless earphones or "out loud": no personal amount or word (income, savings, EMI, budget…) may be spoken; those go to on-screen notes |
| 12 | explainer | **4** (+1 rewrite if budget left) | each agent's spoken line + Alfii's decision sentence; every line re-checked (evidence, privacy, style linter); failing lines regenerated once, then the agent's own argument, then dropped ("Sankz has left a note on your screen") |
| 13 | questions | — | from the code's bank per case type (`questions.py`); the model may only pick ids and lightly reword |
| 14 | save | — | verdict, lines, dropped arguments, blocked lines, trace; guardian alert for red (and big yellow) |

Limits: at most **4 model calls per ask** (`LLM_MAX_CALLS_PER_ASK`), **20 s** per text call, **60 s** per vision call,
one retry with backoff on timeouts / 429 / 5xx within that budget; any failed step marks the answer `degraded`.

**Worked example — the endowment brochure** (real facts from `make app-fixtures`; real spoken lines from the live
model in `docs/reliability_confirm.md`):

| fact | value | from |
|---|---|---|
| `term.premium` | ₹50,000 a year | brochure page 1, read twice |
| `term.pay_years` / `term.policy_years` | 15 / 15 | brochure |
| `term.sum_assured` | ₹7,50,000 (guaranteed) | brochure |
| `term.maturity_low` / `term.maturity_high` | ₹10,20,000 / ₹15,00,000 | brochure (illustration, bonuses not guaranteed) |
| `endowment_return` | 3.75 % a year (lower bonus rate) | `finance.endowment_return` |
| `f_return_high` | 8.26 % a year (higher bonus rate) | code |
| `ref.fd_rate` | 7 % (assumption, as of 2026-10-01) | `server/data/reference_rates.json` |
| `fd_value` | ₹13.44 lakh after 15 years in an FD | `finance.fd_value` |
| `cmp_return_low_vs_fd` | −3.25 percentage points | `compare.compare_rates` |

Votes: Dani against 0.9, Sankz against 0.7 → S = −0.8 → red; override `unbacked_guarantee` ("seller said guaranteed;
document does not"). Claim check: "guaranteed to give 15 lakh" → contradicted by "Bonus rates are not guaranteed and may
change every year". Spoken (discreet mode):

> **Alfii:** Let me ask Dani and Sankz.
> **Dani:** Only 7.5 lakh rupees is certain; bonuses are not promised.
> **Sankz:** Only 7.5 lakh rupees is guaranteed; bonuses are not promised.
> **Alfii:** My advice: do not go ahead with this as it is. Talk to Arun before you decide.

On screen only: "This premium is 31.2 % of your savings each year." · "After this, you would have ₹9,433 left each
month." Ask him this: "How much is guaranteed in writing?"

## 9. The council

| agent | role | voice (app, `core/speech.dart`) |
|---|---|---|
| **Alfii** | curator: routes, applies safety rules, concludes; never votes | pitch 1.0, rate 0.45 |
| **Sankz** | banking: loans, EMIs, FDs, affordability | pitch 0.85, rate 0.44 |
| **Dani** | mutual funds, SIPs, insurance-as-investment | pitch 1.2, rate 0.46 |
| **Vick** | stocks: pump-and-dump checks; never recommends buying | pitch 0.75, rate 0.47 |

| case type | called | weights |
|---|---|---|
| insurance_offer | Dani, Sankz (+ Vick if the document says market-linked) | 0.4 / 0.4 / 0.2 |
| ulip | Dani, Sankz, Vick | 0.4 / 0.4 / 0.2 |
| loan_offer, chit_fund | Sankz | 1.0 |
| sip_or_fund_question | Dani (+ Sankz if the amount is large vs savings) | 0.5 / 0.5 |
| stock_tip, shares, ipo | Vick (+ Sankz if the amount is large) | 0.6 / 0.4 |
| general_money | Sankz, Dani | 0.5 / 0.5 |
| scam_or_payment_request, out_of_scope | nobody (Alfii only, no model call for scams) | — |

## 10. API reference

Base path `/v1` (the old unversioned paths still work). Every request except `/health` and `/ready` needs
`Authorization: Bearer <KANAKKU_TOKEN>`. Errors always look like
`{"error": {"code": "file_too_large", "message": "p.png: 9.0 MB is over the 8 MB limit for image files.", "request_id": "bc553e7630c34700"}}`
and every response has `X-Request-ID`.

| method | path | body / params | answer |
|---|---|---|---|
| GET | `/health` | — | `{"status":"ok","version":"0.2.0","provider":{"name":"local","model":"qwen2.5:7b-instruct","cache":false,"spend_guard":null,"fallback":"none","auth":true},"providers":{"llm":{…},"stt":{…},"ocr":{…},"tts":{…}}}` |
| GET | `/ready` | — | 200 `{"ready":true,"checks":{"db":{"ok":true},"llm":{"ok":true}}}` or 503 |
| POST | `/v1/cases` | form: `family_id`, `text`, `earphones`, `user_says_alone`, `case_id` (follow-up), `wait` (default true), files `audio`, `files` (≤5); headers `Idempotency-Key`, `X-Device-ID` | `CaseResult` (below), or 202 `{"case_id":5,"status":"running"}` with `wait=false` |
| GET | `/v1/cases/{id}` | — | bundle: `case`, `quotes`, `terms`, `facts`, `positions`, `arguments` (incl. dropped + reason), `verdict` (score, overrides), `spoken_lines` (incl. blocked), `trace`, `result` |
| GET | `/v1/cases/{id}/events` | — | Server-Sent Events: `step_started`, `step_finished`, `alfii_opener`, `agent_called`, `agent_done`, `done` |
| POST | `/v1/cases/{id}/letter` | `{"kind":"cancel","sender_name":"Lakshmi"}` | `{"kind":"cancel","text":"…"}` ("Help me say no") |
| GET | `/v1/families/{id}/profile` | — | `{"values":[{"field":"monthly_income","status":"known","value":45000,"source":"typed"},…],"facts":[…],"members":[…],"language":"en"}` |
| POST | `/v1/families/{id}/profile` | `{"field":"savings","value":160000,"source":"typed","confirmed":true}` | profile |
| POST | `/v1/families/{id}/profile/extract` | form: `text` / `audio` / `file`, optional `field` | proposal (nothing saved): `{"values":[{"field":"monthly_income","value":45000.0,"readback":"I heard ₹45,000 a month for your income each month. Is that right?","uncertain":false,…}],"items":[],"heard":"My pension is 45,000 a month."}` |
| POST | `/v1/families/{id}/profile/confirm` | `{"values":[…confirmed…],"items":[…]}` | `{"saved":[…],"skipped":[…],"profile":{…}}` |
| GET/POST | `/v1/families/{id}/items` | POST: an item with `confirmed` | `{"items":[{"id":1,"kind":"policy","name":"Money-back policy (fictional)","amount":12000.0,"frequency":"yearly","source":"document",…}]}` |
| DELETE | `/v1/families/{id}/items/{item_id}` | — | `{"deleted":true}` |
| GET | `/v1/families/{id}/alerts` | `?status=new\|handled` | alerts with `note` (the alert), `guardian_note`, `colour`, `sentence`, `key_facts`, `agent_lines` |
| PATCH | `/v1/alerts/{id}` | `{"status":"handled"}` / `{"note":"Wait for me"}` (the guardian's note) | `{"updated":true}` |
| GET | `/v1/families/{id}/notes` | — | `[{"from":"Arun","note":"Please wait for me before you sign.","at":"…","case_id":7}]` |

`CaseResult` (abridged, real loan answer):

```json
{"case_id": 3, "case_type": "loan_offer", "called_agents": ["sankz"], "privacy_mode": "discreet",
 "verdict": {"colour": "red", "sentence": "Do not take this loan as offered; ask for the reducing-balance rate first.",
             "questions": ["What is the reducing-balance interest rate?"]},
 "short_answer": {"text": "Please don't go ahead with this as it is.", "colour": "red"},
 "council": [{"speaker": "alfii", "text": "Let me ask Sankz.", "kind": "opener"},
             {"speaker": "sankz", "text": "This flat-rate loan really costs about 21.6 percent a year.", "kind": "agent"},
             {"speaker": "alfii", "text": "Do not take this loan as offered; ask for the reducing-balance rate first.", "kind": "conclusion"}],
 "screen_details": [{"id": "note.emi_share", "label": "Your EMIs would take 16.8% of your income.", "kind": "personal",
                     "source": "Kanakku note · only on your screen"}, "…"],
 "claims": [], "suggested_followups": ["…"], "llm_calls": 3, "degraded": false, "degraded_steps": [],
 "provider": "local", "local_fallback": false, "request_id": "…", "council_words": 27, "council_seconds": 10.8}
```

Limits: audio 10 MB, image 8 MB each, PDF/DOCX 15 MB, 5 files, types checked by content (413 / 415); 20 asks a minute
per device (429); request timeout 180 s (504).

## 11. Testing

| what | command | notes |
|---|---|---|
| server unit + API + e2e (offline) | `make test` | 400+ tests, LLM mocked by `tests/fixtures/llm/*.json` |
| `make up` paths with a fake Meta server | `cd server && ../.venv/bin/python -m pytest tests/test_make_up.py` | flag, saved key, typed key (pty), Enter, invalid key, daily cap, 429 once, key never logged |
| lint | `make lint` | ruff |
| real-model reliability | `make reliability RUNS=5` (+ `--full` via the script) | 5 cases × N; reports in `docs/reliability*.md` |
| framing / vision | `make reliability-framing`, `make reliability-vision` | |
| Meta live check | `make meta-check` | needs a real key |
| app: analyze + widget + screenshot tests | `make app-test` | fixtures from `make app-fixtures`; screenshots `make app-goldens` → `docs/screens/` |
| app on a device vs the real server | `make app-integration` | emulator or USB phone; records `docs/demo_run.mp4` |

**Reading `docs/reliability*.md`:** the first table has one row per case: JSON validity, arguments kept / dropped,
the verdict of every run (and how many matched the expectation), model calls and latency. Then: dropped-argument
reasons, auto-placeholder rewrites, linter rejections, red runs (short answer + Alfii's final line), every question
asked, and "What the user gets" (the full council of the first run).

## 12. Releasing the app

`make app-release` (Android) / `make app-ios` (macOS + Xcode only) bump the build number in `app/pubspec.yaml`
(`BUMP=build|patch|minor`), build a release, commit the bump, copy the file to `dist/kanakku-vX.Y.Z+N-<sha>.apk` and add a
row to `dist/RELEASES.md`. The access token is never baked into a release build. Signing uses
`app/android/key.properties` if present, else the debug key. iOS: open `app/ios/Runner.xcworkspace` once in Xcode to set
the team; the Info.plist already has microphone / camera / photo texts and local-network HTTP.

## 13. Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `model not pulled: make llm-pull` in /health | Ollama has no `qwen2.5:7b-instruct` | `make llm-pull` |
| photos of Malayalam papers read badly | Tesseract `mal` missing | `sudo apt install tesseract-ocr-mal`, then set `OCR_LANGS=eng+mal` in `.env` |
| phone: "I can't reach the server" | different Wi-Fi, firewall, or the laptop's address changed | `make start` shows the address; `make firewall-open`; or `make phone-usb` |
| app: "access token is missing or wrong" (401) | token not typed or old | copy the `Token` line from `make start` into Settings |
| photo answers say "read once" / slow | the vision model runs on the CPU and times out (60 s) → OCR fallback | expected on 8 GB GPUs; see `docs/model_setup.md`; Meta has vision |
| Ollama out of GPU memory | two models loaded | stop and `make start` again (only the text model loads), or unset `LLM_VISION_MODEL` |
| Meta: "key rejected" (401) | wrong / expired key | `make forget-key`, then `make start` and paste the new key |
| Meta: `429 daily_limit` | `META_MAX_CALLS_PER_DAY` reached | wait until midnight, `make up PROVIDER=local`, or `LLM_FALLBACK=local` |
| `make up` / `make llm-pull` hang; doctor: "frozen" | Ollama paused with Ctrl+Z: it holds port 11434 but does not answer | `killall -9 ollama`, then `make start` |
| `port 8013 is already used` | another program | close it, or set `PORT=8014` in `.env` |
| anything else | | `make doctor`, then `run/server.log` (request id in the app's error matches the log line) |

## 14. Demo checklist (video)

1. `make start` (choose Meta or Enter for local) · in a second terminal `make demo` (resets the family, prints the 4
   questions).
2. Phone: Settings → Save and test connection → "Connected ✔ Provider: …".
3. Question 1 with the brochure (camera button → Choose a PDF) → Working (live steps) → **Stop** → the council speaks
   → Why (sources, "read twice") → Help me say no.
4. Question 2 (loan), question 3 (stock tip: Vick names the 222 % jump), question 4 (OTP scam: instant red).
5. Long-press "Kanakku" → Under the hood: router decision, facts tagged offer/personal, dropped arguments, vote maths,
   overrides, privacy blocks, provider.
6. Settings → Guardian view → the alert → Note for Amma → back to Amma's Home: "A note from Arun".

## 15. Built during the hackathon vs prior work

All code in this repository was written during the Meta AI Developer Hackathon (Oct 27 – Nov 4 2026). The consensus
idea (weighted specialist vote with safety overrides) comes from our earlier project **IFA** (patent pending), which is
not in this repository and from which no code was copied.

| user story | status |
|---|---|
| Ask a money question by voice or text | done (hold-and-talk + text; STT English for now) |
| Show a brochure / offer photo or PDF | done (OCR + optional vision model; "read twice" vs "read once") |
| Red / yellow / green verdict with one plain sentence | done (colour + icon + word) |
| Hear each specialist's short line | done (council playback, one voice each) |
| Every number checked and sourced ("Why?") | done (evidence checker, sources per number) |
| Personal figures stay private unless alone / earphones | done (discreet default; on-screen notes) |
| Questions to ask the seller | done (code-owned bank) |
| Scam warning without waiting | done (code fast path) |
| Guardian alert and note for Amma | done |
| Onboarding and My details with read-back and confirm | done |
| Malayalam / Hindi answers | partly (answers and templates; UI text English; native review pending) |
| Switch to Meta Model API with spend protection | done (tested with a fake Meta server; real key not tested) |
| Works when the internet drops | done (queue + retry, idempotent resend) |
| iOS | builds need a Mac (not verified) |
