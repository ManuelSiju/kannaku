# Framing test (endowment brochure)

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 14:04.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| neutral | 3 | 12/12 · 0 · 0 | 9 / 3 | 🔴 🔴 🔴 | 4, 4, 4 | 0 | 37.8 |
| seller_positive | 3 | 12/12 · 0 · 0 | 7 / 5 | 🔴 🔴 🔴 | 4, 4, 4 | 0 | 35.9 |
| user_negative | 3 | 10/10 · 0 · 0 | 6 / 5 | 🔴 🔴 🔴 | 3, 4, 3 | 0 | 34.8 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| neutral | 0.0 | 0.0 | 12.0 | 0.0 | 0.0 | 0.0 | 15.0 | – | 0.0 | 11.2 |
| seller_positive | 0.0 | 0.0 | 12.8 | 0.0 | 0.0 | 0.0 | 13.2 | – | 0.0 | 10.1 |
| user_negative | 0.0 | 0.0 | 11.9 | 0.0 | 0.0 | 0.0 | 14.5 | – | 0.0 | 8.8 |

Dropped-argument reasons:

- 2× comparison 'lower' needs a cited cmp_* fact saying 'lower'
- 2× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 2× comparison 'less' needs a cited cmp_* fact saying 'lower'
- 1× raw number in text ('At an 8% bonus'); numbers must be {fact_id} placeholders
- 1× unknown placeholder(s): cmp_effective_vs_quoted
- 1× comparison 'higher' needs a cited cmp_* fact saying 'higher'
- 1× raw number in text ('e after 15 years'); numbers must be {fact_id} placeholders
- 1× unknown placeholder(s): loan_effective_rate
- 1× raw number in text ('y at an 8% bonus'); numbers must be {fact_id} placeholders
- 1× raw number in text ('take up 33.3% of'); numbers must be {fact_id} placeholders

Spoken lines replaced (blocked):

- 2× privacy: cites personal fact surplus_after
- 1× evidence: comparison 'less' needs a cited cmp_* fact saying 'lower'
- 1× evidence: unknown placeholder(s): term.emi_share

Flips vs the neutral framing's majority:

- user_negative run 2: sankz unsure (neutral majority against)

Stances per run (final round):

| framing | run | verdict | stances |
|---|---|---|---|
| neutral | 1 | red | {'dani': 'against 0.7', 'sankz': 'against 0.8'} |
| neutral | 2 | red | {'dani': 'against 0.8', 'sankz': 'against 0.7'} |
| neutral | 3 | red | {'dani': 'against 0.7', 'sankz': 'against 0.8'} |
| seller_positive | 1 | red | {'dani': 'against 0.8', 'sankz': 'against 0.7'} |
| seller_positive | 2 | red | {'dani': 'against 0.8', 'sankz': 'against 0.8'} |
| seller_positive | 3 | red | {'dani': 'against 0.8', 'sankz': 'against 0.7'} |
| user_negative | 1 | red | {'dani': 'against 0.8', 'sankz': 'against 0.7'} |
| user_negative | 2 | red | {'dani': 'against 0.8', 'sankz': 'unsure 0.0'} |
| user_negative | 3 | red | {'dani': 'against 0.7', 'sankz': 'against 0.8'} |

Auto-placeholder / short-id rewrites (every one):

- seller_positive run 2: council: auto_placeholder '14.6%' -> {emi_share}
- seller_positive run 2: explainer: auto_placeholder '14.6%' -> {emi_share}
- user_negative run 1: council: auto_placeholder '3.8%' -> {endowment_return}

Sample spoken lines (2 per case, from the first run; Alfii's opener is a fixed template):

**neutral**

> dani: Even on the guaranteed amount, this plan's return is lower than a fixed deposit.  
> sankz: The ₹50,000 flat rate really costs about 3.8% a year, which is lower than a fixed deposit.  

**seller_positive**

> dani: Only the guaranteed sum assured (₹7.5 lakh) is certain; bonuses are not.  
> sankz: I've put that on your screen.  

**user_negative**

> dani: The higher bonus rate (higher) makes this plan better than a fixed deposit, but only on the guaranteed amount (₹7.5 lakh).  
> sankz: Only ₹7.5 lakh is guaranteed; the bonus-based amounts are not certain. The monthly savings after this plan might be insufficient for other needs.  

