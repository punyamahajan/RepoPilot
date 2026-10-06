"""Analyse how retrieved context affects answers recorded by the evaluator."""

import argparse
import json
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))


def source_file(chunk):
    return chunk.split(" (chunk", 1)[0].replace("\\", "/")


def expected_file_present(row):
    expected = str(row.get("expected_file", "")).replace("\\", "/")
    return any(
        source_file(chunk) == expected or source_file(chunk).endswith("/" + expected)
        for chunk in row.get("retrieved_chunks", [])
    )


def classify_row(row):
    chunks = row.get("retrieved_chunks", [])
    return {
        "relevant_information_retrieved": expected_file_present(row),
        "irrelevant_top_result": bool(chunks) and not bool(row.get("retrieval_quality")),
        "important_information_missed": bool(row.get("expected_file")) and not expected_file_present(row),
        "correct_answer": float(row.get("accuracy", 0) or 0) == 1.0,
        "hallucinated_despite_context": bool(chunks) and bool(row.get("hallucinated")),
    }


BUCKETS = [
    (
        "Relevant information was retrieved",
        "relevant_information_retrieved",
        "At least one retrieved chunk came from the expected source file.",
    ),
    (
        "Irrelevant information was retrieved first",
        "irrelevant_top_result",
        "Context was returned, but its top-ranked chunk did not come from the expected source file.",
    ),
    (
        "Important information was missed",
        "important_information_missed",
        "None of the retrieved chunks came from the expected source file.",
    ),
    (
        "The LLM produced a correct answer",
        "correct_answer",
        "The response contained every expected answer keyword.",
    ),
    (
        "The LLM hallucinated despite having context",
        "hallucinated_despite_context",
        "The response made an identifiable function or file claim absent from its retrieved context.",
    ),
]


def _render_example(row, classification):
    chunks = row.get("retrieved_chunks", [])
    lines = [
        f"### {row['question_id']}: {row['question']}",
        "",
        f"- Category: **{row['category']}**",
        f"- Expected file: `{row.get('expected_file', '')}`",
        f"- Top retrieval correct: **{'yes' if row.get('retrieval_quality') else 'no'}**",
        f"- Expected file present anywhere: **{'yes' if classification['relevant_information_retrieved'] else 'no'}**",
        f"- Answer accuracy: **{float(row.get('accuracy', 0) or 0):.1%}**",
        f"- Hallucination flag: **{'yes' if row.get('hallucinated') else 'no'}**",
        "",
        "#### Question → Retrieved context → LLM response",
        "",
        f"**Question:** {row['question']}",
        "",
        "**Retrieved context:**",
        "",
        "```",
        "\n\n".join(chunks) if chunks else "(none)",
        "```",
        "",
        "**LLM response:**",
        "",
        row.get("response", "(empty)"),
        "",
    ]
    return lines


def build_report(records, model, examples_per_condition=2, controlled_case=None):
    rows = [
        row for row in records
        if row.get("model") == model
        and not row.get("error")
        and str(row.get("response", "")).strip()
    ]
    if not rows:
        raise ValueError(f"No successful evaluation records found for model {model!r}")

    classified = [(row, classify_row(row)) for row in rows]
    counts = {
        key: sum(flags[key] for _, flags in classified)
        for _, key, _ in BUCKETS
    }
    top_relevant = sum(bool(row.get("retrieval_quality")) for row in rows)
    top_relevant_correct = sum(
        bool(row.get("retrieval_quality")) and flags["correct_answer"]
        for row, flags in classified
    )
    top_relevant_hallucinated = sum(
        bool(row.get("retrieval_quality")) and flags["hallucinated_despite_context"]
        for row, flags in classified
    )
    top_irrelevant = len(rows) - top_relevant
    top_irrelevant_correct = sum(
        not bool(row.get("retrieval_quality")) and flags["correct_answer"]
        for row, flags in classified
    )

    lines = [
        "# RAG Pipeline Analysis",
        "",
        f"Model: `{model}`. Source: the same recorded evaluation questions, retrieved chunks, and responses used in the quantitative comparison.",
        "",
        "## Retrieval → context → response summary",
        "",
        "| Observation | Count |",
        "|---|---:|",
    ]
    for title, key, _ in BUCKETS:
        lines.append(f"| {title} | {counts[key]}/{len(rows)} |")

    if controlled_case:
        lines += [
            "## Controlled missed-information trace",
            "",
            "The 24-question benchmark retrieves all three chunks from this three-file sample, so it cannot naturally demonstrate omitted context. This additional sensitivity case deliberately uses `k=1` for a question that requires two files; it is reported separately and is not mixed into the model-comparison scores.",
            "",
            f"- Retrieval depth: **{controlled_case.get('k')}**",
            f"- Expected files: **{', '.join(controlled_case.get('expected_files', []))}**",
            f"- Retrieved files: **{', '.join(controlled_case.get('retrieved_files', [])) or '(none)'}**",
            f"- Important information missed: **{', '.join(controlled_case.get('missing_files', [])) or 'none'}**",
            "",
            "### Question → Retrieved context → LLM response",
            "",
            f"**Question:** {controlled_case.get('question', '')}",
            "",
            "**Retrieved context:**",
            "",
            "```",
            "\n\n".join(controlled_case.get("retrieved_chunks", [])) or "(none)",
            "```",
            "",
            "**LLM response:**",
            "",
            controlled_case.get("response", "(empty)"),
            "",
        ]

    lines += [
        "",
        "## Relationship analysis",
        "",
        f"- The expected file was the top result for **{top_relevant}/{len(rows)}** questions.",
        f"- When the expected file ranked first, **{top_relevant_correct}/{top_relevant}** answers were fully correct." if top_relevant else "- No question had the expected file ranked first.",
        f"- Even with the expected file ranked first, **{top_relevant_hallucinated}/{top_relevant}** answers triggered the hallucination heuristic." if top_relevant else "- Hallucination-with-relevant-context could not be measured.",
        f"- When another file ranked first, **{top_irrelevant_correct}/{top_irrelevant}** answers were still fully correct." if top_irrelevant else "- No question had an irrelevant top-ranked file.",
        "",
        "These counts separate three different failure points: retrieval can rank the wrong source, the assembled context can omit an important source, and the LLM can still misuse relevant context. A RAG call is therefore only successful when retrieval, context construction, and generation all succeed together.",
        "",
        "## Representative traces",
        "",
    ]

    for title, key, definition in BUCKETS:
        matches = [(row, flags) for row, flags in classified if flags[key]]
        lines += [f"## {title}", "", definition, ""]
        if not matches:
            lines += [
                "**No example was observed in this run.** This is reported explicitly rather than inventing a failure case.",
                "",
            ]
            continue
        for row, flags in matches[:examples_per_condition]:
            lines += _render_example(row, flags)

    lines += [
        "## Conclusion",
        "",
        "The measured evidence shows that retrieval quality influences which facts are available, but correct retrieval does not guarantee a correct or non-hallucinated response. Conversely, a model can sometimes answer despite a poor top result because another useful chunk is present or because the model already knows a plausible answer. The full Question → Retrieved Context → Response trace must therefore be inspected alongside quantitative retrieval and answer metrics.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=os.path.join(HERE, "results.json"))
    parser.add_argument("--model", default=os.getenv("RAG_ANALYSIS_MODEL", "codellama"))
    parser.add_argument("--output", default=os.path.join(HERE, "RAG_PIPELINE_ANALYSIS.md"))
    parser.add_argument("--examples-per-condition", type=int, default=2)
    parser.add_argument(
        "--controlled-case",
        default=os.path.join(HERE, "RAG_MISSED_CONTEXT_CASE.json"),
    )
    args = parser.parse_args()

    with open(args.results, encoding="utf-8") as handle:
        payload = json.load(handle)
    controlled_case = None
    if os.path.exists(args.controlled_case):
        with open(args.controlled_case, encoding="utf-8") as handle:
            controlled_case = json.load(handle)
    report = build_report(
        payload.get("results", payload),
        args.model,
        max(1, args.examples_per_condition),
        controlled_case,
    )
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
