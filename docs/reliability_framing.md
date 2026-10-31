# Framing test (endowment brochure)

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 15:15.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| neutral | 3 | 12/12 · 0 · 0 | 8 / 4 | 🟡 🔴 🔴 | 4, 4, 4 | 0 | 35.5 |
| seller_positive | 3 | 12/12 · 0 · 0 | 8 / 4 | 🔴 🔴 🔴 | 4, 4, 4 | 0 | 34.6 |
| user_negative | 3 | 11/11 · 0 · 0 | 9 / 3 | 🔴 🟡 🔴 | 4, 3, 4 | 0 | 34.7 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| neutral | 0.0 | 0.0 | 15.0 | 0.0 | 0.0 | 0.0 | 9.9 | – | 0.0 | 10.5 |
| seller_positive | 0.0 | 0.0 | 15.3 | 0.0 | 0.0 | 0.0 | 10.4 | – | 0.0 | 9.0 |
| user_negative | 0.0 | 0.0 | 15.1 | 0.0 | 0.0 | 0.0 | 9.7 | – | 0.0 | 9.4 |

Dropped-argument reasons:

- 4× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 2× unknown placeholder(s): term.flat_rate
- 1× unknown placeholder(s): cmp_effective_vs_typical
- 1× unknown citation id(s): cmp_return_guaranteed_vs_fd
- 1× unknown placeholder(s): term.flat_rate, loan_effective_rate
- 1× comparison 'better' needs a cited cmp_* fact saying 'higher'
- 1× unknown citation id(s): cmp_effective_vs_typical

Flips vs the neutral framing's majority:

- neutral run 1: verdict yellow (neutral majority red)
- neutral run 1: sankz unsure (neutral majority against)
- user_negative run 2: verdict yellow (neutral majority red)
- user_negative run 2: sankz unsure (neutral majority against)

Stances per run (final round):

| framing | run | verdict | stances |
|---|---|---|---|
| neutral | 1 | yellow | {'dani': 'unsure 0.6', 'sankz': 'unsure 0.0'} |
| neutral | 2 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| neutral | 3 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| seller_positive | 1 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| seller_positive | 2 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| seller_positive | 3 | red | {'dani': 'unsure 0.7', 'sankz': 'against 0.9'} |
| user_negative | 1 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |
| user_negative | 2 | yellow | {'dani': 'unsure 0.6', 'sankz': 'unsure 0.0'} |
| user_negative | 3 | red | {'dani': 'unsure 0.6', 'sankz': 'against 0.8'} |

Auto-placeholder / short-id rewrites (every one):

- seller_positive run 1: council: auto_placeholder '8%' -> {term.bonus_rate_high}
- seller_positive run 1: explainer: auto_placeholder '7%' -> {ref.fd_rate}
- seller_positive run 3: council: auto_placeholder '8%' -> {term.bonus_rate_high}
- user_negative run 1: explainer: auto_placeholder '7%' -> {ref.fd_rate}

Linter rejections per rule:

- 3× too_many_numbers
- 2× sentence_too_long

Agent turns dropped after regeneration + fallback:

- 3× dani
- 2× sankz

Council length: neutral 34 words / 14 s, seller_positive 60 words / 24 s, user_negative 42 words / 17 s (median)

## What the user gets (first run of each case)

### neutral (discreet mode) — yellow

**Short answer:** Let's compare this with a fixed deposit first.

**Council** (34 words, ~14 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): This plan grows higher than a fixed deposit, but costs more each year.  
> alfii (conclusion): Let's compare this with a fixed deposit first. Ask about the real yearly interest rate.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** What are your expectations for future bonus rates?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?


### seller_positive (discreet mode) — red

**Short answer:** Let us not rush.

**Council** (40 words, ~16 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): Bonuses are not guaranteed; they may change every year.  
> sankz (agent): The plan's higher return higher than the FD is not certain due to variable bonuses.  
> alfii (conclusion): Let us not rush. Ask for a written guarantee first.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** Is there any way to lock in these bonus rates?; What happens if the bonus rate drops below 4 percent?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: best guaranteed plan — Bonus rates are not guaranteed and may change every year


### user_negative (discreet mode) — red

**Short answer:** Let's compare this plan with a fixed deposit first.

**Council** (35 words, ~14 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): The 7.5 lakh rupees is certain, but the bonus-based amounts are not guaranteed.  
> alfii (conclusion): Let's compare this plan with a fixed deposit first. Ask about the real yearly interest rate.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** Is there any guarantee of the bonus rates?; What are the terms for surrendering the policy?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

