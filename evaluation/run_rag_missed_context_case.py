"""Create a controlled top-k failure showing important repository context being missed."""

import json
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.ollama_client import query_llm

INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:5001").rstrip("/")
MODEL = os.getenv("RAG_ANALYSIS_MODEL", "codellama")
QUESTION = "Which files and functions are involved in user authentication and registration?"
EXPECTED_FILES = {"auth.py", "models.py"}
OUTPUT = os.path.join(os.path.dirname(__file__), "RAG_MISSED_CONTEXT_CASE.json")


def source_file(chunk):
    return chunk.split(" (chunk", 1)[0].replace("\\", "/").split("/")[-1]


def main():
    response = requests.post(
        f"{INGESTION_URL}/search",
        json={"query": QUESTION, "k": 1},
        timeout=240,
    )
    response.raise_for_status()
    chunks = response.json().get("chunks", [])
    retrieved_files = {source_file(chunk) for chunk in chunks}
    answer = query_llm(QUESTION, context="\n\n".join(chunks), model=MODEL, timeout=600)
    result = {
        "question": QUESTION,
        "model": MODEL,
        "k": 1,
        "expected_files": sorted(EXPECTED_FILES),
        "retrieved_files": sorted(retrieved_files),
        "missing_files": sorted(EXPECTED_FILES - retrieved_files),
        "retrieved_chunks": chunks,
        "response": answer,
    }
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"Wrote {OUTPUT}; missed: {', '.join(result['missing_files']) or 'none'}")
    return 0 if result["missing_files"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
