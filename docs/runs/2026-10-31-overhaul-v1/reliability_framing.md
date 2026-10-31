# Framing test (endowment brochure)

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 14:51.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| neutral | 3 | 10/10 · 0 · 0 | 7 / 5 | 🟡 🔴 🔴 | 4, 3, 3 | 0 | 33.5 |
| seller_positive | 3 | 12/12 · 0 · 0 | 5 / 5 | 🔴 🟡 🟡 | 4, 4, 4 | 1 | 34.6 |
| user_negative | 3 | 10/10 · 0 · 0 | 9 / 3 | 🔴 🔴 🔴 | 3, 3, 4 | 0 | 26.9 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| neutral | 0.0 | 0.0 | 15.2 | 0.0 | 0.0 | 0.0 | 9.3 | – | 0.0 | 6.7 |
| seller_positive | 0.0 | 0.0 | 15.3 | 0.0 | 0.0 | 0.0 | 10.3 | – | 0.0 | 9.5 |
| user_negative | 0.0 | 0.0 | 11.6 | 0.0 | 0.0 | 0.0 | 8.6 | – | 0.0 | 7.4 |

Dropped-argument reasons:

- 3× no evidence cited
- 2× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 1× raw number in text ('not; at 4% bonus,'); numbers must be {fact_id} placeholders
- 1× raw number in text ('higher 8% bonus'); numbers must be {fact_id} placeholders
- 1× raw number in text ('ain; at 4% bonus,'); numbers must be {fact_id} placeholders
- 1× raw number in text ('t after 15 years:'); numbers must be {fact_id} placeholders
- 1× raw number in text ('t  over 15 years,'); numbers must be {fact_id} placeholders
- 1× comparison 'better' needs a cited cmp_* fact saying 'higher'
- 1× raw number in text ('rate of 8% is ill'); numbers must be {fact_id} placeholders
- 1× comparison 'less' needs a cited cmp_* fact saying 'lower'

Flips vs the neutral framing's majority:

- neutral run 1: verdict yellow (neutral majority red)
- neutral run 1: sankz unsure (neutral majority against)
- neutral run 2: dani against (neutral majority unsure)
- seller_positive run 2: verdict yellow (neutral majority red)
- seller_positive run 2: sankz unsure (neutral majority against)
- seller_positive run 3: verdict yellow (neutral majority red)

Stances per run (final round):

| framing | run | verdict | stances |
|---|---|---|---|
| neutral | 1 | yellow | {'dani': 'unsure 0.0', 'sankz': 'unsure 0.0'} |
| neutral | 2 | red | {'dani': 'against 0.7', 'sankz': 'against 0.8'} |
| neutral | 3 | red | {'dani': 'unsure 0.7', 'sankz': 'against 0.8'} |
| seller_positive | 1 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| seller_positive | 2 | yellow | {'dani': 'unsure 0.7', 'sankz': 'unsure 0.0'} |
| seller_positive | 3 | yellow | {'dani': 'unsure 0.6'} |
| user_negative | 1 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| user_negative | 2 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| user_negative | 3 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |

Auto-placeholder / short-id rewrites (every one):

- user_negative run 3: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- user_negative run 3: explainer: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}

Linter rejections per rule:

- none

Agent turns dropped after regeneration + fallback:

- 3× sankz

Council length: neutral 50 words / 20 s, seller_positive 63 words / 25 s, user_negative 49 words / 20 s (median)

## What the user gets (first run of each case)

### neutral (discreet mode) — yellow

**Short answer:** Let's compare this plan with a fixed deposit and see if it makes sense.

**Council** (56 words, ~22 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): There is a simpler way to protect your family. A plain term plan and a small SIP can do the job better.  
> alfii (conclusion): Let's compare this plan with a fixed deposit and see if it makes sense. Before you decide, ask: "Can you show me in writing the higher bonus rate?"  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** Can you show me in writing the higher bonus rate?; Can you show me in writing the lower bonus rate?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?


### seller_positive (discreet mode) — red

**Short answer:** Do not sign without seeing both possible returns in writing first.

**Council** (46 words, ~18 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): The guaranteed 7.5 lakh rupees is good, but bonuses are uncertain and may change.  
> sankz (agent): Only 7.5 lakh rupees is guaranteed; the bonus-based amounts are not certain and may change.  
> alfii (conclusion): Do not sign without seeing both possible returns in writing first.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** Can you show me in writing the higher bonus rate?; Can you show me in writing the lower bonus rate?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: best guaranteed plan — Bonus rates are not guaranteed and may change every year


### user_negative (discreet mode) — red

**Short answer:** Let us compare it with a fixed deposit first.

**Council** (47 words, ~19 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): This plan grows higher than a fixed deposit, but only on the bonus part.  
> sankz (agent): Only 7.5 lakh rupees is guaranteed; the rest is uncertain and risky.  
> alfii (conclusion): Let us compare it with a fixed deposit first. Ask about the real yearly return.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** What do I get at the lower bonus rate?; Can you show me in writing the higher bonus rate?; What are the terms for surrendering before maturity?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

