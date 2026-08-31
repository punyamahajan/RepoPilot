"""Run the complete dataset through retrieval and all configured models."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ingestion"))
import embeddings  # noqa: E402
from metrics import correctness, hallucination_flag, relevance, retrieval_quality, test_pass_rate  # noqa: E402
from run_models import MODELS, OLLAMA_BASE_URL, run_models  # noqa: E402

import requests

INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:5001").rstrip("/")
embeddings.OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embeddings"


def retrieve(question, k=3):
    response = requests.post(f"{INGESTION_URL}/search", json={"query": question, "k": k}, timeout=90)
    response.raise_for_status()
    return response.json().get("chunks", [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default=os.path.join(ROOT, "evaluation", "eval_questions.json"))
    parser.add_argument("--output", default=os.path.join(ROOT, "evaluation", "results.json"))
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    with open(args.questions, encoding="utf-8") as handle:
        questions = json.load(handle)[:args.limit]
    records = []
    for index, item in enumerate(questions, 1):
        print(f"[{index}/{len(questions)}] {item['id']}: {item['question']}", flush=True)
        chunks = retrieve(item["question"])
        context = "\n\n".join(chunks)
        question_embedding = embeddings.get_embedding(item["question"])
        for result in run_models(item["question"], context, args.models):
            response_embedding = embeddings.get_embedding(result["response"]) if result["response"] else []
            result.update({
                "question_id": item["id"], "question": item["question"], "category": item["category"],
                "expected_file": item["expected_file"], "retrieved_chunks": chunks,
                "accuracy": correctness(result["response"], item["expected_answer"]),
                "relevance": relevance(response_embedding, question_embedding),
                "retrieval_quality": retrieval_quality(chunks, item["expected_file"]),
                "hallucinated": hallucination_flag(result["response"], context),
                "test_passed": test_pass_rate(result["response"], item.get("test_case")),
            })
            records.append(result)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "models": args.models, "results": records}
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(f"Saved {len(records)} model-question results to {args.output}")


if __name__ == "__main__":
    main()
