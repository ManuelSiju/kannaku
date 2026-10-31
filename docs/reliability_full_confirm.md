# Reliability run

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 19:13.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 5 | 18/18 · 0 · 0 | 17 / 2 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 3, 3, 4, 4 | 0 | 30.6 |
| flat_loan | 5 | 17/17 · 0 · 0 | 3 / 7 | 🔴 🔴 🟡 🟡 🔴 (5/5 as expected) | 3, 4, 4, 3, 3 | 0 | 17.0 |
| stock_tip | 5 | 19/19 · 0 · 0 | 9 / 6 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 4, 3, 4, 4 | 0 | 23.2 |
| otp_scam | 5 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 0, 0, 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 5 | 5/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (5/5 as expected) | 1, 1, 1, 1, 1 | 0 | 1.4 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.0 | 0.0 | 12.3 | 0.0 | 0.0 | 0.0 | 7.9 | – | 0.0 | 9.8 |
| flat_loan | 0.0 | 0.0 | 5.4 | 0.0 | 0.0 | 0.0 | 4.5 | – | 0.0 | 6.8 |
| stock_tip | 0.0 | 0.0 | 4.5 | 0.0 | 0.0 | 0.0 | 6.5 | – | 0.0 | 12.0 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 1.4 | – | – | – | – | – | – | – |

Dropped-argument reasons:

- 5× comparison 'higher' needs a cited cmp_* fact saying 'higher'
- 4× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 2× unknown citation id(s): q12
- 2× unknown citation id(s): f3
- 1× comparison 'less' needs a cited cmp_* fact saying 'lower'
- 1× unknown citation id(s): f4

Auto-placeholder / short-id rewrites (every one):

- endowment run 1: council: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 2: explainer: auto_placeholder '₹7,50,000' -> {term.sum_assured}
- endowment run 3: council: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 3: explainer: auto_placeholder '8%' -> {term.bonus_rate_high}
- endowment run 4: explainer: auto_placeholder '₹7.5 lakh' -> {term.sum_assured}
- endowment run 4: explainer: auto_placeholder '7%' -> {ref.fd_rate}
- endowment run 5: council: auto_placeholder '15 years' -> {term.pay_years}
- endowment run 5: explainer: auto_placeholder '15 years' -> {term.pay_years}
- endowment run 5: explainer: auto_placeholder '15 years' -> {term.pay_years}
- flat_loan run 2: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- flat_loan run 2: explainer: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- flat_loan run 4: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- stock_tip run 2: council: auto_placeholder '62.5%' -> {invest_share_of_savings}
- stock_tip run 2: explainer: auto_placeholder '7%' -> {ref.fd_rate}
- stock_tip run 5: explainer: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}

Linter rejections per rule:

- 5× vague

Agent turns dropped after regeneration + fallback:

- 3× sankz

Council length: endowment 43 words / 17 s, flat_loan 35 words / 14 s, stock_tip 44 words / 18 s, otp_scam 33 words / 13 s, out_of_scope 14 words / 6 s (median)

## Red runs: short answer and Alfii's final line (18)

| case | run | short answer | Alfii's final line |
|---|---|---|---|
| endowment | 1 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask for details in writing first. |
| endowment | 2 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask about the guaranteed amount first. |
| endowment | 3 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask for the reducing-balance rate first. |
| endowment | 4 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| endowment | 5 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask about the lower bonus rate too. |
| flat_loan | 1 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask for the reducing-balance rate first. |
| flat_loan | 2 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| flat_loan | 5 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask for the reducing-balance rate first. |
| stock_tip | 1 | Please don't go ahead with this as it is. | Do not invest in such tips. Ask about the risks and costs first. |
| stock_tip | 2 | Please don't go ahead with this as it is. | Do not invest in tips like these. Ask about the risks first. |
| stock_tip | 3 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask who sent the tip and if they own ZEPHYRX. |
| stock_tip | 4 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| stock_tip | 5 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Ask about its real value. |
| otp_scam | 1 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 2 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 3 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 4 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 5 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |

## Questions (every run)

| case | run | questions said | reworded | rejected |
|---|---|---|---|---|
| endowment | 1 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get at the higher bonus rate? | — | — |
| endowment | 2 | How much is guaranteed in writing? | — | — |
| endowment | 3 | How much is guaranteed in writing? | — | — |
| endowment | 4 | How much is guaranteed in writing? | — | — |
| endowment | 5 | How much is guaranteed in writing? / What do I get at the lower bonus rate? | — | — |
| flat_loan | 1 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 2 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 3 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 4 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 5 | What is the reducing-balance interest rate? | — | — |
| stock_tip | 1 | Who sent this tip, and do they own the stock? / Why is it rising so fast? / Can you afford to lose this money? | stock_why_rising: “Why is it rising so fast?” | — |
| stock_tip | 2 | Who sent the tip and do they own ZEPHYRX? / Why is ZEPHYRX rising so fast? | stock_who: “Who sent the tip and do they own ZEPHYRX?”; stock_why_rising: “Why is ZEPHYRX rising so fast?” | — |
| stock_tip | 3 | Who sent the tip and do they own ZEPHYRX? | stock_who: “Who sent the tip and do they own ZEPHYRX?” | — |
| stock_tip | 4 | Who sent the tip and do they own ZEPHYRX? | stock_who: “Who sent the tip and do they own ZEPHYRX?” | — |
| stock_tip | 5 | Why is the stock rising so fast? / Can you afford to lose this money? | stock_why_rising: “Why is the stock rising so fast?” | — |
| otp_scam | 1 | none | — | — |
| otp_scam | 2 | none | — | — |
| otp_scam | 3 | none | — | — |
| otp_scam | 4 | none | — | — |
| otp_scam | 5 | none | — | — |
| out_of_scope | 1 | none | — | — |
| out_of_scope | 2 | none | — | — |
| out_of_scope | 3 | none | — | — |
| out_of_scope | 4 | none | — | — |
| out_of_scope | 5 | none | — | — |

Stock-tip questions mentioning fundamentals or the seller: 0

## What the user gets (first run of each case)

### endowment (full mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (43 words, ~17 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): There is a simpler way to protect your family with less risk.  
> sankz (agent): Only 7.5 lakh rupees is written as guaranteed.  
> alfii (conclusion): My advice: do not go ahead with this as it is. Ask for details in writing first.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** How much is guaranteed in writing?; What do I get at the lower bonus rate?; What do I get at the higher bonus rate?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed to give 15 lakh — Bonus rates are not guaranteed and may change every year


### flat_loan (full mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (35 words, ~14 s):

> alfii (opener): Let me ask Sankz.  
> sankz (agent): This loan's effective rate higher than is higher than a typical bank personal loan.  
> alfii (conclusion): My advice: do not go ahead with this as it is. Ask for the reducing-balance rate first.  

**On-screen notes:** Your EMIs would take 16.8% of your income.; After this, you would have ₹8,433 left each month.; Your savings would cover 4.4 months of costs.

**Questions to ask:** What is the reducing-balance interest rate?

**Suggested follow-ups:** What is the real interest rate?; What would my EMI be?; Can I afford this EMI?


### stock_tip (full mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (30 words, ~12 s):

> alfii (opener): Let me ask Vick and Sankz.  
> vick (agent): ZEPHYRX rose 222 percent; check if this is a pump-and-dump scheme.  
> alfii (conclusion): Do not invest in such tips. Ask about the risks and costs first.  

**On-screen notes:** This amount is 62.5% of your savings.

**Questions to ask:** Who sent this tip, and do they own the stock?; Why is it rising so fast?; Can you afford to lose this money?

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

