# Reliability run

Model `qwen2.5:7b-instruct` at `http://127.0.0.1:11435/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-11-04 11:35.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 5 | 15/15 · 0 · 0 | 18 / 2 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 3, 3, 3, 3, 3 | 0 | 28.5 |
| flat_loan | 5 | 20/20 · 0 · 0 | 7 / 3 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 4, 4, 4, 4 | 0 | 18.5 |
| stock_tip | 5 | 20/20 · 0 · 0 | 7 / 6 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 4, 4, 4, 4 | 0 | 18.6 |
| otp_scam | 5 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 0, 0, 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 5 | 5/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (5/5 as expected) | 1, 1, 1, 1, 1 | 0 | 1.4 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.0 | 0.0 | 12.7 | 0.0 | 0.0 | 0.0 | 8.9 | – | 0.0 | 7.0 |
| flat_loan | 0.0 | 0.0 | 5.6 | 0.0 | 0.0 | 0.0 | 5.3 | – | 0.0 | 7.5 |
| stock_tip | 0.0 | 0.0 | 4.6 | 0.0 | 0.0 | 0.0 | 6.0 | – | 0.0 | 7.5 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 1.4 | – | – | – | – | – | – | – |

Dropped-argument reasons:

- 3× comparison 'less' needs a cited cmp_* fact saying 'lower'
- 3× comparison 'more' needs a cited cmp_* fact saying 'higher'
- 2× comparison 'higher' needs a cited cmp_* fact saying 'higher'
- 1× unknown placeholder(s): term.flat_rate, loan_effective_rate, cmp_effective_vs_quoted
- 1× comparison 'better' needs a cited cmp_* fact saying 'higher'
- 1× unknown placeholder(s): cmp_effective_vs_quoted

Auto-placeholder / short-id rewrites (every one):

- endowment run 1: council: ignored unknown citation f_return_high_vs_fd
- endowment run 1: explainer: auto_placeholder '₹7.5 lakh' -> {term.sum_assured}
- endowment run 1: explainer: auto_placeholder '₹7.5 lakh' -> {term.sum_assured}
- endowment run 1: explainer: auto_placeholder '15 lakh' -> {term.maturity_high}
- endowment run 4: council: ignored unknown citation q10
- endowment run 5: council: ignored unknown citation f_return_high_vs_fd
- endowment run 5: council: ignored unknown citation f_return_guaranteed_vs_fd
- flat_loan run 1: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 1: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 1: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- flat_loan run 1: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 1: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 2: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 2: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 4: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- flat_loan run 4: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 4: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 5: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 5: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 5: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- flat_loan run 5: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 5: explainer: auto_placeholder '12%' -> {term.flat_rate}
- stock_tip run 1: explainer: ignored unknown citation cmp_return_low_vs_fd
- stock_tip run 2: council: ignored unknown citation cmp_run_up_30d_vs_long_run
- stock_tip run 2: council: auto_placeholder '14%' -> {ref.typical_personal_loan_rate}
- stock_tip run 2: explainer: ignored unknown citation cmp_return_low_vs_fd
- stock_tip run 4: council: ignored unknown citation cmp_pump_risk
- stock_tip run 4: council: ignored unknown citation cmp_return_high_vs_fd
- stock_tip run 5: explainer: ignored unknown citation cmp_return_low_vs_fd

Linter rejections per rule:

- 6× vague
- 2× too_many_numbers

Agent turns dropped after regeneration + fallback:

- 1× sankz

Council length: endowment 41 words / 16 s, flat_loan 34 words / 14 s, stock_tip 45 words / 18 s, otp_scam 33 words / 13 s, out_of_scope 14 words / 6 s (median)

## Red runs: short answer and Alfii's final line (20)

| case | run | short answer | Alfii's final line |
|---|---|---|---|
| endowment | 1 | Please don't go ahead with this as it is. | Do not sign this plan as it is not guaranteed to give 15 lakh rupees. |
| endowment | 2 | Please don't go ahead with this as it is. | Do not sign this plan; only 7.5 lakh rupees is certain. |
| endowment | 3 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| endowment | 4 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| endowment | 5 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| flat_loan | 1 | Please don't go ahead with this as it is. | Do not take this loan; it costs more than a normal bank loan. Talk to Arun before you decide. |
| flat_loan | 2 | Please don't go ahead with this as it is. | Do not take this loan; it costs more than a normal bank loan. Talk to Arun before you decide. |
| flat_loan | 3 | Please don't go ahead with this as it is. | Do not take this loan; it costs more than a normal bank loan. Talk to Arun before you decide. |
| flat_loan | 4 | Please don't go ahead with this as it is. | Do not take this loan; it costs more than a normal bank loan. Talk to Arun before you decide. |
| flat_loan | 5 | Please don't go ahead with this as it is. | Do not take this loan; it costs more than a normal bank loan. Talk to Arun before you decide. |
| stock_tip | 1 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| stock_tip | 2 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| stock_tip | 3 | Please don't go ahead with this as it is. | My advice: do not go ahead with this as it is. Talk to Arun before you decide. |
| stock_tip | 4 | Please don't go ahead with this as it is. | Do not invest in tips like these, please. Talk to Arun before you decide. |
| stock_tip | 5 | Please don't go ahead with this as it is. | Do not invest in tips like these, please. Talk to Arun before you decide. |
| otp_scam | 1 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 2 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 3 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 4 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |
| otp_scam | 5 | No real bank ever asks for your OTP or PIN. | Please don't share any code or pay anyone. Hang up and call your bank yourself. |

## Questions (every run)

| case | run | questions said | reworded | rejected |
|---|---|---|---|---|
| endowment | 1 | How much is guaranteed in writing? / What do I get at the lower bonus rate? | — | — |
| endowment | 2 | How much is guaranteed in writing? / What do I get at the lower bonus rate? / What do I get at the higher bonus rate? | — | — |
| endowment | 3 | How much is guaranteed in writing? | — | — |
| endowment | 4 | How much is guaranteed in writing? | — | — |
| endowment | 5 | How much is guaranteed in writing? / What do I get at the lower bonus rate? | — | — |
| flat_loan | 1 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 2 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 3 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 4 | What is the reducing-balance interest rate? | — | — |
| flat_loan | 5 | What is the reducing-balance interest rate? | — | — |
| stock_tip | 1 | Who sent this tip, and do they own the stock? / Why is it rising this fast? | — | — |
| stock_tip | 2 | Who sent this tip, and do they own the stock? | — | — |
| stock_tip | 3 | Who sent this tip, and do they own the stock? | — | — |
| stock_tip | 4 | Who sent this tip, and do they own the stock? | — | stock_who (lost key word(s): own) |
| stock_tip | 5 | Why is it rising this fast? | — | — |
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

### endowment (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (39 words, ~16 s):

> alfii (opener): Let me ask Dani and Sankz.  
> dani (agent): Only 7.5 lakh rupees is certain; bonus-based amounts are not.  
> sankz (agent): Only 7.5 lakh rupees is written as guaranteed.  
> alfii (conclusion): Do not sign this plan as it is not guaranteed to give 15 lakh rupees.  

**On-screen notes:** This premium is 31.2% of your savings each year.; Each month this premium is 9.3% of your income.; After this, you would have ₹9,433 left each month.; Your savings would cover 4.5 months of costs.

**Questions to ask:** How much is guaranteed in writing?; What do I get at the lower bonus rate?

**Suggested follow-ups:** What would an FD give me instead?; How much of this is guaranteed?; Can I afford this premium?

**Claim checks:** contradicted: guaranteed to give 15 lakh — Bonus rates are not guaranteed and may change every year


### flat_loan (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (34 words, ~14 s):

> alfii (opener): Let me ask Sankz.  
> sankz (agent): The real cost is 21.6 percent, higher than the quoted rate.  
> alfii (conclusion): Do not take this loan; it costs more than a normal bank loan. Talk to Arun before you decide.  

**On-screen notes:** Your EMIs would take 16.8% of your income.; After this, you would have ₹8,433 left each month.; Your savings would cover 4.4 months of costs.

**Questions to ask:** What is the reducing-balance interest rate?

**Suggested follow-ups:** What is the real interest rate?; What would my EMI be?; Can I afford this EMI?


### stock_tip (discreet mode) — red

**Short answer:** Please don't go ahead with this as it is.

**Council** (48 words, ~19 s):

> alfii (opener): Let me ask Vick and Sankz.  
> vick (agent): This stock rose 222 percent recently, a sign of pump-and-dump activity.  
> sankz (agent): A personal loan costs more than the risk here; choose a fixed deposit instead.  
> alfii (conclusion): My advice: do not go ahead with this as it is. Talk to Arun before you decide.  

**On-screen notes:** This amount is 62.5% of your savings.

**Questions to ask:** Who sent this tip, and do they own the stock?; Why is it rising this fast?

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

