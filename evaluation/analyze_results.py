"""Aggregate evaluation results into overall and category-wise comparisons."""

import json
import os
from collections import defaultdict


HERE = os.path.dirname(os.path.abspath(__file__))

CATEGORY_ORDER = [
    "code explanation",
    "code retrieval",
    "dependency understanding",
    "bug analysis",
    "code generation",
    "refactoring suggestion",
    "RAG-based questions about docs",
]

CATEGORY_LABELS = {
    "code explanation": "Explanation",
    "code retrieval": "Code Retrieval",
    "dependency understanding": "Dependency Understanding",
    "bug analysis": "Bug Analysis",
    "code generation": "Code Generation",
    "refactoring suggestion": "Refactoring",
    "RAG-based questions about docs": "RAG",
}

# A model must first complete the shared question set. These rules then apply
# one category-specific primary metric followed by transparent tie-breakers.
CATEGORY_RULES = {
    "code explanation": (
        ("accuracy", True),
        [("relevance", True), ("hallucination_rate", False), ("latency_seconds", False)],
    ),
    "code retrieval": (
        ("retrieval_quality", True),
        [("accuracy", True), ("relevance", True), ("latency_seconds", False)],
    ),
    "dependency understanding": (
        ("accuracy", True),
        [("retrieval_quality", True), ("hallucination_rate", False), ("latency_seconds", False)],
    ),
    "bug analysis": (
        ("accuracy", True),
        [("hallucination_rate", False), ("relevance", True), ("latency_seconds", False)],
    ),
    "code generation": (
        ("test_pass_rate", True),
        [("accuracy", True), ("hallucination_rate", False), ("latency_seconds", False)],
    ),
    "refactoring suggestion": (
        ("accuracy", True),
        [("relevance", True), ("hallucination_rate", False), ("latency_seconds", False)],
    ),
    "RAG-based questions about docs": (
        ("accuracy", True),
        [("retrieval_quality", True), ("relevance", True), ("hallucination_rate", False)],
    ),
}

METRIC_LABELS = {
    "accuracy": "accuracy",
    "relevance": "relevance",
    "retrieval_quality": "retrieval quality",
    "hallucination_rate": "hallucination rate",
    "test_pass_rate": "test-pass rate",
    "latency_seconds": "latency",
    "total_tokens": "token usage",
    "cpu_percent": "client CPU",
    "memory_mb": "client memory",
    "ollama_cpu_percent": "Ollama CPU",
    "ollama_memory_mb": "Ollama memory",
    "gpu_utilization_percent": "GPU utilization",
    "gpu_memory_mb": "GPU memory",
}


def _successful_rows(rows):
    return [
        row for row in rows
        if not row.get("error") and str(row.get("response", "")).strip()
    ]


def _mean(rows, key):
    return sum(float(row.get(key, 0) or 0) for row in rows) / len(rows) if rows else 0.0


def _aggregate_group(rows):
    successful = _successful_rows(rows)
    valid_tests = [row["test_passed"] for row in successful if row.get("test_passed") is not None]
    attempted = len(rows)
    completed = len(successful)
    return {
        "questions": attempted,
        "completed": completed,
        "errors": attempted - completed,
        "completion_rate": completed / attempted if attempted else 0.0,
        "accuracy": _mean(successful, "accuracy"),
        "relevance": _mean(successful, "relevance"),
        "retrieval_quality": _mean(successful, "retrieval_quality"),
        "latency_seconds": _mean(successful, "latency_seconds"),
        "total_tokens": _mean(successful, "total_tokens"),
        "cpu_percent": _mean(successful, "cpu_percent_avg"),
        "memory_mb": _mean(successful, "memory_mb_avg"),
        "ollama_cpu_percent": _mean(successful, "ollama_cpu_percent_avg"),
        "ollama_memory_mb": _mean(successful, "ollama_memory_mb_avg"),
        "gpu_utilization_percent": _mean(successful, "gpu_utilization_percent_avg"),
        "gpu_memory_mb": _mean(successful, "gpu_memory_mb_avg"),
        "hallucination_rate": (
            sum(bool(row.get("hallucinated")) for row in successful) / completed
            if completed else 0.0
        ),
        "test_pass_rate": sum(valid_tests) / len(valid_tests) if valid_tests else None,
    }


def aggregate_results(records):
    """Return overall metrics grouped by model, excluding failed responses from means."""
    grouped = defaultdict(list)
    for row in records:
        grouped[row["model"]].append(row)
    return {model: _aggregate_group(rows) for model, rows in grouped.items()}


def aggregate_by_category(records):
    """Return metrics grouped first by category and then by model."""
    grouped = defaultdict(lambda: defaultdict(list))
    for row in records:
        grouped[row["category"]][row["model"]].append(row)

    ordered = {}
    for category in CATEGORY_ORDER:
        if category in grouped:
            ordered[category] = {
                model: _aggregate_group(rows)
                for model, rows in grouped[category].items()
            }
    for category in sorted(set(grouped) - set(ordered)):
        ordered[category] = {
            model: _aggregate_group(rows)
            for model, rows in grouped[category].items()
        }
    return ordered


def _rank_value(value, maximize):
    if value is None:
        return float("-inf")
    numeric = float(value)
    return numeric if maximize else -numeric


def select_category_winners(category_aggregates):
    """Choose one model per category using documented, category-specific rules."""
    winners = {}
    for category, model_values in category_aggregates.items():
        primary, tie_breakers = CATEGORY_RULES.get(
            category,
            (("accuracy", True), [("relevance", True), ("latency_seconds", False)]),
        )

        def ranking(item):
            _, values = item
            return (
                values["completion_rate"],
                *[
                    _rank_value(values.get(metric), maximize)
                    for metric, maximize in [primary, *tie_breakers]
                ],
            )

        model, values = max(model_values.items(), key=ranking)
        winners[category] = {
            "model": model,
            "primary_metric": primary[0],
            "primary_value": values.get(primary[0]),
            "completion_rate": values["completion_rate"],
            "tie_breakers": [metric for metric, _ in tie_breakers],
        }
    return winners


def _format_metric(name, value):
    if value is None:
        return "n/a"
    if name in {
        "accuracy", "retrieval_quality", "hallucination_rate",
        "test_pass_rate", "completion_rate",
    }:
        return f"{value:.1%}"
    if name == "relevance":
        return f"{value:.3f}"
    if name == "latency_seconds":
        return f"{value:.2f} s"
    if name in {"memory_mb", "ollama_memory_mb", "gpu_memory_mb"}:
        return f"{value:.1f} MiB"
    if name in {"cpu_percent", "ollama_cpu_percent", "gpu_utilization_percent"}:
        return f"{value:.1f}%"
    return f"{value:.1f}"


def render_table(aggregates):
    """Render one model-comparison table for Markdown output."""
    headers = [
        "Model", "Complete", "Errors", "Accuracy", "Relevance", "Retrieval",
        "Hallucination", "Test pass", "Latency", "Tokens", "Client CPU",
        "Client memory", "Ollama CPU", "Ollama memory", "GPU", "GPU memory",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for model, values in aggregates.items():
        row = [
            model,
            f"{values['completed']}/{values['questions']}",
            str(values["errors"]),
            _format_metric("accuracy", values["accuracy"]),
            _format_metric("relevance", values["relevance"]),
            _format_metric("retrieval_quality", values["retrieval_quality"]),
            _format_metric("hallucination_rate", values["hallucination_rate"]),
            _format_metric("test_pass_rate", values["test_pass_rate"]),
            _format_metric("latency_seconds", values["latency_seconds"]),
            _format_metric("total_tokens", values["total_tokens"]),
            _format_metric("cpu_percent", values["cpu_percent"]),
            _format_metric("memory_mb", values["memory_mb"]),
            _format_metric("ollama_cpu_percent", values["ollama_cpu_percent"]),
            _format_metric("ollama_memory_mb", values["ollama_memory_mb"]),
            _format_metric("gpu_utilization_percent", values["gpu_utilization_percent"]),
            _format_metric("gpu_memory_mb", values["gpu_memory_mb"]),
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _metric_winner(aggregates, metric, maximize=True, require_value=False):
    candidates = {
        model: values for model, values in aggregates.items()
        if not require_value or values.get(metric) is not None
    }
    if not candidates:
        return None
    chooser = max if maximize else min
    return chooser(candidates, key=lambda model: candidates[model][metric])


def _metric_leader_text(aggregates, metric, maximize=True):
    """Format all overall leaders so exact ties are not reported as single winners."""
    values = {
        model: row[metric]
        for model, row in aggregates.items()
        if row.get(metric) is not None
    }
    if not values:
        return "n/a", None
    target = (max if maximize else min)(values.values())
    leaders = [model for model, value in values.items() if abs(value - target) < 1e-12]
    names = ", ".join(f"`{model}`" for model in leaders)
    return names, target


def _coverage_statement(records):
    questions_by_model = defaultdict(set)
    for row in records:
        questions_by_model[row["model"]].add(row.get("question_id", row.get("question")))
    counts = {model: len(question_ids) for model, question_ids in questions_by_model.items()}
    same = len({frozenset(ids) for ids in questions_by_model.values()}) <= 1
    detail = ", ".join(f"`{model}`: {count}" for model, count in counts.items())
    return same, detail


def build_report(records):
    """Build the complete Week 4 quantitative analysis as Markdown."""
    overall = aggregate_results(records)
    if not overall:
        raise ValueError("No evaluation records found")
    by_category = aggregate_by_category(records)
    winners = select_category_winners(by_category)
    same_questions, coverage = _coverage_statement(records)

    total_errors = sum(values["errors"] for values in overall.values())
    best_accuracy = _metric_winner(overall, "accuracy")
    best_retrieval = _metric_winner(overall, "retrieval_quality")
    least_hallucination = _metric_winner(overall, "hallucination_rate", maximize=False)
    best_tests = _metric_winner(overall, "test_pass_rate", require_value=True)
    fastest = _metric_winner(overall, "latency_seconds", maximize=False)
    fewest_tokens = _metric_winner(overall, "total_tokens", maximize=False)
    least_gpu_memory = _metric_winner(overall, "gpu_memory_mb", maximize=False)
    least_ollama_memory = _metric_winner(overall, "ollama_memory_mb", maximize=False)
    accuracy_leaders = _metric_leader_text(overall, "accuracy")
    retrieval_leaders = _metric_leader_text(overall, "retrieval_quality")
    hallucination_leaders = _metric_leader_text(overall, "hallucination_rate", maximize=False)
    test_leaders = _metric_leader_text(overall, "test_pass_rate")
    latency_leaders = _metric_leader_text(overall, "latency_seconds", maximize=False)
    token_leaders = _metric_leader_text(overall, "total_tokens", maximize=False)
    ollama_memory_leaders = _metric_leader_text(overall, "ollama_memory_mb", maximize=False)
    gpu_memory_leaders = _metric_leader_text(overall, "gpu_memory_mb", maximize=False)

    lines = [
        "# Week 4 Model Evaluation Analysis",
        "",
        "Generated from `results.json`. Failed or empty model responses are reported as errors and are excluded from metric means instead of being silently scored as zero.",
        "",
        "## Evaluation validity",
        "",
        f"- Same question set used by every model: **{'yes' if same_questions else 'no'}** ({coverage}).",
        f"- Failed or empty responses: **{total_errors}**.",
        "- CPU and memory are reported separately for the Python client and Ollama processes.",
        "- GPU utilization and VRAM are sampled with `nvidia-smi` when an NVIDIA GPU is available; otherwise they remain zero and should be reported as unavailable.",
        "",
        "## Overall comparison",
        "",
        render_table(overall),
        "",
        "## Overall findings",
        "",
        f"- **Highest accuracy:** {accuracy_leaders[0]} ({_format_metric('accuracy', accuracy_leaders[1])}).",
        f"- **Best retrieval quality:** {retrieval_leaders[0]} ({_format_metric('retrieval_quality', retrieval_leaders[1])}).",
        f"- **Fewest hallucinations:** {hallucination_leaders[0]} ({_format_metric('hallucination_rate', hallucination_leaders[1])}).",
        (
            f"- **Highest generated-code test-pass rate:** {test_leaders[0]} "
            f"({_format_metric('test_pass_rate', test_leaders[1])})."
            if best_tests else "- **Generated-code test-pass rate:** no applicable test results."
        ),
        f"- **Lowest response latency:** {latency_leaders[0]} ({_format_metric('latency_seconds', latency_leaders[1])}).",
        f"- **Fewest tokens:** {token_leaders[0]} ({_format_metric('total_tokens', token_leaders[1])} tokens/query).",
        f"- **Lowest sampled Ollama memory:** {ollama_memory_leaders[0]} ({_format_metric('ollama_memory_mb', ollama_memory_leaders[1])}).",
        f"- **Lowest sampled GPU memory:** {gpu_memory_leaders[0]} ({_format_metric('gpu_memory_mb', gpu_memory_leaders[1])}).",
        "",
        "## Category winners",
        "",
        "A model must first complete the shared question set. Each winner is then selected using the category's primary metric followed by the documented tie-breakers.",
        "",
        "| Category | Primary metric | Winner | Primary result | Tie-breakers |",
        "|---|---|---|---|---|",
    ]

    for category, winner in winners.items():
        label = CATEGORY_LABELS.get(category, category.title())
        primary = winner["primary_metric"]
        tie_breakers = ", ".join(METRIC_LABELS[name] for name in winner["tie_breakers"])
        lines.append(
            f"| {label} | {METRIC_LABELS[primary]} | `{winner['model']}` | "
            f"{_format_metric(primary, winner['primary_value'])} | {tie_breakers} |"
        )

    lines += ["", "## Category-wise quantitative comparison", ""]
    for category, aggregates in by_category.items():
        label = CATEGORY_LABELS.get(category, category.title())
        primary, tie_breakers = CATEGORY_RULES.get(
            category,
            (("accuracy", True), [("relevance", True), ("latency_seconds", False)]),
        )
        rule_parts = [
            f"{'highest' if primary[1] else 'lowest'} {METRIC_LABELS[primary[0]]}",
            *[
                f"{'highest' if maximize else 'lowest'} {METRIC_LABELS[metric]}"
                for metric, maximize in tie_breakers
            ],
        ]
        winner = winners[category]["model"]
        lines += [
            f"### {label}",
            "",
            f"**Decision rule:** complete all shared questions, then {', then '.join(rule_parts)}.",
            "",
            render_table(aggregates),
            "",
            f"**Result:** `{winner}` ranks first for {label} under this rule.",
            "",
        ]

    accurate_is_fastest = best_accuracy == fastest
    accurate_is_lowest_memory = best_accuracy in {least_gpu_memory, least_ollama_memory}
    lines += [
        "## Quality–latency–resource trade-off",
        "",
        f"The most accurate model (`{best_accuracy}`) is "
        f"{'also' if accurate_is_fastest else 'not'} the fastest model (`{fastest}`) and is "
        f"{'also' if accurate_is_lowest_memory else 'not'} one of the lowest-memory models. "
        "This comparison separates answer quality, latency, token usage, client overhead, Ollama process consumption, and GPU consumption so the conclusion is based on measured evidence rather than appearance.",
        "",
        "## Metric interpretation",
        "",
        "- Accuracy is the fraction of expected answer keywords found in the response.",
        "- Relevance is cosine similarity between response and question embeddings.",
        "- Retrieval quality is one when the top retrieved chunk comes from the expected file, otherwise zero.",
        "- Hallucination is a conservative flag for function or file claims absent from retrieved context.",
        "- Test-pass rate executes the applicable generated Python function against its specified expression.",
        "- Latency and Ollama token counts come from the real local model request.",
        "- Resource metrics are sampled during each request; heuristic quality metrics should still be paired with manual review.",
        "",
    ]
    return "\n".join(lines)


def main(results_path=os.path.join(HERE, "results.json"), output_path=os.path.join(HERE, "ANALYSIS.md")):
    with open(results_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("results", payload)
    report = build_report(records)
    print(report)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
