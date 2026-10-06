import unittest
from unittest.mock import Mock, patch

from app.ollama_client import query_llm_with_metrics


class OllamaClientMetricsTests(unittest.TestCase):
    @patch("app.ollama_client.requests.post")
    def test_query_returns_exact_ollama_token_metadata(self, post):
        response = Mock()
        response.json.return_value = {
            "response": "Repository-backed answer",
            "prompt_eval_count": 83,
            "eval_count": 17,
            "total_duration": 1_250_000_000,
        }
        post.return_value = response

        result = query_llm_with_metrics(
            "What does this do?", context="trusted repository evidence", model="codellama"
        )

        response.raise_for_status.assert_called_once_with()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["options"]["temperature"], 0.0)
        self.assertEqual(result["response"], "Repository-backed answer")
        self.assertEqual(result["prompt_tokens"], 83)
        self.assertEqual(result["completion_tokens"], 17)
        self.assertEqual(result["total_tokens"], 100)
        self.assertEqual(result["total_duration_ns"], 1_250_000_000)


if __name__ == "__main__":
    unittest.main()
