import os
import tempfile
import unittest

from evaluation.rag_pipeline_analysis import classify_row
from exercise3_rag_comparison import write_report


class ReportTests(unittest.TestCase):
    def test_rag_classification_distinguishes_retrieval_and_generation(self):
        row = {
            "expected_file": "auth.py",
            "retrieved_chunks": ["payment.py (chunk 0): code"],
            "retrieval_quality": 0.0,
            "accuracy": 1.0,
            "hallucinated": True,
        }
        flags = classify_row(row)
        self.assertTrue(flags["irrelevant_top_result"])
        self.assertTrue(flags["important_information_missed"])
        self.assertTrue(flags["correct_answer"])
        self.assertTrue(flags["hallucinated_despite_context"])

    def test_week3_report_replaces_manual_notes_with_evidence(self):
        results = [{
            "question": "What does login do?",
            "context": "auth.py (chunk 0): login",
            "rag_response": "find_user verify_password session token",
            "no_rag_response": "login",
            "retrieval_quality": 1.0,
            "rag_accuracy": 1.0,
            "no_rag_accuracy": 0.0,
            "rag_hallucinated": False,
            "no_rag_ungrounded": False,
        }]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "report.md")
            write_report(results, path)
            with open(path, encoding="utf-8") as handle:
                report = handle.read()
        self.assertIn("## Quantitative summary", report)
        self.assertIn("### Evidence-based interpretation", report)
        self.assertIn("## Conclusion", report)
        self.assertNotIn("fill in manually", report)


if __name__ == "__main__":
    unittest.main()
