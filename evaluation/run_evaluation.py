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


def save_results(path, models, records):
    """Checkpoint completed model-question records after every successful result."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
        "results": records,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default=os.path.join(ROOT, "evaluation", "eval_questions.json"))
    parser.add_argument("--output", default=os.path.join(ROOT, "evaluation", "results.json"))
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    with open(args.questions, encoding="utf-8") as handle:
        questions = json.load(handle)[:args.limit]
    records = []
    if args.resume and os.path.exists(args.output):
        with open(args.output, encoding="utf-8") as handle:
            existing = json.load(handle)
        if existing.get("models") != args.models:
            raise ValueError("Cannot resume: output file uses a different model list")
        records = existing.get("results", [])
    completed = {(row.get("question_id"), row.get("model")) for row in records}

    prepared = {}
    for index, item in enumerate(questions, 1):
        if all((item["id"], model) in completed for model in args.models):
            continue
        print(f"Preparing [{index}/{len(questions)}] {item['id']}", flush=True)
        chunks = retrieve(item["question"])
        prepared[item["id"]] = {
            "chunks": chunks,
            "context": "\n\n".join(chunks),
            "question_embedding": embeddings.get_embedding(item["question"]),
        }

    # Keep one model loaded while it processes the complete shared dataset. This
    # avoids repeatedly swapping multi-gigabyte models without changing inputs.
    for model in args.models:
        for index, item in enumerate(questions, 1):
            if (item["id"], model) in completed:
                continue
            evidence = prepared[item["id"]]
            chunks = evidence["chunks"]
            context = evidence["context"]
            question_embedding = evidence["question_embedding"]
            print(f"[{model}] [{index}/{len(questions)}] {item['id']}: {item['question']}", flush=True)
            result = run_models(item["question"], context, [model])[0]
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
            completed.add((item["id"], result["model"]))
            save_results(args.output, args.models, records)
    save_results(args.output, args.models, records)
    print(f"Saved {len(records)} model-question results to {args.output}")


if __name__ == "__main__":
    main()
