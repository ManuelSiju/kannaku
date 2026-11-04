# Kanakku

**A money adviser for Indian families, built on Meta Muse Spark.**

Before you pay for an insurance plan, take a loan, follow a stock tip or answer a strange call, show it to Kanakku. A council
of AI specialists answers red, yellow or green, in one plain sentence, with the exact questions to ask. Every number is
computed by code, never by the AI.

Built for the Meta AI Developer Hackathon (27 Oct – 4 Nov 2026). Decision support, not investment advice.

<p>
  <img src="docs/screens/verdict_endowment_red@1.0.png" width="230" alt="A red verdict">
  <img src="docs/screens/working@1.0.png" width="230" alt="The council at work">
  <img src="docs/screens/under_hood@1.0.png" width="230" alt="Under the hood">
</p>

## The problem

In one year, life insurers in India received 26,667 complaints of unfair selling (IRDAI Annual Report 2024-25). Most families
have no adviser to turn to at the moment a seller is sitting in front of them. Kanakku is built for that moment.

## What it does

- **Reads the paper.** Show a brochure, offer or statement as a PDF or photo, and ask your question.
- **Checks it with a council.** Sankz (banking), Dani (funds and insurance) and Vick (stock tips) argue from facts, and Alfii
  concludes, out loud, in different voices.
- **Stops scams at once.** OTP and KYC tricks are caught by rules, with no AI call.
- **Keeps a family in the loop.** A red answer appears in the guardian's view, who can call or leave a note.
- **Knows the whole family.** Each value has an owner. A member's money stays out of the family budget unless the family says
  so, and mutual fund, share and SIP statements become facts.
- **Stays private.** A family's own figures stay on screen and are spoken only when the listener is private.

## Verify in 5 minutes

No key is needed. This runs the 5 demo cases and serves the app from
[recorded real Meta replies](server/demo_assets/replay/), each labelled "replay of recorded Meta call":

```bash
git clone <repo-url> kanakku && cd kanakku
make demo-replay
```

| question | expected |
|---|---|
| Endowment brochure: "guaranteed to give 15 lakh" | Stop: only 7.5 lakh is written as guaranteed |
| Loan of 1,00,000 at 12% flat for 24 months | Stop or Careful: the real rate is 21.6% |
| ZEPHYRX stock tip | Stop: a 222% jump and a high pump-and-dump risk |
| Bank caller asking for an OTP | Stop, with no model call |
| "How do I make sambar?" | Politely out of scope |

## Use of Meta AI

Kanakku uses two Meta models and Muse Spark's vision, each where it does something the rest of the system cannot. Every row was
run live, and the model id is the one Meta returned, not our setting.

| step | Meta model | setting | why | proof | median time |
|---|---|---|---|---|---|
| Hearing the question | `muse-voice-transcribe-1.0` | keyword bias for lakh, EMI, KYC and the council's names | hears Indian money words a general model misses | [meta run](docs/reports/meta_run.md) | 3.7 s for a short question |
| Case builder | `muse-spark-1.3` | `json_object`, `minimal` reasoning | classifies the case and copies the terms | [meta run](docs/reports/meta_run.md) | 2.8–5.5 s |
| Reading photos | `muse-spark-1.3` vision | checked against Tesseract | two independent readings: both must agree for "read twice" | [meta run](docs/reports/meta_run.md) | within the case builder |
| Council | `muse-spark-1.3` | `json_object`, `minimal` reasoning | specialists argue from fact ids, as one structured call | [reliability](docs/reports/reliability_meta.md) | 9.6–12.8 s |
| Explainer | `muse-spark-1.3` | `json_object`, `minimal` reasoning | plain spoken lines, checked again by code | [reliability](docs/reports/reliability_meta.md) | 9.9–19.8 s |

**What building on Muse Spark taught us:**

- **Reasoning effort is a real dial.** A reasoning model spent 300 tokens to say "ok". Under a 20 second budget only `minimal`
  gave every expected verdict with nothing degraded, while `low` and `high` timed out ([measurements](docs/reports/effort_matrix.md)).
- **Structured output needs care.** `json_schema` ran to the token limit on the same request that `json_object` finished in
  13 seconds, so the schema stays in the prompt and code validates the reply.
- **Keyword biasing changed the result.** With our word list it heard "Dani and Sankz" where Whisper heard "Ghanian Sanks".
- **The model argues, code decides.** Muse Spark never writes a number, and a safety rule can overrule its vote.

If Muse Voice Transcribe fails, the local Whisper model takes over and the trace says so.

## How it works

```mermaid
flowchart LR
    App["Flutter app"] -- "HTTP + token" --> API["FastAPI /v1"]
    API -- "JSON + live events" --> App
    API --> Pipeline["Ask pipeline"]
    Pipeline --> Engines["Number engines<br/>and MCP tools"]
    Pipeline --> Models["Model providers<br/>LLM, speech, OCR"]
    Engines --> DB[("SQLite")]
    Pipeline --> DB
    Models --> LLM["Meta Muse Spark<br/>or local Ollama"]
```

| step | what happens |
|---|---|
| Ingest | Voice, photos and PDFs become text and evidence quotes |
| Scam rules | Code spots OTP and KYC scams and answers red at once |
| **Case builder** | The model identifies the case type, terms and seller claims |
| Verify and compute | Each term is checked against the evidence, then code computes the facts |
| **Council** | Specialists argue using fact ids only; unsupported arguments are dropped |
| **Debate** | One rebuttal round, only on disagreement |
| Consensus | Weighted vote, then safety rules that overrule it |
| Privacy | Personal figures are kept off the spoken lines |
| **Explainer** | Plain spoken lines, each one checked again |
| Questions | Chosen from a fixed bank per case type |

Bold steps use the model: at most 4 calls per question, 20 seconds each, with a visible flag if a step fails.

**Numbers cannot be invented.** The model writes `{fact_id}` placeholders and code fills in the value. A line with a digit of
its own is dropped. Each term must be found in the paper, and a comparison such as "higher than a fixed deposit" comes from
code with its condition attached.

The [project guide](docs/PROJECT_GUIDE.md) covers every step, function and setting.

## Evidence

| check | result | report |
|---|---|---|
| Live on Meta | All demo cases answered as expected; in the latest run one council call timed out and the answer was flagged | [meta_run](docs/reports/meta_run.md) |
| Number audit | 22 figures recomputed without our engines, 0 mismatches | [numbers_audit](docs/reports/numbers_audit.md) |
| Calibration on Meta, 3 runs each | Greens 12/12, reds 21/21, yellows 7 yellow and 5 red: no risky case came out green | [calibration](docs/reports/calibration.md) |
| Reliability on Meta, 5 cases × 3 | 15 of 15 as expected, 1 run degraded | [reliability](docs/reports/reliability_meta.md) |
| Framing on Meta, 3 framings × 2 | Never green; one framing gave yellow, not red | [framing](docs/reports/reliability_framing_meta.md) |
| Prompt injection in a brochure | Never green; the text is treated as data | [QA report](docs/reports/qa_final.md) |
| Automated tests | 534 server and 66 app tests | `make test`, `make app-test` |
| Real phone | Samsung A73, Android 16: install, asks, uploads, guardian note, voices recorded | [QA report](docs/reports/qa_final.md) |

Every claim is listed with its status in the [claims audit](docs/reports/claims_audit.md). Early reactions, on the local
models, are in [user feedback](docs/user_feedback.md).

## Run it live

Requires Linux with `git`, `curl` and `make`, 10 GB of free disk and 16 GB of RAM.

```bash
make start
```

`make start` installs what it needs, asks for a Meta API key (press Enter to use the local model), and shows a QR code with a
live log. Ctrl+C stops everything.

To install the app, connect an Android phone with USB debugging on and run `make phone`. This needs
[Flutter](https://docs.flutter.dev/get-started/install/linux/android) 3.41 and the Android SDK. In the app, open
**Settings → Scan code** and scan the QR code.

| command | what it does |
|---|---|
| `make start` | Set up if needed, start Kanakku, show the live log |
| `make phone` | Build the app and install it on the phone |
| `make demo` | Reset the fictional demo family and print the demo questions |
| `make demo-replay` | Run on recorded Meta replies, no key needed |
| `make meta-run` | Repeat the live Meta proof |
| `make doctor` | Check everything; each problem comes with its fix |
| `make test` | Run the server tests |
| `make stop` | Stop Kanakku if Ctrl+C was not possible |
| `make help` | List every command |

## Tech stack

| layer | tools |
|---|---|
| App | Flutter, shadcn_ui, provider |
| Server | Python 3.11, FastAPI, Pydantic, SQLite |
| Models | Meta Muse Spark and Muse Voice Transcribe, or Ollama (`qwen2.5:7b-instruct`) and faster-whisper; Tesseract |
| Tools | MCP server over the same functions the pipeline uses |

## Project layout

```
app/        Flutter app (Android)
server/     FastAPI server, pipeline, engines, providers, tests
scripts/    Scripts behind the Makefile
docs/       Project guide, evidence reports, screenshots, user feedback
```

## From prototype to product

A family's money lives in separate places: bank statements, policies, loans, demat accounts and old paper files. Each seller
sees one piece, and nobody looks at the whole picture on the family's side. Our vision is a personal AI assistant that keeps
that picture in sync with the family's consent and guides them before each decision.

None of this is built yet. The next steps are consent-based data through Account Aggregators, Malayalam and Hindi speech and
app text, and reaching families through co-operative banks.

## Known limits

- Speech is English only, and the phone's microphone path has not been tried with a real voice. Transcription can repeat a
  word or digit ("7.5 5 lakh" in one test).
- Answers can be in Malayalam and Hindi, but the app's own text is English and native review is pending.
- There are no push notifications: guardian alerts appear when the Alerts tab is opened.
- A model can vary between runs, so the same case can move between yellow and red.
- A Meta call can pass the 20 second limit. The answer then says "partly checked".
- Android only.

## Prior work

All code in this repository was written during the hackathon. The consensus idea, a weighted vote of specialists with safety
overrides, comes from our earlier project **IFA** (patent pending), which is not in this repository; no code was copied from
it. The demo family, brochure, loan offer and share (ZEPHYRX) are fictional.

## Licence

[MIT](LICENSE)
