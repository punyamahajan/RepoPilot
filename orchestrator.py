"""Application Service CLI: retrieval API -> LLM API -> answer."""

import argparse
import os

import requests


INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "http://localhost:5001"
).rstrip("/")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5000").rstrip("/")


def ask(question: str, k: int = 3, model: str = "codellama") -> dict:
    retrieval = requests.post(
        f"{INGESTION_SERVICE_URL}/search",
        json={"query": question, "k": k},
        timeout=60,
    )
    retrieval.raise_for_status()
    chunks = retrieval.json()["chunks"]

    llm = requests.post(
        f"{LLM_SERVICE_URL}/ask",
        json={
            "prompt": question,
            "context": "\n\n".join(chunks),
            "use_retrieval": False,
            "model": model,
        },
        timeout=180,
    )
    llm.raise_for_status()
    return llm.json()


def main():
    parser = argparse.ArgumentParser(description="Ask RepoPilot through both services")
    parser.add_argument("question", help="Question about the indexed repository")
    parser.add_argument("--k", type=int, default=3, help="Context chunks to retrieve")
    parser.add_argument("--model", default="codellama", help="Ollama model name")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k must be positive")

    result = ask(args.question, k=args.k, model=args.model)
    print(result["response"])


if __name__ == "__main__":
    main()
