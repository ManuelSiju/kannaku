# Vision test (brochure photos)

Model `qwen2.5:7b-instruct (+ vision qwen2.5vl:7b)` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 15:20.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment_photos | 3 | 6/10 · 0 · 0 | 5 / 3 | ⚪ 🔴 🟡 (1/3 as expected) | 2, 4, 4 | 3 | 81.5 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment_photos | 2.2 | 0.0 | 78.3 | 0.0 | 0.0 | 0.0 | 10.8 | – | 0.0 | 7.0 |

Dropped-argument reasons:

- 2× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 1× comparison 'higher' needs a cited cmp_* fact saying 'higher'

Step errors:

- 1× case_builder: LLMStepFailed: LLM call failed: APITimeoutError: Request timed out.

Terms per run:

- run 1: no terms; confirmed by OCR: none
- run 2: premium=50000, pay_years=15, policy_years=15, sum_assured=750000, maturity_low=1.02e+06, bonus_rate_low=0.04, maturity_high=1.5e+06, bonus_rate_high=0.08; confirmed by OCR: none
- run 3: premium=50000, pay_years=15, policy_years=15, sum_assured=750000, maturity_low=1.02e+06, maturity_high=1.5e+06, bonus_rate_low=0.04, bonus_rate_high=0.08; confirmed by OCR: none

Auto-placeholder / short-id rewrites (every one):

- endowment_photos run 3: council: auto_placeholder '15 years' -> {term.pay_years}
- endowment_photos run 3: explainer: auto_placeholder '₹7.5 lakh' -> {term.sum_assured}
- endowment_photos run 3: explainer: auto_placeholder '₹7.5 lakh' -> {term.sum_assured}
- endowment_photos run 3: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}

Linter rejections per rule:

- 1× too_many_numbers

Council length: endowment_photos 53 words / 21 s (median)

## What the user gets (first run of each case)

### endowment_photos (discreet mode) — None

**Short answer:** Is this about a loan, a policy, an investment or a payment?

**Council** (12 words, ~5 s):

> alfii (conclusion): Is this about a loan, a policy, an investment or a payment?  

**On-screen notes:** none

**Questions to ask:** none

**Suggested follow-ups:** none

