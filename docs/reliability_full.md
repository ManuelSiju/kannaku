# Reliability run

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 15:10.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 5 | 19/19 · 0 · 0 | 12 / 7 | 🔴 🔴 🔴 🔴 🟡 (4/5 as expected) | 4, 4, 4, 4, 3 | 0 | 33.6 |
| flat_loan | 5 | 19/19 · 0 · 0 | 9 / 1 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 4, 4, 3, 4 | 0 | 19.6 |
| stock_tip | 5 | 18/18 · 0 · 0 | 9 / 11 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 3, 4, 3, 4, 4 | 0 | 20.6 |
| otp_scam | 5 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 0, 0, 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 5 | 5/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (5/5 as expected) | 1, 1, 1, 1, 1 | 0 | 1.4 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.0 | 0.0 | 15.4 | 0.0 | 0.0 | 0.0 | 9.6 | – | 0.0 | 9.4 |
| flat_loan | 0.0 | 0.0 | 5.4 | 0.0 | 0.0 | 0.0 | 5.5 | – | 0.0 | 8.5 |
| stock_tip | 0.0 | 0.0 | 4.4 | 0.0 | 0.0 | 0.0 | 9.7 | – | 0.0 | 7.4 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 1.4 | – | – | – | – | – | – | – |

Dropped-argument reasons:

- 4× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 3× comparison 'less' needs a cited cmp_* fact saying 'lower'
- 2× comparison 'beats' needs a cited cmp_* fact saying 'higher'
- 2× raw number in text ('rise in 30 days a'); numbers must be {fact_id} placeholders
- 1× no evidence cited
- 1× comparison 'higher' needs a cited cmp_* fact saying 'higher'
- 1× unknown citation id(s): cmp_return_guaranteed_vs_fd
- 1× comparison 'less' needs a cited cmp_* fact saying 'higher'
- 1× comparison 'better' needs a cited cmp_* fact saying 'higher'
- 1× raw number in text ('ose  in 30 days,'); numbers must be {fact_id} placeholders
- 1× unknown placeholder(s): value_for_reasoning
- 1× unknown citation id(s): invest_amount

Auto-placeholder / short-id rewrites (every one):

- endowment run 2: council: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 2: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 3: council: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 3: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 3: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 4: council: auto_placeholder '8%' -> {term.bonus_rate_high}
- endowment run 5: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}
- flat_loan run 1: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 1: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 1: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 1: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 2: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 2: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 3: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- flat_loan run 3: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 3: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 4: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 5: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 5: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 5: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 5: explainer: auto_placeholder '12%' -> {term.flat_rate}
- stock_tip run 1: council: auto_placeholder '222%' -> {run_up_30d}
- stock_tip run 4: council: auto_placeholder '222%' -> {run_up_30d}
- stock_tip run 5: council: short id {invest_amount} -> {term.invest_amount}

Linter rejections per rule:

- 5× too_many_numbers
- 4× vague

Agent turns dropped after regeneration + fallback:

- 4× sankz
- 3× vick

Council length: endowment 40 words / 16 s, flat_loan 35 words / 14 s, stock_tip 37 words / 15 s, otp_scam 33 words / 13 s, out_of_scope 14 words / 6 s (median)

## What the user gets (first run of each case)

### endowment (full mode) — red

**Short answer:** Do not sign without clear written guarantees.

**Council** (30 words, ~12 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): The guaranteed sum is 7.5 lakh rupees, but bonus rates may change.  
> alfii (conclusion): Do not sign without clear written guarantees. Ask about cancellation terms first.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** What are the terms if I want to cancel this policy?; What are your expectations for future bonus rates?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed to give 15 lakh — Bonus rates are not guaranteed and may change every year


### flat_loan (full mode) — red

**Short answer:** This loan's real yearly rate is very high, so be cautious.

**Council** (34 words, ~14 s):

> alfii (opener): Let me ask Sankz.  
> sankz (agent): The real yearly cost is higher than the quoted rate, so be cautious.  
> alfii (conclusion): This loan's real yearly rate is very high, so be cautious. Ask for the reducing-balance rate first.  

**On-screen notes:** Your EMIs would take 16.8% of your income.; After this, you would have ₹8,433 left each month.; Your savings would cover 4.4 months of costs.

**Questions to ask:** What are your monthly expenses including this EMI?

**Suggested follow-ups:** What is the real interest rate?; What would my EMI be?; Can I afford this EMI?


### stock_tip (full mode) — red

**Short answer:** Do not invest without clear facts.

**Council** (19 words, ~8 s):

> alfii (opener): Let me ask Vick and Sankz.  
> alfii (conclusion): Do not invest without clear facts. Ask for proof of the target price.  

**On-screen notes:** This amount is 62.5% of your savings.

**Questions to ask:** Is there a written guarantee?; How much do I get back if it falls?; What news is this about?

**Suggested follow-ups:** What are the warning signs?; How much of my savings is this?


### otp_scam (full mode) — red

**Short answer:** No real bank ever asks for your OTP or PIN.

**Council** (33 words, ~13 s):

> alfii (opener): You did the right thing by asking me.  
> alfii (agent): No real bank ever asks for your OTP or PIN.  
> alfii (conclusion): Please don't share any code or pay anyone. Hang up and call your bank yourself.  

**On-screen notes:** none

**Questions to ask:** none

**Suggested follow-ups:** Is this message real?


### out_of_scope (full mode) — None

**Short answer:** I can only help with money questions. You could ask me one of these.

**Council** (14 words, ~6 s):

> alfii (conclusion): I can only help with money questions. You could ask me one of these.  

**On-screen notes:** none

**Questions to ask:** none

**Suggested follow-ups:** Is this insurance plan good for me?; Should I take this loan?; Is this stock tip safe?

