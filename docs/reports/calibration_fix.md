# Calibration (meta, muse-spark-1.3)

| scenario | expected | got | oracle | agents | reason given | result |
|---|---|---|---|---|---|---|
| G3 Reducing-balance two-wheeler loan | green | green green green | ok | sankz | You can take this bike loan. Before you decide, ask: "What are the pro | PASS |
| Y3 Affordable loan, EMI share 45 percent | yellow | yellow yellow yellow | ok | sankz | emi_share_over_40 | PASS |
| R2 12 percent flat loan | red/yellow | red red red | ok | sankz | Please do not take this loan as it is. Talk to Arun before you decide. | PASS |
| R7 Guaranteed return, nothing written | red/yellow | red red red | ok | sankz, dani | Please do not put money in this scheme. Talk to Arun before you decide | PASS |
| S2a G3 at 10 percent | green | green yellow green | ok | sankz | You can take this two-wheeler loan if you need it. Before you decide,  | FAIL: colour flipped; run 2 gave yellow |
| S2b G3 at 9 percent | green | green green yellow | ok | sankz | You can take this loan. Before you decide, ask: "What is the reducing- | FAIL: colour flipped; run 3 gave yellow |
| P1 G3 loan for a poorer family | yellow/red | red red red | ok | sankz | buffer_under_1_month | PASS |
