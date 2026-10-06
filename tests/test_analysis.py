import unittest

from evaluation.analyze_results import (
    CATEGORY_ORDER,
    aggregate_by_category,
    aggregate_results,
    build_report,
    select_category_winners,
)


def record(model, category, question_id, accuracy, **overrides):
    row = {
        "model": model,
        "category": category,
        "question_id": question_id,
        "question": question_id,
        "response": "answer",
        "error": None,
        "accuracy": accuracy,
        "relevance": 0.75,
        "retrieval_quality": 1.0,
        "latency_seconds": 2.0,
        "total_tokens": 100,
        "cpu_percent_avg": 3.0,
        "memory_mb_avg": 40.0,
        "ollama_cpu_percent_avg": 30.0,
        "ollama_memory_mb_avg": 500.0,
        "gpu_utilization_percent_avg": 60.0,
        "gpu_memory_mb_avg": 2000.0,
        "hallucinated": False,
        "test_passed": None,
    }
    row.update(overrides)
    return row


class AnalysisTests(unittest.TestCase):
    def test_failed_responses_are_reported_but_excluded_from_means(self):
        rows = [
            record("model-a", "code explanation", "q1", 1.0),
            record(
                "model-a",
                "code explanation",
                "q2",
                0.0,
                response="",
                error="timeout",
            ),
        ]
        values = aggregate_results(rows)["model-a"]
        self.assertEqual(values["questions"], 2)
        self.assertEqual(values["completed"], 1)
        self.assertEqual(values["errors"], 1)
        self.assertEqual(values["accuracy"], 1.0)

    def test_category_winner_prefers_complete_shared_question_coverage(self):
        rows = [
            record("complete", "code explanation", "q1", 0.5),
            record("complete", "code explanation", "q2", 0.5),
            record("incomplete", "code explanation", "q1", 1.0),
            record(
                "incomplete",
                "code explanation",
                "q2",
                0.0,
                response="",
                error="timeout",
            ),
        ]
        grouped = aggregate_by_category(rows)
        winners = select_category_winners(grouped)
        self.assertEqual(winners["code explanation"]["model"], "complete")

    def test_report_contains_every_category_and_tradeoff_analysis(self):
        rows = []
        for index, category in enumerate(CATEGORY_ORDER):
            for model, accuracy in (("model-a", 1.0), ("model-b", 0.5)):
                rows.append(record(model, category, f"q{index}", accuracy))
        report = build_report(rows)
        self.assertIn("## Category winners", report)
        self.assertIn("## Quality–latency–resource trade-off", report)
        for heading in (
            "Explanation",
            "Code Retrieval",
            "Dependency Understanding",
            "Bug Analysis",
            "Code Generation",
            "Refactoring",
            "RAG",
        ):
            self.assertIn(f"### {heading}", report)


if __name__ == "__main__":
    unittest.main()
