"""Evaluate repository-level, multi-file questions through the current RAG services."""

import os
import sys
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from evaluation.metrics import correctness, hallucination_flag

INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:5001").rstrip("/")
LLM_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5000").rstrip("/")
MODEL = os.getenv("REPO_UNDERSTANDING_MODEL", "codellama")
HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = [
    {
        "question": "Which files are involved in user authentication and registration?",
        "files": {"auth.py", "models.py"},
        "keywords": ["auth.py", "models.py"],
    },
    {
        "question": "What happens after a user submits a registration request end-to-end?",
        "files": {"models.py", "auth.py"},
        "keywords": ["register_user", "bcrypt", "db.insert"],
    },
    {
        "question": "Which components would be affected if calculate_fee() changes?",
        "files": {"payment.py"},
        "keywords": ["process_payment", "calculate_fee", "log_transaction"],
    },
    {
        "question": "Trace user identity from registration through login to a payment.",
        "files": {"models.py", "auth.py", "payment.py"},
        "keywords": ["register_user", "login", "process_payment"],
    },
    {
        "question": "Which database tables are touched across authentication and payment?",
        "files": {"auth.py", "payment.py"},
        "keywords": ["users", "payments"],
    },
]


def source_files(chunks):
    return {c.split(" (chunk", 1)[0].replace("\\", "/").split("/")[-1] for c in chunks}


def main():
    rows = []
    for case in QUESTIONS:
        question = case["question"]
        needed = case["files"]
        answer_response = requests.post(
            f"{LLM_URL}/ask",
            json={"prompt": question, "use_retrieval": True, "k": 5, "model": MODEL},
            timeout=600,
        )
        answer_response.raise_for_status()
        payload = answer_response.json()
        chunks = payload.get("retrieved_chunks", [])
        found = source_files(chunks)
        answer = payload["response"]
        rows.append({
            "question": question,
            "needed": needed,
            "found": found,
            "chunks": chunks,
            "answer": answer,
            "file_coverage": len(needed & found) / len(needed),
            "answer_correctness": correctness(answer, case["keywords"]),
            "hallucinated": hallucination_flag(answer, "\n\n".join(chunks)),
            "status": payload.get("status", "answered"),
            "reason_code": payload.get("guardrail", {}).get("reason_code"),
        })
    lines = ["# Repository Understanding Evaluation", "", f"Model: `{MODEL}`; retrieval depth: 5 chunks.", ""]
    full = 0
    fully_correct = 0
    hallucinated = 0
    for i, row in enumerate(rows, 1):
        question = row["question"]
        needed = row["needed"]
        found = row["found"]
        answer = row["answer"]
        covered = needed <= found
        full += covered
        fully_correct += row["answer_correctness"] == 1.0
        hallucinated += row["hallucinated"]
        assessment = (
            "All expected source files were retrieved."
            if covered else f"Incomplete context: missing {', '.join(sorted(needed - found))}."
        )
        lines += [
            f"## {i}. {question}",
            "",
            f"**Expected files:** {', '.join(sorted(needed))}",
            "",
            f"**Retrieved files:** {', '.join(sorted(found)) or '(none)'}",
            "",
            f"**File coverage:** {row['file_coverage']:.1%}",
            "",
            f"**Answer correctness:** {row['answer_correctness']:.1%}",
            "",
            f"**Hallucination flag:** {'yes' if row['hallucinated'] else 'no'}",
            "",
            f"**Guardrail decision:** {row['status']} ({row['reason_code'] or 'passed'})",
            "",
            f"**Assessment:** {assessment}",
            "",
            "### Response",
            "",
            answer,
            "",
        ]
    mean_coverage = sum(row["file_coverage"] for row in rows) / len(rows)
    mean_correctness = sum(row["answer_correctness"] for row in rows) / len(rows)
    lines += [
        "## Overall assessment",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Questions with every expected file retrieved | {full}/{len(rows)} |",
        f"| Mean expected-file coverage | {mean_coverage:.1%} |",
        f"| Fully correct cross-file answers | {fully_correct}/{len(rows)} |",
        f"| Mean expected-keyword correctness | {mean_correctness:.1%} |",
        f"| Answers flagged for hallucination | {hallucinated}/{len(rows)} |",
        "",
        "The single vector store can answer small cross-file questions when independently similar chunks all fit in top-k, but it has no call graph, symbol relationships, dependency edges, or guaranteed coverage. Semantic top-k retrieval may omit a crucial but lexically dissimilar file and cannot prove end-to-end control flow. A code-intelligence graph/index, such as the Sourcegraph work planned for the following week, is the appropriate next step for reliable repository-wide reasoning.",
        "",
    ]
    path = os.path.join(HERE, "REPO_UNDERSTANDING.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
