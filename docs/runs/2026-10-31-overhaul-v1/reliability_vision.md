# Vision test (brochure photos)

Model `qwen2.5:7b-instruct (+ vision qwen2.5vl:7b)` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 14:55.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment_photos | 3 | 9/12 · 0 · 0 | 6 / 6 | 🔴 🟡 🔴 (2/3 as expected) | 4, 4, 4 | 3 | 97.4 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment_photos | 2.1 | 0.0 | 76.7 | 0.0 | 0.0 | 0.0 | 11.4 | – | 0.0 | 6.9 |

Dropped-argument reasons:

- 3× comparison 'higher' needs a cited cmp_* fact saying 'higher'
- 2× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 1× comparison 'less' needs a cited cmp_* fact saying 'lower'

Terms per run:

- run 1: premium=50000, pay_years=15, policy_years=15, sum_assured=750000, bonus_rate_low ✗ could not read a number, bonus_rate_high ✗ could not read a number; confirmed by OCR: none
- run 2: premium=50000, pay_years=15, policy_years=15, sum_assured=750000, maturity_low=1.02e+06, maturity_high=1.5e+06, bonus_rate_low ✗ could not read a number, bonus_rate_high ✗ could not read a number; confirmed by OCR: none
- run 3: premium=50000, pay_years=15, policy_years=15, sum_assured=750000, maturity_low=1.02e+06, maturity_high=1.5e+06, bonus_rate_low ✗ could not read a number, bonus_rate_high ✗ could not read a number; confirmed by OCR: none

Auto-placeholder / short-id rewrites (every one):

- none

Linter rejections per rule:

- none

Agent turns dropped after regeneration + fallback:

- 1× sankz

Council length: endowment_photos 40 words / 16 s (median)

## What the user gets (first run of each case)

### endowment_photos (discreet mode) — red

**Short answer:** Do not sign without seeing it in writing.

**Council** (40 words, ~16 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): Only 7.5 lakh rupees is guaranteed, not the bonus-based amounts.  
> sankz (agent): Only 7.5 lakh rupees is guaranteed, not the bonus-based amounts.  
> alfii (conclusion): Do not sign without seeing it in writing. Ask about the guaranteed amount only.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** Can you show me in writing the higher bonus rate?; What bonuses can I expect in the first few years?; Can you show me in writing the lower bonus rate?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed to give 15 lakh — Bonus rates are not guaranteed and may change every year

