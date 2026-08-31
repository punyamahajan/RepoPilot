"""Aggregate evaluation/results.json and generate the numerical comparison report."""

import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def aggregate_results(records):
    grouped = defaultdict(list)
    for row in records:
        grouped[row["model"]].append(row)
    output = {}
    for model, rows in grouped.items():
        valid_tests = [r["test_passed"] for r in rows if r.get("test_passed") is not None]
        mean = lambda key: sum(float(r.get(key, 0) or 0) for r in rows) / len(rows)
        output[model] = {
            "questions": len(rows), "accuracy": mean("accuracy"), "relevance": mean("relevance"),
            "retrieval_quality": mean("retrieval_quality"), "latency_seconds": mean("latency_seconds"),
            "total_tokens": mean("total_tokens"), "cpu_percent": mean("cpu_percent_avg"),
            "memory_mb": mean("memory_mb_avg"),
            "hallucination_rate": sum(bool(r.get("hallucinated")) for r in rows) / len(rows),
            "test_pass_rate": sum(valid_tests) / len(valid_tests) if valid_tests else None,
        }
    return output


def render_table(aggregates):
    headers = ["Model", "Accuracy", "Relevance", "Retrieval", "Latency(s)", "Tokens", "CPU%", "Memory MiB", "Hallucination", "Test pass"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for model, x in aggregates.items():
        test = "n/a" if x["test_pass_rate"] is None else f"{x['test_pass_rate']:.1%}"
        lines.append(f"| {model} | {x['accuracy']:.1%} | {x['relevance']:.3f} | {x['retrieval_quality']:.1%} | {x['latency_seconds']:.2f} | {x['total_tokens']:.1f} | {x['cpu_percent']:.1f} | {x['memory_mb']:.1f} | {x['hallucination_rate']:.1%} | {test} |")
    return "\n".join(lines)


def main(results_path=os.path.join(HERE, "results.json"), output_path=os.path.join(HERE, "ANALYSIS.md")):
    with open(results_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    aggregates = aggregate_results(payload.get("results", payload))
    if not aggregates:
        raise ValueError("No evaluation records found")
    table = render_table(aggregates)
    print(table)
    best_accuracy = max(aggregates, key=lambda m: aggregates[m]["accuracy"])
    least_hallucination = min(aggregates, key=lambda m: aggregates[m]["hallucination_rate"])
    fastest = min(aggregates, key=lambda m: aggregates[m]["latency_seconds"])
    fewest_tokens = min(aggregates, key=lambda m: aggregates[m]["total_tokens"])
    least_cpu = min(aggregates, key=lambda m: aggregates[m]["cpu_percent"])
    least_memory = min(aggregates, key=lambda m: aggregates[m]["memory_mb"])
    same = len({best_accuracy, fastest, least_cpu, least_memory}) == 1
    text = f"""# Week 4 Model Evaluation Analysis

Generated from `results.json`; all values are averages across the same questions and retrieved context.

{table}

## Findings

- **Most accurate:** `{best_accuracy}` ({aggregates[best_accuracy]['accuracy']:.1%}).
- **Least hallucination:** `{least_hallucination}` ({aggregates[least_hallucination]['hallucination_rate']:.1%} flagged).
- **Fastest:** `{fastest}` ({aggregates[fastest]['latency_seconds']:.2f} seconds/query).
- **Fewest tokens:** `{fewest_tokens}` ({aggregates[fewest_tokens]['total_tokens']:.1f} tokens/query).
- **Lowest sampled CPU:** `{least_cpu}` ({aggregates[least_cpu]['cpu_percent']:.1f}%).
- **Lowest sampled client memory:** `{least_memory}` ({aggregates[least_memory]['memory_mb']:.1f} MiB).

## Trade-off

{"The highest-accuracy model is also the fastest and lowest-resource model in this run; no clear efficiency trade-off was observed." if same else f"There is a measurable trade-off: `{best_accuracy}` is most accurate, while `{fastest}` is fastest, `{least_cpu}` uses the least sampled CPU, and `{least_memory}` uses the least client memory. The best model is therefore not uniformly the most efficient."}

CPU and memory measure the Python evaluation client during each HTTP request, not the host Ollama daemon. Token counts come directly from Ollama. The hallucination detector is a conservative identifier/file-name heuristic and should be paired with manual review.
"""
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
