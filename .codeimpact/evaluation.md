# CodeImpact benchmark

Ten hand-labelled scenarios over a small executable fixture repository. Ground truth lists all reachable consumers, including tests.

Precision = TP / predicted files. Recall = TP / expected files. F1 = 2PR / (P+R). Averages are macro-averaged over identical cases.

Keyword baseline: top 5 matching chunks. Graph: all reverse dependency consumers. Hybrid: graph union top retrieval candidates (unconfirmed candidates count as predictions).

| Method | Precision | Recall | F1 |
|---|---:|---:|---:|
| keyword | 0.867 | 0.775 | 0.781 |
| graph | 1.000 | 1.000 | 1.000 |
| hybrid | Not measured | Not measured | Not measured |

This fixture checks dependency tracing, not generalization to large production repositories. It does not establish that LLM reasoning outperforms static analysis. AI suggestions require a separate human-labelled benchmark.
