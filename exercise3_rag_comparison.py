"""
exercise3_rag_comparison.py
----------------------------
Week 3, Exercise 3 deliverable:

    Question -> Query Embedding -> Vector Similarity -> Context
    Context + Question -> Ollama -> Code Llama -> Response

The brief specifically asks you to "demonstrate how the response
differs when relevant information is provided through RAG compared
with asking the LLM without retrieval." This script runs BOTH modes
for the same set of questions, using the real vectorstore (Person B)
and the real Ollama call (Person A) — no stubs — and saves a report
you can drop straight into your submission.

Run from the repo root:
    python exercise3_rag_comparison.py

Output:
    reports/exercise3_rag_vs_no_rag.md
"""

import sys
import os
from datetime import datetime

# Make app/ and ingestion/ importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ingestion"))

from ollama_client import query_llm            # Person A
from vectorstore import build_index, load_index  # Person B

INDEX_PATH = "data/index.json"
SAMPLE_REPO = "data/sample_repo"
REPORT_PATH = "reports/exercise3_rag_vs_no_rag.md"

# Swap these for questions about your real target repo once you've picked one.
TEST_QUESTIONS = [
    "What does the login function do?",
    "How is the payment fee calculated?",
    "What fields does the User class have?",
    "Which function verifies a password?",
    "How does the system log a transaction?",
]


def get_or_build_index():
    if os.path.exists(INDEX_PATH):
        print(f"Loading existing index from {INDEX_PATH}")
        return load_index(INDEX_PATH)
    print(f"No index found — building one from {SAMPLE_REPO}")
    return build_index(SAMPLE_REPO, save_path=INDEX_PATH)


def compare_rag_vs_no_rag(question: str, vectorstore, model: str = "codellama") -> dict:
    """Runs the same question WITH retrieved context and WITHOUT any context."""
    context_chunks = vectorstore.similarity_search(question, k=3)
    context = "\n\n".join(context_chunks)

    rag_response = query_llm(question, context=context, model=model)
    no_rag_response = query_llm(question, context="", model=model)

    return {
        "question": question,
        "context_chunks": context_chunks,
        "context": context,
        "rag_response": rag_response,
        "no_rag_response": no_rag_response,
    }


def write_report(results: list, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Exercise 3 — RAG vs No-RAG Comparison\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(
            "Each question below was sent to the same model (`codellama` via "
            "Ollama) twice: once with context retrieved from the vectorstore "
            "(RAG), and once with no context at all (baseline). Compare the "
            "two responses to see where retrieval improves accuracy and "
            "specificity.\n\n---\n\n"
        )
        for i, r in enumerate(results, 1):
            f.write(f"## Question {i}: {r['question']}\n\n")
            f.write("### Retrieved context (RAG)\n\n```\n")
            f.write(r["context"] if r["context"] else "(no context retrieved)")
            f.write("\n```\n\n")
            f.write("### Response WITH RAG\n\n")
            f.write(r["rag_response"] + "\n\n")
            f.write("### Response WITHOUT RAG (baseline)\n\n")
            f.write(r["no_rag_response"] + "\n\n")
            f.write("### Notes (fill in manually)\n\n")
            f.write(
                "- Was the retrieved context actually relevant? \n"
                "- Did RAG produce a more specific / correct answer? \n"
                "- Did the no-RAG response hallucinate details? \n\n---\n\n"
            )
    print(f"\nReport saved to {path}")


if __name__ == "__main__":
    vs = get_or_build_index()

    all_results = []
    for q in TEST_QUESTIONS:
        print(f"\n{'=' * 60}\nQUESTION: {q}\n{'=' * 60}")
        result = compare_rag_vs_no_rag(q, vs)
        all_results.append(result)

        print("\n--- WITH RAG ---")
        print(result["rag_response"])
        print("\n--- WITHOUT RAG ---")
        print(result["no_rag_response"])

    write_report(all_results, REPORT_PATH)