# Reliability run

Model `muse-spark-1.3` at `https://api.meta.ai/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-11-04 20:15.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 3 | 9/9 · 0 · 0 | 12 / 0 | 🔴 🔴 🔴 (3/3 as expected) | 3, 3, 3 | 0 | 28.0 |
| flat_loan | 3 | 9/10 · 0 · 0 | 6 / 0 | 🔴 🔴 🔴 (3/3 as expected) | 3, 3, 4 | 1 | 32.3 |
| stock_tip | 3 | 9/9 · 0 · 0 | 10 / 0 | 🔴 🔴 🔴 (3/3 as expected) | 3, 3, 3 | 0 | 25.9 |
| otp_scam | 3 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 (3/3 as expected) | 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 3 | 3/3 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ (3/3 as expected) | 1, 1, 1 | 0 | 1.5 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.0 | 0.0 | 5.5 | 0.0 | 0.0 | 0.0 | 12.7 | – | 0.0 | 10.4 |
| flat_loan | 0.0 | 0.0 | 2.8 | 0.0 | 0.0 | 0.0 | 9.6 | – | 0.0 | 19.8 |
| stock_tip | 0.0 | 0.0 | 2.8 | 0.0 | 0.0 | 0.0 | 12.8 | – | 0.0 | 9.9 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 1.5 | – | – | – | – | – | – | – |

Step errors:

- 1× explainer: LLMStepFailed: LLM call failed: APITimeoutError: Request timed out.

Auto-placeholder / short-id rewrites (every one):

- endowment run 1: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 3: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}

Linter rejections per rule:

- 1× sentence_too_long

Council length: endowment 62 words / 25 s, flat_loan 35 words / 14 s, stock_tip 70 words / 28 s, otp_scam 33 words / 13 s, out_of_scope 14 words / 6 s (median)

## Red runs: short answer and Alfii's final line (12)

| case | run | short answer | Alfii's final line |
|---|---|---|---|
| endowment | 1 | Please don't go ahead with this as it is. | Please do not sign this plan as it is. |
| endowment | 2 | Please don't go ahead with this as it is. | Please do not take this plan as it is. Talk to Arun before you decide. |
| endowment | 3 | Please don't go ahead with this as it is. | Please do not take this plan as it is. Talk to Arun before you decide. |
| flat_loan | 1 | Please don't go ahead with this as it is. | Please do not take this loan. Talk to Arun before you decide. |
| flat_loan | 2 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| flat_loan | 3 | Please don't go ahead with this as it is. | Please do not sign this loan as it is. |
| stock_tip | 1 | Please don't go ahead with this as it is. | Please do not put money in this tip. Talk to Arun before you decide. |
| stock_tip | 2 | Please don't go ahead with this as it is. | Please do not put money in this tip. Talk to Arun before you decide. |
| stock_tip | 3 | Please don't go ahead with this as it is. | Please do not put your money in this tip. Talk to Arun before you decide. |
| otp_scam | 1 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 2 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 3 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |

## Questions (every run)

| case | run | questions said | reworded | rejected |
|---|---|---|---|---|
| endowment | 1 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| endowment | 2 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| endowment | 3 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get if I stop after 3 years? | — | — |
| flat_loan | 1 | What is the reducing-balance interest rate? / What are the processing and prepayment charges? | — | — |
| flat_loan | 2 | What is the reducing-balance interest rate? / What are the processing and prepayment charges? | — | — |
| flat_loan | 3 | What is the reducing-balance interest rate? / What are the processing and prepayment charges? | — | — |
| stock_tip | 1 | Who sent this tip, and do they own the stock? / Why is it rising this fast? | — | — |
| stock_tip | 2 | Who sent this tip, and do they own the stock? / Why is it rising this fast? | — | — |
| stock_tip | 3 | Who sent this tip, and do they own the stock? / Why is it rising this fast? | — | — |
| otp_scam | 1 | none | — | — |
| otp_scam | 2 | none | — | — |
| otp_scam | 3 | none | — | — |
| out_of_scope | 1 | none | — | — |
| out_of_scope | 2 | none | — | — |
| out_of_scope | 3 | none | — | — |

Stock-tip questions mentioning fundamentals or the seller: 0

## What the user gets (first run of each case)

### endowment (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (60 words, ~24 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): You were told “guaranteed to give 15 lakh rupees” but the paper says bonuses may change. Only 7.5 lakh rupees is written as guaranteed for you.  
> sankz (agent): On that guaranteed part it grows lower than a fixed deposit, so a bank deposit would keep you safer.  
> alfii (conclusion): Please do not sign this plan as it is.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** How much is guaranteed in writing?; What do I get at the lower bonus rate?; What do I get if I stop after 3 years?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed to give 15 lakh — Bonus rates are not guaranteed and may change every year


### flat_loan (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (35 words, ~14 s):

> alfii (opener): Let me ask Sankz.  
> sankz (agent): This loan really costs you 21.6 percent a year. That is higher than the flat rate they told you.  
> alfii (conclusion): Please do not take this loan. Talk to Arun before you decide.  

**On-screen notes:** Your EMIs would take 16.8% of your income.; After this, you would have ₹8,433 left each month.; Your savings would cover 4.4 months of costs.

**Questions to ask:** What is the reducing-balance interest rate?; What are the processing and prepayment charges?

**Suggested follow-ups:** What is the real interest rate?; What would my EMI be?; Can I afford this EMI?


### stock_tip (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (72 words, ~29 s):

> alfii (opener): Let me ask Vick and Sankz.  
> vick (agent): This share carries a high pump-and-dump risk for you in recent trading. It already jumped 222 percent in the last month, so you may get trapped.  
> sankz (agent): If you put 1 lakh rupees in this tip you may get back nothing. A fixed deposit at 7 percent keeps your money safe for you.  
> alfii (conclusion): Please do not put money in this tip. Talk to Arun before you decide.  

**On-screen notes:** This amount is 62.5% of your savings.

**Questions to ask:** Who sent this tip, and do they own the stock?; Why is it rising this fast?

**Suggested follow-ups:** What are the warning signs?; How much of my savings is this?

**Claim checks:** cant_verify: Target Rs. 180 in 2 weeks — ; cant_verify: Upper circuit guaranteed — 


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

