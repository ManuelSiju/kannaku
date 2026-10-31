# Reliability run

Model `qwen2.5vl:7b` at `http://localhost:11434/v1`, temperature 0.2, timeout 20 s per call, max 4 calls per ask. Run 2026-10-31 14:25.

| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | LLM calls | degraded runs | total s (median) |
|---|---|---|---|---|---|---|---|
| endowment | 5 | 0/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (0/5 as expected) | 1, 1, 1, 1, 1 | 5 | 20.1 |
| flat_loan | 5 | 2/9 · 0 · 0 | 0 / 0 | 🟡 ⚪ ⚪ ⚪ 🟡 (2/5 as expected) | 3, 1, 1, 1, 3 | 5 | 20.1 |
| stock_tip | 5 | 1/7 · 0 · 0 | 0 / 0 | ⚪ ⚪ 🟡 ⚪ ⚪ (0/5 as expected) | 1, 1, 3, 1, 1 | 5 | 20.0 |
| otp_scam | 5 | no LLM steps | 0 / 0 | 🔴 🔴 🔴 🔴 🔴 (5/5 as expected) | 0, 0, 0, 0, 0 | 0 | 0.0 |
| out_of_scope | 5 | 5/5 · 0 · 0 | 0 / 0 | ⚪ ⚪ ⚪ ⚪ ⚪ (5/5 as expected) | 1, 1, 1, 1, 1 | 0 | 3.5 |

Latency per step, median seconds:

| case | ingest | scam_rules | case_builder | verify_terms | compute | router | council | debate | consensus | explainer |
|---|---|---|---|---|---|---|---|---|---|---|
| endowment | 0.1 | 0.0 | 20.0 | – | – | – | – | – | – | – |
| flat_loan | 0.0 | 0.0 | 20.0 | 0.0 | 0.0 | 0.0 | 20.0 | – | 0.0 | 20.0 |
| stock_tip | 0.0 | 0.0 | 20.0 | 0.0 | 0.0 | 0.0 | 20.0 | – | 0.0 | 20.0 |
| otp_scam | 0.0 | 0.0 | – | – | – | – | – | – | – | – |
| out_of_scope | 0.0 | 0.0 | 3.4 | – | – | – | – | – | – | – |

Step errors:

- 12× case_builder: LLMStepFailed: LLM call failed: APITimeoutError: Request timed out.
- 3× explainer: LLMStepFailed: LLM call failed: APITimeoutError: Request timed out.
- 2× council: LLMStepFailed: LLM call failed: APITimeoutError: Request timed out.
- 1× council: LLMStepFailed: LLM call timed out after 20.0s

Auto-placeholder / short-id rewrites (every one):

- none

Sample spoken lines (2 per case, from the first run; Alfii's opener is a fixed template):

**endowment**

> alfii: Is this about a loan, a policy, an investment or a payment?  

**flat_loan**

> alfii: Be careful: get clear answers to these questions before you decide.  

**stock_tip**

> alfii: Is this about a loan, a policy, an investment or a payment?  

**otp_scam**

> alfii: Stop. Please do not do what this person is asking.  
> alfii: Someone is asking for your OTP, PIN, CVV or password. No real bank or company ever asks for these.  

**out_of_scope**

> alfii: I help with money questions like loans, insurance, savings and stock tips. What would you like to check?  

