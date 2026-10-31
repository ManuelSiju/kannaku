# Reliability run

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 14:46.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 5 | 19/19 · 0 · 0 | 12 / 8 | 🔴 🟡 🔴 🔴 🟡 (3/5 as expected) | 3, 4, 4, 4, 4 | 0 | 32.2 |
| flat_loan | 5 | 19/19 · 0 · 0 | 0 / 10 | 🟡 🟡 🟡 🟡 🟡 (5/5 as expected) | 4, 3, 4, 4, 4 | 0 | 19.0 |
| stock_tip | 5 | 17/17 · 0 · 0 | 14 / 6 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 3, 3, 3, 4, 4 | 0 | 20.9 |
| otp_scam | 5 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 0, 0, 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 5 | 5/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (5/5 as expected) | 1, 1, 1, 1, 1 | 0 | 1.4 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.0 | 0.0 | 15.6 | 0.0 | 0.0 | 0.0 | 9.8 | – | 0.0 | 10.5 |
| flat_loan | 0.0 | 0.0 | 5.5 | 0.0 | 0.0 | 0.0 | 5.2 | – | 0.0 | 8.3 |
| stock_tip | 0.0 | 0.0 | 4.6 | 0.0 | 0.0 | 0.0 | 8.2 | – | 0.0 | 8.6 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 1.4 | – | – | – | – | – | – | – |

Dropped-argument reasons:

- 10× comparison 'higher' needs a cited cmp_* fact saying 'higher'
- 3× no evidence cited
- 3× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 2× comparison 'less' needs a cited cmp_* fact saying 'lower'
- 2× comparison 'better' needs a cited cmp_* fact saying 'higher'
- 1× raw number in text ('after 15 years'); numbers must be {fact_id} placeholders
- 1× comparison 'less' needs a cited cmp_* fact saying 'higher'
- 1× unknown citation id(s): q10
- 1× comparison 'lower' needs a cited cmp_* fact saying 'lower'

Auto-placeholder / short-id rewrites (every one):

- flat_loan run 1: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: council: auto_placeholder '12%' -> {term.flat_rate}

Linter rejections per rule:

- 7× too_many_numbers

Agent turns dropped after regeneration + fallback:

- 9× sankz

Council length: endowment 38 words / 15 s, flat_loan 32 words / 13 s, stock_tip 40 words / 16 s, otp_scam 33 words / 13 s, out_of_scope 14 words / 6 s (median)

## What the user gets (first run of each case)

### endowment (full mode) — red

**Short answer:** Do not sign without seeing both rates in writing first.

**Council** (38 words, ~15 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): The 7.5 lakh rupees is certain, but bonus-based returns are not guaranteed.  
> sankz (agent): Only the 7.5 lakh rupees is guaranteed; bonuses are not.  
> alfii (conclusion): Do not sign without seeing both rates in writing first.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** Can you show me in writing the higher bonus rate?; What is the typical bonus rate over time?; Can you show me in writing the lower bonus rate?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed to give 15 lakh — Bonus rates are not guaranteed and may change every year


### flat_loan (full mode) — yellow

**Short answer:** This loan's real yearly rate is higher than both the quoted and typical rates, so be cautious.

**Council** (32 words, ~13 s):

> alfii (opener): Let me ask Sankz.  
> alfii (conclusion): This loan's real yearly rate is higher than both the quoted and typical rates, so be cautious. Before you decide, ask: "What is the real yearly interest rate?"  

**On-screen notes:** Your EMIs would take 16.8% of your income.; After this, you would have ₹8,433 left each month.; Your savings would cover 4.4 months of costs.

**Questions to ask:** What is the real yearly interest rate?

**Suggested follow-ups:** What is the real interest rate?; What would my EMI be?; Can I afford this EMI?


### stock_tip (full mode) — red

**Short answer:** Do not invest without a safer plan first.

**Council** (44 words, ~18 s):

> alfii (opener): Let me ask Vick and Sankz.  
> vick (agent): This stock shows a high pump-and-dump risk and big price jumps, risky indeed.  
> sankz (agent): Putting so much in shares is too risky for your savings.  
> alfii (conclusion): Do not invest without a safer plan first. Talk to Arun before you decide.  

**On-screen notes:** This amount is 62.5% of your savings.

**Questions to ask:** none

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

