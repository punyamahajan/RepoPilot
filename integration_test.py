"""
integration_test.py
--------------------
Connects Person A's query_llm() directly to Person B's vectorstore —
no stubs, the real pipeline:

    Question -> Vector Similarity (B) -> Context -> Ollama (A) -> Response

This is essentially what Person C's retrieval.py does, but wired up
here as a standalone script so A and B can prove the two halves talk
to each other correctly *before* C even needs to touch it. Once this
runs clean, C's job on integration day is just pointing his imports
at these same two modules.

Run from the repo root:
    python integration_test.py
"""

import sys
import os

# Make both sibling folders importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ingestion"))

from ollama_client import query_llm          # Person A
from vectorstore import build_index, load_index  # Person B

INDEX_PATH = "data/index.json"
SAMPLE_REPO = "data/sample_repo"


def get_or_build_index():
    if os.path.exists(INDEX_PATH):
        print(f"Loading existing index from {INDEX_PATH}")
        return load_index(INDEX_PATH)
    print(f"No index found — building one from {SAMPLE_REPO}")
    return build_index(SAMPLE_REPO, save_path=INDEX_PATH)


def ask(question: str, vectorstore, model: str = "codellama"):
    context_chunks = vectorstore.similarity_search(question, k=3)
    context = "\n\n".join(context_chunks)

    print(f"\n{'=' * 60}")
    print(f"QUESTION: {question}")
    print(f"{'=' * 60}")
    print(f"\n--- Retrieved context ({len(context_chunks)} chunks) ---")
    for c in context_chunks:
        print(c[:150], "...\n")

    response = query_llm(question, context=context, model=model)
    print(f"--- Response ---\n{response}")
    return {"question": question, "context": context, "response": response}


if __name__ == "__main__":
    vs = get_or_build_index()

    test_questions = [
        "What does the login function do?",
        "How is the payment fee calculated?",
        "What fields does the User class have?",
    ]

    for q in test_questions:
        ask(q, vs)