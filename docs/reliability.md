# Reliability run

Model `qwen2.5:7b-instruct` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 13:58.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 5 | 19/19 · 0 · 0 | 15 / 4 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 4, 3, 4, 4 | 0 | 31.8 |
| flat_loan | 5 | 20/20 · 0 · 0 | 9 / 1 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 4, 4, 4, 4 | 0 | 20.3 |
| stock_tip | 5 | 18/18 · 0 · 0 | 12 / 8 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 4, 3, 4, 3, 4 | 0 | 19.2 |
| otp_scam | 5 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 0, 0, 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 5 | 5/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (5/5 as expected) | 1, 1, 1, 1, 1 | 0 | 1.4 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.0 | 0.0 | 12.0 | 0.0 | 0.0 | 0.0 | 9.8 | – | 0.0 | 9.8 |
| flat_loan | 0.0 | 0.0 | 5.5 | 0.0 | 0.0 | 0.0 | 5.4 | – | 0.0 | 9.1 |
| stock_tip | 0.0 | 0.0 | 4.5 | 0.0 | 0.0 | 0.0 | 7.8 | – | 0.0 | 7.1 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 1.4 | – | – | – | – | – | – | – |

Dropped-argument reasons:

- 5× raw number in text ('he last 30 days,'); numbers must be {fact_id} placeholders
- 4× comparison 'lower' needs a cited cmp_* fact saying 'lower'
- 1× unknown placeholder(s): cmp_effective_vs_quoted
- 1× raw number in text ('with an 8% bonus,'); numbers must be {fact_id} placeholders
- 1× comparison 'less' needs a cited cmp_* fact saying 'lower'
- 1× unknown citation id(s): q7

Spoken lines replaced (blocked):

- 4× privacy: cites personal fact emi_share
- 2× privacy: cites personal fact surplus_after
- 1× privacy: cites personal fact profile.monthly_expenses

Auto-placeholder / short-id rewrites (every one):

- endowment run 1: council: auto_placeholder '14.6%' -> {emi_share}
- endowment run 1: explainer: auto_placeholder '14.6%' -> {emi_share}
- endowment run 1: explainer: auto_placeholder '14.6%' -> {emi_share}
- endowment run 4: explainer: auto_placeholder '₹50,000' -> {term.premium}
- endowment run 5: council: auto_placeholder '4.5 months' -> {buffer_months_after}
- flat_loan run 1: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 1: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 1: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 1: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 2: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 3: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 3: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 3: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: council: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 4: council: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 4: explainer: auto_placeholder '21.6%' -> {loan_effective_rate}
- flat_loan run 4: explainer: auto_placeholder '12%' -> {term.flat_rate}
- flat_loan run 5: council: auto_placeholder '12%' -> {term.flat_rate}
- stock_tip run 2: council: auto_placeholder '222%' -> {run_up_30d}
- stock_tip run 3: council: auto_placeholder '222%' -> {run_up_30d}
- stock_tip run 4: council: auto_placeholder '222%' -> {run_up_30d}
- stock_tip run 5: council: auto_placeholder '222%' -> {run_up_30d}

Sample spoken lines (2 per case, from the first run; Alfii's opener is a fixed template):

**endowment**

> dani: Only ₹7.5 lakh is guaranteed; bonuses are not assured and may change annually.  
> sankz: I've put that on your screen.  

**flat_loan**

> sankz: The loan's real yearly rate is higher than the quoted flat rate, at 21.6% compared to 12%. This is quite high.  
> sankz: I've put that on your screen.  

**stock_tip**

> vick: The stock has a high high, indicating potential pump-and-dump activity.  
> sankz: Given your monthly income and high expenses, this investment is risky.  

**otp_scam**

> alfii: Stop. Please do not do what this person is asking.  
> alfii: Someone is asking for your OTP, PIN, CVV or password. No real bank or company ever asks for these.  

**out_of_scope**

> alfii: I help with money questions like loans, insurance, savings and stock tips. What would you like to check?  

