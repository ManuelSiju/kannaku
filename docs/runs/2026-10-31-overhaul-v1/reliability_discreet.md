# Reliability run

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 14:40.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 5 | 18/18 · 0 · 0 | 5 / 15 | 🔴 🔴 🟡 🟡 🔴 (3/5 as expected) | 3, 4, 4, 4, 3 | 0 | 33.2 |
| flat_loan | 5 | 18/18 · 0 · 0 | 4 / 6 | 🔴 🔴 🟡 🔴 🔴 (5/5 as expected) | 3, 4, 3, 4, 4 | 0 | 17.6 |
| stock_tip | 5 | 20/20 · 0 · 0 | 14 / 6 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 4, 4, 4, 4 | 0 | 21.1 |
| otp_scam | 5 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 0, 0, 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 5 | 5/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (5/5 as expected) | 1, 1, 1, 1, 1 | 0 | 1.4 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.0 | 0.0 | 15.5 | 0.0 | 0.0 | 0.0 | 9.5 | – | 0.0 | 8.9 |
| flat_loan | 0.0 | 0.0 | 5.5 | 0.0 | 0.0 | 0.0 | 5.1 | – | 0.0 | 7.3 |
| stock_tip | 0.0 | 0.0 | 4.5 | 0.0 | 0.0 | 0.0 | 8.1 | – | 0.0 | 8.8 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 1.4 | – | – | – | – | – | – | – |

Dropped-argument reasons:

- 7× comparison 'higher' needs a cited cmp_* fact saying 'higher'
- 3× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 3× raw number in text ('t after 15 years.'); numbers must be {fact_id} placeholders
- 1× raw number in text ('s only ₹7,50,000,'); numbers must be {fact_id} placeholders
- 1× raw number in text ('Only ₹7,50,000'); numbers must be {fact_id} placeholders
- 1× raw number in text ('at  for 15 years.'); numbers must be {fact_id} placeholders
- 1× raw number in text ('y , not 15 lakh a'); numbers must be {fact_id} placeholders
- 1× raw number in text ('ed, not 15 lakh a'); numbers must be {fact_id} placeholders
- 1× raw number in text ('t  over 15 years.'); numbers must be {fact_id} placeholders
- 1× raw number in text ('not the 15 lakh p'); numbers must be {fact_id} placeholders
- 1× raw number in text ('it over 15 years'); numbers must be {fact_id} placeholders
- 1× no evidence cited

Auto-placeholder / short-id rewrites (every one):

- endowment run 3: council: auto_placeholder '₹7.5 lakh' -> {term.sum_assured}
- endowment run 3: council: auto_placeholder '₹7.5 lakh' -> {term.sum_assured}
- flat_loan run 2: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 4: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 4: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 5: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 5: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 5: explainer: auto_placeholder '12%' -> {term.flat_rate}
- stock_tip run 1: explainer: auto_placeholder '7%' -> {ref.fd_rate}
- stock_tip run 1: explainer: auto_placeholder '222%' -> {run_up_30d}
- stock_tip run 1: explainer: auto_placeholder '22' -> {upper_circuit_hits_30d}

Linter rejections per rule:

- 8× vague
- 6× too_many_numbers

Agent turns dropped after regeneration + fallback:

- 6× sankz
- 1× vick

Council length: endowment 47 words / 19 s, flat_loan 24 words / 10 s, stock_tip 43 words / 17 s, otp_scam 33 words / 13 s, out_of_scope 14 words / 6 s (median)

## What the user gets (first run of each case)

### endowment (discreet mode) — red

**Short answer:** Let us not rush into this.

**Council** (42 words, ~17 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): There is a simpler way to protect your family, like a fixed deposit.  
> sankz (agent): A bank FD would do the job better, with less risk.  
> alfii (conclusion): Let us not rush into this. Ask for a written guarantee first.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** Can you show me in writing the higher bonus rate?; Can you show me in writing the lower bonus rate?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed to give 15 lakh — Bonus rates are not guaranteed and may change every year


### flat_loan (discreet mode) — red

**Short answer:** This loan really costs you more than a normal bank loan, so be careful.

**Council** (24 words, ~10 s):

> alfii (opener): Let me ask Sankz.  
> alfii (conclusion): This loan really costs you more than a normal bank loan, so be careful. Talk to Arun before you decide.  

**On-screen notes:** Your EMIs would take 16.8% of your income.; After this, you would have ₹8,433 left each month.; Your savings would cover 4.4 months of costs.

**Questions to ask:** What is the real yearly interest rate?

**Suggested follow-ups:** What is the real interest rate?; What would my EMI be?; Can I afford this EMI?


### stock_tip (discreet mode) — red

**Short answer:** Do not invest without a safer option first.

**Council** (33 words, ~13 s):

> alfii (opener): Let me ask Vick and Sankz.  
> sankz (agent): A fixed deposit at 7 percent is safer than stocks, which can fall.  
> alfii (conclusion): Do not invest without a safer option first. Talk to Arun before you decide.  

**On-screen notes:** This amount is 62.5% of your savings.

**Questions to ask:** What's the real yearly interest rate for a bank deposit?

**Suggested follow-ups:** What are the warning signs?; How much of my savings is this?


### otp_scam (discreet mode) — red

**Short answer:** No real bank ever asks for your OTP or PIN.

**Council** (33 words, ~13 s):

> alfii (opener): You did the right thing by asking me.  
> alfii (agent): No real bank ever asks for your OTP or PIN.  
> alfii (conclusion): Please don't share any code or pay anyone. Hang up and call your bank yourself.  

**On-screen notes:** none

**Questions to ask:** none

**Suggested follow-ups:** Is this message real?


### out_of_scope (discreet mode) — None

**Short answer:** I can only help with money questions. You could ask me one of these.

**Council** (14 words, ~6 s):

> alfii (conclusion): I can only help with money questions. You could ask me one of these.  

**On-screen notes:** none

**Questions to ask:** none

**Suggested follow-ups:** Is this insurance plan good for me?; Should I take this loan?; Is this stock tip safe?

