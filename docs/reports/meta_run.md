# Meta run

The model id below is the one each Meta reply returned, not the configured value. Reasoning effort: minimal. Limit: 20 s per call (60 s with images).

| case | started (UTC) | model id returned | verdict | model calls | total | degraded steps |
|---|---|---|---|---|---|---|
| endowment PDF | 2026-11-04T14:26:53Z | muse-spark-1.3 x3 | red | 3 | 42.2 s | no |
| endowment brochure PNG (vision) | 2026-11-04T14:27:36Z | muse-spark-1.3 x4 | red | 4 | 50.3 s | no |
| flat loan | 2026-11-04T14:28:26Z | muse-spark-1.3 x3 | red | 3 | 33.0 s | no |
| ZEPHYRX tip | 2026-11-04T14:28:59Z | muse-spark-1.3 x3 | red | 3 | 27.9 s | no |
| OTP scam | 2026-11-04T14:29:27Z | none (no model call) | red | 0 | 0.0 s | no |

### endowment PDF

- Answer: Please don't go ahead with this as it is.
- Terms: premium=50000.0 (kept); pay_years=15.0 (kept); policy_years=15.0 (kept); sum_assured=750000.0 (kept); maturity_low=1020000.0 (kept); maturity_high=1500000.0 (kept); bonus_rate_low=0.04 (kept); bonus_rate_high=0.08 (kept)
- Term sources shown: Brochure page 1 · checked; Brochure page 2 · checked

### endowment brochure PNG (vision)

- Answer: Please don't go ahead with this as it is.
- Terms: premium=50000.0 (kept); pay_years=15.0 (kept); policy_years=15.0 (kept); sum_assured=750000.0 (kept); maturity_low=1020000.0 (kept); maturity_high=1500000.0 (kept); bonus_rate_low=0.04 (kept); bonus_rate_high=0.08 (kept)
- Term sources shown: Brochure page 1 · read twice; Brochure page 2 · read twice

### flat loan

- Answer: Please don't go ahead with this as it is.
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
