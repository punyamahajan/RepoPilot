import unittest

from dashboard.app import app, preset_insight_data


class DashboardTests(unittest.TestCase):
    def test_dashboard_exposes_showcase_and_reliability_sections(self):
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Category-wise model winners", page)
        self.assertIn("Quantitative evaluation analysis", page)
        self.assertIn("RAG pipeline analysis", page)
        self.assertIn("Repository understanding", page)
        self.assertIn("Guardrail effectiveness", page)
        self.assertIn("AI output testing", page)
        self.assertIn("How reliability flows", page)
        self.assertIn("Guardrail coverage", page)
        self.assertIn("Open the complete Guardrail Effectiveness Analysis", page)

    def test_visual_insights_page_uses_graphs_and_keeps_saved_evidence(self):
        client = app.test_client()
        response = client.get("/insights")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Five representative evaluation questions", page)
        self.assertIn("Ask one repository question", page)
        self.assertIn('id="presetQuestionsGrid"', page)
        self.assertIn("Consistent model colors", page)
        self.assertIn("Best accuracy", page)
        self.assertNotIn('id="presetQuestion"', page)
        self.assertNotIn('id="overallRadar"', page)
        self.assertNotIn("Overall measurable comparison", page)
        self.assertNotIn("Category winners", page)
        self.assertIn('id="liveMetricGrid"', page)
        self.assertIn("Current live metric bar graphs", page)
        self.assertIn("comparison-metric-grid", page)
        self.assertIn('id="liveRadar"', page)
        self.assertIn("Question radar comparison", page)
        self.assertIn("Three-model vertical bar plot", page)
        self.assertNotIn("five-question session", page)
        self.assertNotIn('id="resetLive"', page)
        self.assertNotIn("<table", page.lower())

    def test_visual_insights_data_covers_five_presets_and_all_results(self):
        insights = preset_insight_data()
        self.assertEqual(insights["question_count"], 24)
        self.assertEqual(insights["run_count"], 72)
        self.assertEqual(len(insights["questions"]), 5)
        self.assertEqual(len(insights["category_winners"]), 7)
        self.assertEqual(
            set(insights["models"]),
            {"codellama", "starcoder2", "qwen2.5-coder"},
        )


if __name__ == "__main__":
    unittest.main()
