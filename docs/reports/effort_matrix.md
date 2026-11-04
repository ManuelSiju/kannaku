# Reasoning effort per step

`muse-spark-1.3`, 20 s per call, 2 runs of the 3 cases that use the council.

| setting | verdict as expected | kept / dropped | degraded runs | median time | calls |
|---|---|---|---|---|---|
| council minimal, explainer minimal | 6/6 | 20 / 0 | 0/6 | 22.8 s | 3 |
| council low | 3/6 | 4 / 0 | 5/6 | 39.7 s | 4 |
| council high | 2/6 | 0 / 0 | 6/6 | 41.8 s | 3 |
| explainer low | 6/6 | 19 / 0 | 3/6 | 36.8 s | 3 |
| explainer high | 6/6 | 18 / 2 | 6/6 | 38.9 s | 3 |
