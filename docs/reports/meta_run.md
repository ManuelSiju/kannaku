# Meta run

The model id below is the one each Meta reply returned, not the configured value. Reasoning effort: minimal. Limit: 20 s per call (60 s with images).

| case | trace (case id) | started (UTC) | model id returned | verdict | model calls | total | degraded |
|---|---|---|---|---|---|---|---|
| endowment PDF | 1 | 2026-11-04T19:15:52Z | muse-spark-1.3 x3 | red | 3 | 35.3 s | no |
| endowment brochure PNG (vision) | 2 | 2026-11-04T19:16:27Z | muse-spark-1.3 x3 | red | 3 | 41.4 s | no |
| flat loan | 3 | 2026-11-04T19:17:09Z | muse-spark-1.3 x2 | yellow | 3 | 39.6 s | council |
| ZEPHYRX tip | 4 | 2026-11-04T19:17:48Z | muse-spark-1.3 x3 | red | 3 | 29.3 s | no |
| OTP scam | 5 | 2026-11-04T19:18:18Z | none (no model call) | red | 0 | 0.0 s | no |
| out of scope | 6 | 2026-11-04T19:18:18Z | muse-spark-1.3 x1 | None | 1 | 2.9 s | no |

### endowment PDF

- Answer: Please don't go ahead with this as it is.
- Terms: premium=50000.0 (kept); pay_years=15.0 (kept); policy_years=15.0 (kept); sum_assured=750000.0 (kept); maturity_low=1020000.0 (kept); maturity_high=1500000.0 (kept); bonus_rate_low=0.04 (kept); bonus_rate_high=0.08 (kept)
- Term sources shown: Brochure page 1 · checked; Brochure page 2 · checked

### endowment brochure PNG (vision)

- Answer: Please don't go ahead with this as it is.
- Terms: premium=50000.0 (kept); pay_years=15.0 (kept); policy_years=15.0 (kept); sum_assured=750000.0 (kept); maturity_low=1020000.0 (kept); maturity_high=1500000.0 (kept); bonus_rate_low=0.04 (kept); bonus_rate_high=0.08 (kept)
- Term sources shown: Brochure page 1 · read twice; Brochure page 2 · read twice

### flat loan

- Answer: You should hold on and compare before you sign this loan.
- Terms: loan_amount=100000.0 (kept); flat_rate=0.12 (kept); tenure_months=24.0 (kept)
- Term sources shown: What you said · checked

### ZEPHYRX tip

- Answer: Please don't go ahead with this as it is.
- Terms: invest_amount=100000.0 (kept)
- Term sources shown: What you said · checked

### OTP scam

- Answer: No real bank ever asks for your OTP or PIN.
- Terms: none
- Term sources shown: none

### out of scope

- Answer: I can only help with money questions. You could ask me one of these.
- Terms: none
- Term sources shown: none

### Speech, 25 s of recorded audio

- Path: meta, model muse-voice-transcribe-1.0, 7.5 s
- Heard: Let me ask Dani and Sankz. You were told guaranteed but the paper paper says bonuses may change each year. only 7.5 lakh rupees is written as guaranteed for you you get back 10.2 lakh rupees at the small bonus rate this plan grows lower than a fixed deposit. Please do not take this plan. Talk to Arun before you before you decide

## Settings and what was tried

- **Reasoning effort: `minimal` on every step**, from [effort_matrix.md](effort_matrix.md). `low` and `high` on the
  council or explainer run past the 20 s limit, so steps degrade. Only `minimal` gave 6 of 6 expected verdicts with no
  degraded run.
- **Structured output: `json_object`.** On the same explainer request `json_schema` ran to the token limit.
- **Muse Voice Transcribe: used on Meta**, with keyword biasing for words like lakh, EMI and the council's names, and
  local faster-whisper as the automatic fallback. The trace records which path ran. It can repeat a word or digit.
- **SAM 3.1: not tried.** It is listed by `GET /models`; nothing in Kanakku calls it.
