import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(relative_path):
    with open(os.path.join(ROOT, relative_path), encoding="utf-8") as handle:
        return handle.read()


class DockerConfigurationTests(unittest.TestCase):
    def test_compose_connects_every_service_to_the_expected_dependencies(self):
        compose = read("docker-compose.yml")
        for service in ("ingestion:", "app:", "dashboard:", "evaluation:"):
            self.assertIn(service, compose)
        self.assertIn("OLLAMA_BASE_URL: http://host.docker.internal:11434", compose)
        self.assertIn("INGESTION_SERVICE_URL: http://ingestion:5001", compose)
        self.assertIn("LLM_SERVICE_URL: http://app:5000", compose)
        self.assertIn("./evaluation:/repopilot/evaluation", compose)
        self.assertIn("./reports:/repopilot/reports", compose)

    def test_images_copy_the_modules_used_by_their_entrypoints(self):
        app_image = read("app/Dockerfile")
        ingestion_image = read("ingestion/Dockerfile")
        dashboard_image = read("dashboard/Dockerfile")
        evaluation_image = read("evaluation/Dockerfile")
        self.assertIn("COPY app/ app/", app_image)
        self.assertIn("COPY ingestion/ ingestion/", ingestion_image)
        for required in ("COPY dashboard/ dashboard/", "COPY evaluation/ evaluation/", "COPY reports/ reports/"):
            self.assertIn(required, dashboard_image)
        for required in (
            "COPY app/ app/",
            "COPY ingestion/ ingestion/",
            "COPY evaluation/ evaluation/",
            "COPY data/ data/",
            "COPY reports/ reports/",
            "COPY exercise3_rag_comparison.py .",
        ):
            self.assertIn(required, evaluation_image)

    def test_large_local_artifacts_are_excluded_from_build_context(self):
        dockerignore = read(".dockerignore")
        self.assertIn(".git", dockerignore.splitlines())
        self.assertIn(".venv", dockerignore.splitlines())
        self.assertIn("**/__pycache__", dockerignore.splitlines())


if __name__ == "__main__":
    unittest.main()
