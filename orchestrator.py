"""Application Service CLI: guarded LLM API -> retrieval -> answer."""

import argparse
import os

import requests


LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5000").rstrip("/")


def ask(question: str, k: int = 3, model: str = "codellama") -> dict:
    llm = requests.post(
        f"{LLM_SERVICE_URL}/ask",
        json={
            "prompt": question,
            "use_retrieval": True,
            "k": k,
            "model": model,
        },
        timeout=600,
    )
    llm.raise_for_status()
    return llm.json()


def main():
    parser = argparse.ArgumentParser(description="Ask RepoPilot through both services")
    parser.add_argument("question", help="Question about the indexed repository")
    parser.add_argument("--k", type=int, default=3, help="Context chunks to retrieve")
    parser.add_argument("--model", default="codellama", help="Ollama model name")
    args = parser.parse_args()
    if not 1 <= args.k <= 5:
        parser.error("--k must be between 1 and 5")

    result = ask(args.question, k=args.k, model=args.model)
    print(result["response"])


if __name__ == "__main__":
    main()
