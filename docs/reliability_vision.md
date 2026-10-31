# Vision test (brochure photos)

Model `qwen2.5:7b-instruct (+ vision qwen2.5vl:7b)` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 14:05.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment_photos | 3 | 0/3 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ (0/3 as expected) | 1, 1, 1 | 3 | 21.2 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment_photos | 1.2 | 0.0 | 20.0 | – | – | – | – | – | – | – |

Step errors:

- 3× case_builder: LLMStepFailed: LLM call failed: APITimeoutError: Request timed out.

Terms per run:

- run 1: no terms; confirmed by OCR: none
- run 2: no terms; confirmed by OCR: none
- run 3: no terms; confirmed by OCR: none

Auto-placeholder / short-id rewrites (every one):

- none

Sample spoken lines (2 per case, from the first run; Alfii's opener is a fixed template):

**endowment_photos**

> alfii: Is this about a loan, a policy, an investment or a payment?  

