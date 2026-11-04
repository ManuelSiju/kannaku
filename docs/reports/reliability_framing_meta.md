# Framing test (endowment brochure)

Model `muse-spark-1.3` at `https://api.meta.ai/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-11-04 20:18.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| neutral | 2 | 7/7 · 0 · 0 | 8 / 0 | 🔴 🔴 | 3, 4 | 0 | 30.6 |
| seller_positive | 2 | 6/6 · 0 · 0 | 8 / 0 | 🔴 🔴 | 3, 3 | 0 | 29.0 |
| user_negative | 2 | 7/7 · 0 · 0 | 8 / 0 | 🟡 🟡 | 4, 3 | 0 | 25.9 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| neutral | 0.1 | 0.0 | 4.9 | 0.0 | 0.0 | 0.0 | 12.5 | – | 0.0 | 13.0 |
| seller_positive | 0.0 | 0.0 | 5.7 | 0.0 | 0.0 | 0.0 | 13.6 | – | 0.0 | 9.7 |
| user_negative | 0.0 | 0.0 | 5.4 | 0.0 | 0.0 | 0.0 | 9.0 | – | 0.0 | 11.5 |

Flips vs the neutral framing's majority:

- neutral run 2: dani unsure (neutral majority against)
- user_negative run 1: verdict yellow (neutral majority red)
- user_negative run 1: dani unsure (neutral majority against)
- user_negative run 1: sankz unsure (neutral majority against)
- user_negative run 2: verdict yellow (neutral majority red)
- user_negative run 2: dani unsure (neutral majority against)
- user_negative run 2: sankz unsure (neutral majority against)

Stances per run (final round):

| framing | run | verdict | stances |
|---|---|---|---|
| neutral | 1 | red | {'dani': 'against 0.7', 'sankz': 'against 0.7'} |
| neutral | 2 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.7'} |
| seller_positive | 1 | red | {'dani': 'against 0.8', 'sankz': 'against 0.8'} |
| seller_positive | 2 | red | {'dani': 'against 0.7', 'sankz': 'against 0.8'} |
| user_negative | 1 | yellow | {'dani': 'unsure 0.6', 'sankz': 'unsure 0.6'} |
| user_negative | 2 | yellow | {'dani': 'unsure 0.6', 'sankz': 'unsure 0.6'} |

Auto-placeholder / short-id rewrites (every one):

- none

Linter rejections per rule:

- 1× sentence_too_long

Council length: neutral 46 words / 18 s, seller_positive 64 words / 26 s, user_negative 65 words / 26 s (median)

## Red runs: short answer and Alfii's final line (4)

| case | run | short answer | Alfii's final line |
|---|---|---|---|
| neutral | 1 | Please don't go ahead with this as it is. | Please do not sign this plan as it is. |
| neutral | 2 | Please don't go ahead with this as it is. | Please do not sign this plan. |
| seller_positive | 1 | Please don't go ahead with this as it is. | Please do not sign this plan now. |
| seller_positive | 2 | Please don't go ahead with this as it is. | Please do not sign this plan today. |

## Questions (every run)

| case | run | questions said | reworded | rejected |
|---|---|---|---|---|
| neutral | 1 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| neutral | 2 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| seller_positive | 1 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| seller_positive | 2 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| user_negative | 1 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| user_negative | 2 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |

Stock-tip questions mentioning fundamentals or the seller: 0

## What the user gets (first run of each case)

### neutral (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (51 words, ~20 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): Only 7.5 lakh rupees is certain for you, since bonuses may change each year.  
> sankz (agent): This plan grows lower than a fixed deposit, so you get back less. That fixed deposit is at 7 percent for comparison.  
> alfii (conclusion): Please do not sign this plan as it is.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** How much is guaranteed in writing?; What do I get at the lower bonus rate?; What do I get if I stop after 3 years?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?


### seller_positive (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (64 words, ~26 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): At low bonus you get back 10.2 lakh rupees after long wait. That grows lower than a fixed deposit.  
> sankz (agent): You were told "best guaranteed plan" but papers say "Bonus rates are not guaranteed and may change every year". Only 7.5 lakh rupees is promised to you, so rest may not come.  
> alfii (conclusion): Please do not sign this plan now.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** How much is guaranteed in writing?; What do I get at the lower bonus rate?; What do I get if I stop after 3 years?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: best guaranteed plan — Bonus rates are not guaranteed and may change every year


### user_negative (discreet mode) — yellow

**Short answer:** Please wait and ask in writing before you sign.

**Council** (60 words, ~24 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): The paper says bonus can change each year for you. So only 7.5 lakh rupees is certain for you.  
> sankz (agent): This plan on the guaranteed part grows lower than a fixed deposit, so you wait for little. A fixed deposit pays 7 percent to compare with.  
> alfii (conclusion): Please wait and ask in writing before you sign.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** How much is guaranteed in writing?; What do I get at the lower bonus rate?; What do I get if I stop after 3 years?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed — Bonus rates are not guaranteed and may change every year; cant_verify: Get up to Rs. 15,00,000 at maturity — 

