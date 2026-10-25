import unittest

from dashboard.app import app, preset_insight_data


class DashboardTests(unittest.TestCase):
    def test_dashboard_is_one_page_with_all_codeimpact_sections(self):
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("CodeImpact AI", page)
        self.assertIn("Evaluation benchmarks &amp; active repository", page)
        self.assertIn('id="sharedRepo"', page)
        self.assertIn('id="remoteRepoUrl"', page)
        self.assertIn("Choose your model and API key", page)
        self.assertIn('id="llmApiKey"', page)
        self.assertIn('type="password" id="llmApiKey"', page)
        self.assertIn("Ask your codebase anything", page)
        self.assertIn('id="compareAll"', page)
        self.assertIn("Predict the ripple effect", page)
        self.assertIn('id="impactBase"', page)
        self.assertIn("Task-wise model winners", page)
        self.assertIn("Deterministic guardrails", page)
        for model in ("codellama", "starcoder2", "qwen2.5-coder"):
            self.assertIn(f'data-compare-model="{model}"', page)

    def test_visual_insights_tab_stays_removed(self):
        # The separate Visual Insights page was removed on request: everything lives on one page.
        client = app.test_client()
        self.assertEqual(client.get("/insights").status_code, 404)
        self.assertNotIn('href="/insights"', client.get("/").get_data(as_text=True))

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
