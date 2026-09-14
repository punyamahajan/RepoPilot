# Week 4 Model Evaluation Analysis

Generated from `results.json`; all values are averages across the same questions and retrieved context.

| Model | Accuracy | Relevance | Retrieval | Latency(s) | Tokens | CPU% | Memory MiB | Hallucination | Test pass |
|---|---|---|---|---|---|---|---|---|---|
| codellama | 79.9% | 0.791 | 87.5% | 18.88 | 901.8 | 0.4 | 33.1 | 29.2% | 33.3% |
| starcoder2 | 36.1% | 0.329 | 87.5% | 60.66 | 548.2 | 0.3 | 33.1 | 16.7% | 0.0% |
| qwen2.5-coder | 72.9% | 0.817 | 87.5% | 11.34 | 600.9 | 0.3 | 33.1 | 25.0% | 66.7% |

## Findings

- **Most accurate:** `codellama` (79.9%).
- **Least hallucination:** `starcoder2` (16.7% flagged).
- **Fastest:** `qwen2.5-coder` (11.34 seconds/query).
- **Fewest tokens:** `starcoder2` (548.2 tokens/query).
- **Lowest sampled CPU:** `qwen2.5-coder` (0.3%).
- **Lowest sampled client memory:** `codellama` (33.1 MiB).

## Trade-off

There is a measurable trade-off: `codellama` is most accurate, while `qwen2.5-coder` is fastest, `qwen2.5-coder` uses the least sampled CPU, and `codellama` uses the least client memory. The best model is therefore not uniformly the most efficient.

CPU and memory measure the Python evaluation client during each HTTP request, not the host Ollama daemon. Token counts come directly from Ollama. The hallucination detector is a conservative identifier/file-name heuristic and should be paired with manual review.
