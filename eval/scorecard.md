# Eval scorecard

Per-dimension scores (rate 1.0 = perfect); misses list the specific failures.
This is the v1 baseline the v2 rebuild must beat, not regress.

| thesis | dimension | passed/total | rate | misses |
|---|---|---|---|---|
| gao | structure (chapters) | 4/4 | 1.0 |  |
| gao | citation/markup strip | 4/4 | 1.0 |  |
| gao | value preservation | 4/4 | 1.0 |  |
| gao | raw-token leak (clean=1) | 1/1 | 1.0 |  |
| zhu | structure (chapters) | 0/6 | 0.0 | detected 0/6 chapters |
| zhu | citation/markup strip | 0/4 | 0.0 | span id, doi:, the link in the text, re:page-?\w+ to (zero\|one) |
| zhu | value preservation | 2/3 | 0.667 | one point zero one |
| zhu | raw-token leak (clean=1) | 1/1 | 1.0 |  |
