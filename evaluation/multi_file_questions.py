"""Evaluate repository-level, multi-file questions through the current RAG services."""

import os
import requests

INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:5001").rstrip("/")
LLM_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5000").rstrip("/")
MODEL = os.getenv("REPO_UNDERSTANDING_MODEL", "codellama")
HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = [
    ("Which files are involved in user authentication and registration?", {"auth.py", "models.py"}),
    ("What happens after a user submits a registration request end-to-end?", {"models.py", "auth.py"}),
    ("Which components would be affected if calculate_fee() changes?", {"payment.py"}),
    ("Trace user identity from registration through login to a payment.", {"models.py", "auth.py", "payment.py"}),
    ("Which database tables are touched across authentication and payment?", {"auth.py", "payment.py"}),
]


def source_files(chunks):
    return {c.split(" (chunk", 1)[0].replace("\\", "/").split("/")[-1] for c in chunks}


def main():
    rows = []
    for question, needed in QUESTIONS:
        found_response = requests.post(f"{INGESTION_URL}/search", json={"query": question, "k": 5}, timeout=90)
        found_response.raise_for_status()
        chunks = found_response.json().get("chunks", [])
        found = source_files(chunks)
        answer_response = requests.post(f"{LLM_URL}/ask", json={"prompt": question, "context": "\n\n".join(chunks), "use_retrieval": False, "model": MODEL}, timeout=180)
        answer_response.raise_for_status()
        rows.append((question, needed, found, chunks, answer_response.json()["response"]))
    lines = ["# Repository Understanding Evaluation", "", f"Model: `{MODEL}`; retrieval depth: 5 chunks.", ""]
    full = 0
    for i, (question, needed, found, chunks, answer) in enumerate(rows, 1):
        covered = needed <= found
        full += covered
        assessment = "All expected source files were retrieved." if covered else f"Incomplete context: missing {', '.join(sorted(needed - found))}."
        lines += [f"## {i}. {question}", "", f"**Expected files:** {', '.join(sorted(needed))}", "", f"**Retrieved files:** {', '.join(sorted(found)) or '(none)'}", "", f"**Assessment:** {assessment}", "", "### Response", "", answer, ""]
    lines += ["## Overall assessment", "", f"The single vector store retrieved every expected file for {full}/{len(rows)} multi-file questions. It can answer small cross-file questions when independently similar chunks all fit in top-k, but it has no call graph, symbol relationships, dependency edges, or guaranteed coverage. Semantic top-k retrieval may omit a crucial but lexically dissimilar file and cannot prove end-to-end control flow. A code-intelligence graph/index (the planned Sourcegraph work) is the appropriate next step for reliable repository-wide reasoning.", ""]
    path = os.path.join(HERE, "REPO_UNDERSTANDING.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
