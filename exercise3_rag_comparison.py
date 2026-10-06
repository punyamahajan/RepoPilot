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
from evaluation.metrics import correctness, hallucination_flag, retrieval_quality

INDEX_PATH = "data/index.json"
SAMPLE_REPO = "data/sample_repo"
REPORT_PATH = "reports/exercise3_rag_vs_no_rag.md"

# The expected file and keywords make the written comparison repeatable instead
# of leaving the final analysis as a manual fill-in exercise.
TEST_CASES = [
    {
        "question": "What does the login function do?",
        "expected_keywords": ["find_user", "verify_password", "session token"],
        "expected_file": "auth.py",
    },
    {
        "question": "How is the payment fee calculated?",
        "expected_keywords": ["0.03", "round"],
        "expected_file": "payment.py",
    },
    {
        "question": "What fields does the User class have?",
        "expected_keywords": ["id", "username", "password_hash", "created_at"],
        "expected_file": "models.py",
    },
    {
        "question": "Which function verifies a password?",
        "expected_keywords": ["verify_password", "bcrypt.checkpw"],
        "expected_file": "auth.py",
    },
    {
        "question": "How does the system log a transaction?",
        "expected_keywords": ["log_transaction", "db.insert", "payments"],
        "expected_file": "payment.py",
    },
]


def get_or_build_index():
    if os.path.exists(INDEX_PATH):
        print(f"Loading existing index from {INDEX_PATH}")
        return load_index(INDEX_PATH)
    print(f"No index found — building one from {SAMPLE_REPO}")
    return build_index(SAMPLE_REPO, save_path=INDEX_PATH)


def compare_rag_vs_no_rag(case: dict, vectorstore, model: str = "codellama") -> dict:
    """Runs the same question WITH retrieved context and WITHOUT any context."""
    question = case["question"]
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
        "retrieval_quality": retrieval_quality(context_chunks, case["expected_file"]),
        "rag_accuracy": correctness(rag_response, case["expected_keywords"]),
        "no_rag_accuracy": correctness(no_rag_response, case["expected_keywords"]),
        "rag_hallucinated": hallucination_flag(rag_response, context),
        "no_rag_ungrounded": hallucination_flag(no_rag_response, ""),
    }


def write_report(results: list, path: str):
    rag_mean = sum(row["rag_accuracy"] for row in results) / len(results)
    baseline_mean = sum(row["no_rag_accuracy"] for row in results) / len(results)
    improved = sum(row["rag_accuracy"] > row["no_rag_accuracy"] for row in results)
    equal = sum(row["rag_accuracy"] == row["no_rag_accuracy"] for row in results)
    worse = len(results) - improved - equal
    relevant = sum(bool(row["retrieval_quality"]) for row in results)
    rag_hallucinations = sum(row["rag_hallucinated"] for row in results)
    baseline_ungrounded = sum(row["no_rag_ungrounded"] for row in results)

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
        f.write("## Quantitative summary\n\n")
        f.write("| Measure | RAG | No-RAG baseline |\n|---|---:|---:|\n")
        f.write(f"| Mean expected-keyword accuracy | {rag_mean:.1%} | {baseline_mean:.1%} |\n")
        f.write(f"| Relevant top retrieval / questions | {relevant}/{len(results)} | n/a |\n")
        f.write(f"| Contextual hallucination / ungrounded-claim flags | {rag_hallucinations}/{len(results)} | {baseline_ungrounded}/{len(results)} |\n\n")
        f.write(
            f"RAG improved expected-keyword coverage for **{improved}/{len(results)}** questions, "
            f"matched the baseline for **{equal}/{len(results)}**, and was worse for "
            f"**{worse}/{len(results)}**. This evidence separates retrieval quality from "
            "answer quality: relevant context can improve grounding, but it does not "
            "guarantee that the model will use every relevant fact.\n\n"
        )
        f.write("## Per-question evidence\n\n")
        for i, r in enumerate(results, 1):
            f.write(f"## Question {i}: {r['question']}\n\n")
            f.write(
                f"- Top retrieval came from the expected file: **{'yes' if r['retrieval_quality'] else 'no'}**\n"
                f"- RAG accuracy: **{r['rag_accuracy']:.1%}**\n"
                f"- No-RAG accuracy: **{r['no_rag_accuracy']:.1%}**\n"
                f"- RAG contextual hallucination flag: **{'yes' if r['rag_hallucinated'] else 'no'}**\n"
                f"- No-RAG ungrounded-claim flag: **{'yes' if r['no_rag_ungrounded'] else 'no'}**\n\n"
            )
            f.write("### Retrieved context (RAG)\n\n```\n")
            f.write(r["context"] if r["context"] else "(no context retrieved)")
            f.write("\n```\n\n")
            f.write("### Response WITH RAG\n\n")
            f.write(r["rag_response"] + "\n\n")
            f.write("### Response WITHOUT RAG (baseline)\n\n")
            f.write(r["no_rag_response"] + "\n\n")
            delta = r["rag_accuracy"] - r["no_rag_accuracy"]
            comparison = "improved" if delta > 0 else "matched" if delta == 0 else "reduced"
            f.write("### Evidence-based interpretation\n\n")
            f.write(
                f"The retrieved top chunk was {'relevant' if r['retrieval_quality'] else 'not from the expected file'}. "
                f"Adding it {comparison} expected-keyword coverage by {abs(delta):.1%}. "
                f"The grounded response {'did' if r['rag_hallucinated'] else 'did not'} trigger the contextual hallucination heuristic, "
                f"while the baseline {'contained' if r['no_rag_ungrounded'] else 'did not contain'} identifiable code claims that could not be verified without supplied context.\n\n---\n\n"
            )
        f.write("## Conclusion\n\n")
        f.write(
            f"Across this controlled comparison, RAG achieved {rag_mean:.1%} mean keyword accuracy versus "
            f"{baseline_mean:.1%} without retrieval. The top result came from the expected file for "
            f"{relevant}/{len(results)} questions. These results show the complete relationship: "
            "retrieval determines available context, context constrains the model, and the model can still omit facts or make unsupported claims. RAG therefore improves the evidence available to the LLM but is not, by itself, a guarantee of correctness.\n"
        )
    print(f"\nReport saved to {path}")


if __name__ == "__main__":
    vs = get_or_build_index()

    all_results = []
    for case in TEST_CASES:
        print(f"\n{'=' * 60}\nQUESTION: {case['question']}\n{'=' * 60}")
        result = compare_rag_vs_no_rag(case, vs)
        all_results.append(result)

        print("\n--- WITH RAG ---")
        print(result["rag_response"])
        print("\n--- WITHOUT RAG ---")
        print(result["no_rag_response"])

    write_report(all_results, REPORT_PATH)
