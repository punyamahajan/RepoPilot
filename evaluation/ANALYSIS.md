# Week 4 Model Evaluation Analysis

Generated from `results.json`. Failed or empty model responses are reported as errors and are excluded from metric means instead of being silently scored as zero.

## Evaluation validity

- Same question set used by every model: **yes** (`codellama`: 24, `starcoder2`: 24, `qwen2.5-coder`: 24).
- Failed or empty responses: **0**.
- CPU and memory are reported separately for the Python client and Ollama processes.
- GPU utilization and VRAM are sampled with `nvidia-smi` when an NVIDIA GPU is available; otherwise they remain zero and should be reported as unavailable.

## Overall comparison

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 24/24 | 0 | 63.9% | 0.798 | 87.5% | 16.7% | 33.3% | 5.47 s | 879.5 | 3.0% | 38.1 MiB | 52.3% | 2038.2 MiB | 46.5% | 7138.7 MiB |
| starcoder2 | 24/24 | 0 | 50.0% | 0.606 | 87.5% | 16.7% | 0.0% | 5.09 s | 891.0 | 3.3% | 38.6 MiB | 49.8% | 1352.5 MiB | 46.7% | 3546.5 MiB |
| qwen2.5-coder | 24/24 | 0 | 70.8% | 0.795 | 87.5% | 33.3% | 66.7% | 5.58 s | 665.0 | 3.3% | 38.7 MiB | 46.9% | 2608.1 MiB | 42.2% | 7397.8 MiB |

## Overall findings

- **Highest accuracy:** `qwen2.5-coder` (70.8%).
- **Best retrieval quality:** `codellama`, `starcoder2`, `qwen2.5-coder` (87.5%).
- **Fewest hallucinations:** `codellama`, `starcoder2` (16.7%).
- **Highest generated-code test-pass rate:** `qwen2.5-coder` (66.7%).
- **Lowest response latency:** `starcoder2` (5.09 s).
- **Fewest tokens:** `qwen2.5-coder` (665.0 tokens/query).
- **Lowest sampled Ollama memory:** `starcoder2` (1352.5 MiB).
- **Lowest sampled GPU memory:** `starcoder2` (3546.5 MiB).

## Category winners

A model must first complete the shared question set. Each winner is then selected using the category's primary metric followed by the documented tie-breakers.

| Category | Primary metric | Winner | Primary result | Tie-breakers |
|---|---|---|---|---|
| Explanation | accuracy | `codellama` | 66.7% | relevance, hallucination rate, latency |
| Code Retrieval | retrieval quality | `qwen2.5-coder` | 100.0% | accuracy, relevance, latency |
| Dependency Understanding | accuracy | `qwen2.5-coder` | 83.3% | retrieval quality, hallucination rate, latency |
| Bug Analysis | accuracy | `codellama` | 22.2% | hallucination rate, relevance, latency |
| Code Generation | test-pass rate | `qwen2.5-coder` | 66.7% | accuracy, hallucination rate, latency |
| Refactoring | accuracy | `qwen2.5-coder` | 55.6% | relevance, hallucination rate, latency |
| RAG | accuracy | `codellama` | 90.0% | retrieval quality, relevance, hallucination rate |

## Category-wise quantitative comparison

### Explanation

**Decision rule:** complete all shared questions, then highest accuracy, then highest relevance, then lowest hallucination rate, then lowest latency.

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 4/4 | 0 | 66.7% | 0.754 | 100.0% | 25.0% | n/a | 9.65 s | 893.8 | 5.5% | 36.9 MiB | 60.5% | 1258.8 MiB | 46.4% | 5399.1 MiB |
| starcoder2 | 4/4 | 0 | 41.7% | 0.629 | 100.0% | 0.0% | n/a | 7.02 s | 839.0 | 3.1% | 38.0 MiB | 33.0% | 1237.6 MiB | 32.1% | 3729.9 MiB |
| qwen2.5-coder | 4/4 | 0 | 66.7% | 0.741 | 100.0% | 0.0% | n/a | 11.69 s | 644.0 | 2.9% | 37.8 MiB | 60.3% | 1641.4 MiB | 37.6% | 5507.3 MiB |

**Result:** `codellama` ranks first for Explanation under this rule.

### Code Retrieval

**Decision rule:** complete all shared questions, then highest retrieval quality, then highest accuracy, then highest relevance, then lowest latency.

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 3/3 | 0 | 50.0% | 0.814 | 100.0% | 0.0% | n/a | 3.61 s | 814.0 | 1.5% | 37.7 MiB | 41.9% | 1712.0 MiB | 43.4% | 7547.2 MiB |
| starcoder2 | 3/3 | 0 | 50.0% | 0.536 | 100.0% | 0.0% | n/a | 3.80 s | 812.3 | 3.0% | 39.2 MiB | 39.1% | 1363.0 MiB | 39.7% | 3487.8 MiB |
| qwen2.5-coder | 3/3 | 0 | 83.3% | 0.862 | 100.0% | 0.0% | n/a | 2.87 s | 602.3 | 3.5% | 38.7 MiB | 31.7% | 2891.6 MiB | 27.0% | 7752.4 MiB |

**Result:** `qwen2.5-coder` ranks first for Code Retrieval under this rule.

### Dependency Understanding

**Decision rule:** complete all shared questions, then highest accuracy, then highest retrieval quality, then lowest hallucination rate, then lowest latency.

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 3/3 | 0 | 61.1% | 0.785 | 66.7% | 33.3% | n/a | 4.46 s | 860.0 | 1.5% | 38.1 MiB | 54.9% | 2114.3 MiB | 46.2% | 7547.9 MiB |
| starcoder2 | 3/3 | 0 | 77.8% | 0.461 | 66.7% | 0.0% | n/a | 5.26 s | 946.3 | 3.3% | 38.3 MiB | 61.0% | 1367.9 MiB | 54.6% | 3497.1 MiB |
| qwen2.5-coder | 3/3 | 0 | 83.3% | 0.802 | 66.7% | 33.3% | n/a | 3.76 s | 635.0 | 3.2% | 38.7 MiB | 41.3% | 2901.4 MiB | 38.0% | 7773.9 MiB |

**Result:** `qwen2.5-coder` ranks first for Dependency Understanding under this rule.

### Bug Analysis

**Decision rule:** complete all shared questions, then highest accuracy, then lowest hallucination rate, then highest relevance, then lowest latency.

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 3/3 | 0 | 22.2% | 0.735 | 100.0% | 0.0% | n/a | 4.54 s | 868.3 | 2.2% | 38.1 MiB | 50.1% | 2149.9 MiB | 49.9% | 7559.2 MiB |
| starcoder2 | 3/3 | 0 | 22.2% | 0.718 | 100.0% | 33.3% | n/a | 4.38 s | 873.0 | 3.9% | 38.9 MiB | 47.5% | 1369.9 MiB | 44.6% | 3512.0 MiB |
| qwen2.5-coder | 3/3 | 0 | 22.2% | 0.554 | 100.0% | 33.3% | n/a | 4.53 s | 677.3 | 3.5% | 39.4 MiB | 43.2% | 2865.9 MiB | 39.9% | 7780.9 MiB |

**Result:** `codellama` ranks first for Bug Analysis under this rule.

### Code Generation

**Decision rule:** complete all shared questions, then highest test-pass rate, then highest accuracy, then lowest hallucination rate, then lowest latency.

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 3/3 | 0 | 83.3% | 0.821 | 100.0% | 66.7% | 33.3% | 4.60 s | 893.0 | 2.8% | 38.1 MiB | 54.4% | 2165.6 MiB | 52.1% | 7572.5 MiB |
| starcoder2 | 3/3 | 0 | 66.7% | 0.623 | 100.0% | 100.0% | 0.0% | 4.78 s | 922.7 | 3.7% | 38.4 MiB | 55.8% | 1373.1 MiB | 53.8% | 3512.0 MiB |
| qwen2.5-coder | 3/3 | 0 | 100.0% | 0.930 | 100.0% | 100.0% | 66.7% | 3.31 s | 645.0 | 3.9% | 38.8 MiB | 37.0% | 2814.4 MiB | 43.3% | 7782.2 MiB |

**Result:** `qwen2.5-coder` ranks first for Code Generation under this rule.

### Refactoring

**Decision rule:** complete all shared questions, then highest accuracy, then highest relevance, then lowest hallucination rate, then lowest latency.

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 3/3 | 0 | 55.6% | 0.812 | 66.7% | 0.0% | n/a | 7.85 s | 1036.7 | 2.5% | 38.2 MiB | 75.5% | 2169.7 MiB | 64.8% | 7414.7 MiB |
| starcoder2 | 3/3 | 0 | 11.1% | 0.562 | 66.7% | 0.0% | n/a | 5.23 s | 948.3 | 3.2% | 39.0 MiB | 60.8% | 1371.8 MiB | 56.5% | 3512.0 MiB |
| qwen2.5-coder | 3/3 | 0 | 55.6% | 0.827 | 66.7% | 100.0% | n/a | 8.92 s | 848.0 | 2.8% | 38.8 MiB | 79.8% | 2752.8 MiB | 73.9% | 7780.2 MiB |

**Result:** `qwen2.5-coder` ranks first for Refactoring under this rule.

### RAG

**Decision rule:** complete all shared questions, then highest accuracy, then highest retrieval quality, then highest relevance, then lowest hallucination rate.

| Model | Complete | Errors | Accuracy | Relevance | Retrieval | Hallucination | Test pass | Latency | Tokens | Client CPU | Client memory | Ollama CPU | Ollama memory | GPU | GPU memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codellama | 5/5 | 0 | 90.0% | 0.849 | 80.0% | 0.0% | n/a | 3.49 s | 823.2 | 3.6% | 39.1 MiB | 36.6% | 2589.4 MiB | 32.3% | 7361.8 MiB |
| starcoder2 | 5/5 | 0 | 70.0% | 0.667 | 80.0% | 0.0% | n/a | 4.73 s | 904.0 | 2.9% | 38.6 MiB | 53.9% | 1394.4 MiB | 49.0% | 3526.6 MiB |
| qwen2.5-coder | 5/5 | 0 | 80.0% | 0.837 | 80.0% | 0.0% | n/a | 3.41 s | 632.0 | 3.3% | 38.7 MiB | 37.3% | 2670.2 MiB | 39.3% | 7781.9 MiB |

**Result:** `codellama` ranks first for RAG under this rule.

## Quality–latency–resource trade-off

The most accurate model (`qwen2.5-coder`) is not the fastest model (`starcoder2`) and is not one of the lowest-memory models. This comparison separates answer quality, latency, token usage, client overhead, Ollama process consumption, and GPU consumption so the conclusion is based on measured evidence rather than appearance.

## Metric interpretation

- Accuracy is the fraction of expected answer keywords found in the response.
- Relevance is cosine similarity between response and question embeddings.
- Retrieval quality is one when the top retrieved chunk comes from the expected file, otherwise zero.
- Hallucination is a conservative flag for function or file claims absent from retrieved context.
- Test-pass rate executes the applicable generated Python function against its specified expression.
- Latency and Ollama token counts come from the real local model request.
- Resource metrics are sampled during each request; heuristic quality metrics should still be paired with manual review.
