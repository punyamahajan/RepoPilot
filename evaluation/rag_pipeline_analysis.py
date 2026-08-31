"""Trace retrieval and response quality for a representative RAG subset."""

import json
import os
import requests

INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:5001").rstrip("/")
LLM_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5000").rstrip("/")
MODEL = os.getenv("RAG_ANALYSIS_MODEL", "codellama")
HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = [
    ("What does the login function do?", "auth.py", ["find_user", "verify_password"]),
    ("How is the payment fee calculated?", "payment.py", ["0.03", "round"]),
    ("What fields does the User class have?", "models.py", ["username", "password_hash"]),
    ("Which function verifies a password?", "auth.py", ["verify_password"]),
    ("How does the system log a transaction?", "payment.py", ["db.insert", "payments"]),
    ("What happens when Stripe rejects a charge?", "payment.py", ["not", "handled"]),
    ("Does session token creation set an expiry?", "auth.py", ["no", "expiry"]),
]


def classify(chunks, expected_file, response, keywords):
    if not chunks:
        return "missing-info-not-retrieved"
    top_source = chunks[0].split(" (chunk", 1)[0].replace("\\", "/")
    relevant = top_source.endswith(expected_file)
    correct = any(k.lower() in response.lower() for k in keywords)
    if not relevant:
        return "irrelevant-context-retrieved"
    return "relevant-context-correct-answer" if correct else "relevant-context-hallucinated-anyway"


def main():
    rows = []
    for question, expected_file, keywords in QUESTIONS:
        retrieval = requests.post(f"{INGESTION_URL}/search", json={"query": question, "k": 3}, timeout=90)
        retrieval.raise_for_status()
        chunks = retrieval.json().get("chunks", [])
        llm = requests.post(f"{LLM_URL}/ask", json={"prompt": question, "context": "\n\n".join(chunks), "use_retrieval": False, "model": MODEL}, timeout=180)
        llm.raise_for_status()
        response = llm.json()["response"]
        rows.append((question, chunks, response, classify(chunks, expected_file, response, keywords)))
    counts = {label: sum(r[3] == label for r in rows) for label in ["relevant-context-correct-answer", "relevant-context-hallucinated-anyway", "irrelevant-context-retrieved", "missing-info-not-retrieved"]}
    lines = ["# RAG Pipeline Analysis", "", f"Model: `{MODEL}`", ""]
    for i, (question, chunks, response, label) in enumerate(rows, 1):
        lines += [f"## {i}. {question}", "", f"**Classification:** `{label}`", "", "### Retrieved Context", "", "```", "\n\n".join(chunks) or "(none)", "```", "", "### LLM Response", "", response, ""]
    lines += ["## Conclusion", "", f"Relevant context produced correct answers in {counts['relevant-context-correct-answer']} of {len(rows)} traces; {counts['relevant-context-hallucinated-anyway']} hallucinated despite relevant context, {counts['irrelevant-context-retrieved']} retrieved irrelevant top context, and {counts['missing-info-not-retrieved']} had no retrieved information. These traces show that response quality depends on both retrieval relevance and whether the requested fact actually exists in the indexed repository.", ""]
    path = os.path.join(HERE, "RAG_PIPELINE_ANALYSIS.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
