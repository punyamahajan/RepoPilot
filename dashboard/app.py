"""RepoPilot results and live RAG demonstration dashboard."""

import concurrent.futures
import json
import os
import sys
import time

import markdown
import requests
from flask import Flask, jsonify, render_template, request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Put the project root before dashboard/ so `app.guardrails` resolves to the
# application package rather than this dashboard module when run as a script.
if ROOT in sys.path:
    sys.path.remove(ROOT)
sys.path.insert(0, ROOT)
from evaluation.analyze_results import (
    CATEGORY_LABELS,
    METRIC_LABELS,
    aggregate_by_category,
    aggregate_results,
    select_category_winners,
)

RESULTS_PATH = os.getenv("RESULTS_PATH", os.path.join(ROOT, "evaluation", "results.json"))
GUARDRAIL_RESULTS_PATH = os.getenv(
    "GUARDRAIL_RESULTS_PATH", os.path.join(ROOT, "evaluation", "guardrail_results.json")
)
OUTPUT_TEST_RESULTS_PATH = os.getenv(
    "OUTPUT_TEST_RESULTS_PATH", os.path.join(ROOT, "evaluation", "AI_OUTPUT_TEST_RESULTS.json")
)
INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:5001").rstrip("/")
LLM_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5000").rstrip("/")
MODELS = [x.strip() for x in os.getenv("EVALUATION_MODELS", "codellama,starcoder2,qwen2.5-coder").split(",") if x.strip()]
PRESET_QUESTION_IDS = [
    "explain-02",
    "retrieve-01",
    "dependency-02",
    "generate-02",
    "rag-03",
]
app = Flask(__name__)


def read_markdown(relative_path):
    path = os.path.join(ROOT, relative_path)
    if not os.path.exists(path):
        return "<p>Run the corresponding analysis script to generate this report.</p>"
    with open(path, encoding="utf-8") as handle:
        return markdown.markdown(handle.read(), extensions=["fenced_code", "tables"])


def evaluation_records():
    if not os.path.exists(RESULTS_PATH):
        return []
    with open(RESULTS_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("results", payload)


def model_rows(records=None):
    records = evaluation_records() if records is None else records
    aggregates = aggregate_results(records)
    return [{"model": model, **values} for model, values in aggregates.items()]


def category_summaries(records):
    aggregates = aggregate_by_category(records)
    winners = select_category_winners(aggregates)
    output = []
    for category, winner in winners.items():
        metric = winner["primary_metric"]
        value = winner["primary_value"]
        if value is None:
            score = "n/a"
        elif metric in {"accuracy", "retrieval_quality", "hallucination_rate", "test_pass_rate"}:
            score = f"{value:.1%}"
        elif metric == "latency_seconds":
            score = f"{value:.2f} s"
        else:
            score = f"{value:.3f}"
        output.append({
            "category": category,
            "label": CATEGORY_LABELS.get(category, category.title()),
            "model": winner["model"],
            "metric": METRIC_LABELS[metric],
            "score": score,
            "completion_rate": winner["completion_rate"],
        })
    return output


def preset_insight_data(records=None):
    """Build graph-ready data without changing the saved evaluation evidence."""
    records = evaluation_records() if records is None else records
    grouped = {}
    for row in records:
        grouped.setdefault(row.get("question_id"), []).append(row)

    questions = []
    for question_id in PRESET_QUESTION_IDS:
        rows = grouped.get(question_id, [])
        if not rows:
            continue
        ordered = sorted(
            rows,
            key=lambda row: MODELS.index(row.get("model"))
            if row.get("model") in MODELS
            else len(MODELS),
        )
        first = ordered[0]
        questions.append({
            "question_id": question_id,
            "question": first.get("question", ""),
            "category": first.get("category", ""),
            "category_label": CATEGORY_LABELS.get(
                first.get("category", ""), first.get("category", "").title()
            ),
            "models": [
                {
                    "model": row.get("model"),
                    "accuracy": row.get("accuracy"),
                    "relevance": row.get("relevance"),
                    "retrieval_quality": row.get("retrieval_quality"),
                    "grounding": 0.0 if row.get("hallucinated") else 1.0,
                    "test_passed": row.get("test_passed"),
                    "latency_seconds": row.get("latency_seconds"),
                    "total_tokens": row.get("total_tokens"),
                }
                for row in ordered
            ],
        })

    category_aggregates = aggregate_by_category(records)
    winners = select_category_winners(category_aggregates)
    category_graph = []
    for category, winner in winners.items():
        category_graph.append({
            "category": category,
            "label": CATEGORY_LABELS.get(category, category.title()),
            "model": winner.get("model"),
            "metric": METRIC_LABELS.get(
                winner.get("primary_metric"), winner.get("primary_metric", "")
            ),
            "score": winner.get("primary_value"),
        })

    return {
        "question_count": len(records) // len(MODELS) if MODELS else 0,
        "run_count": len(records),
        "models": MODELS,
        "overall": model_rows(records),
        "questions": questions,
        "category_winners": category_graph,
    }


def exercise5_data():
    """Load saved Exercise 5 results for a dashboard view without hiding evidence."""
    guardrail_rows = []
    if os.path.exists(GUARDRAIL_RESULTS_PATH):
        with open(GUARDRAIL_RESULTS_PATH, encoding="utf-8") as handle:
            guardrail_rows = json.load(handle).get("results", [])

    total = len(guardrail_rows)
    passed = sum(bool(row.get("passed")) for row in guardrail_rows)
    refused = [row for row in guardrail_rows if row.get("expected_decision") == "refused"]
    supported = [row for row in guardrail_rows if row.get("expected_decision") == "answered"]
    false_accepts = sum(row.get("guarded", {}).get("decision") == "answered" for row in refused)
    false_refusals = sum(row.get("guarded", {}).get("decision") != "answered" for row in supported)
    blocked_before_model = sum(
        not row.get("guarded", {}).get("llm_invoked", False) for row in refused
    )

    output_rows = output_test_rows()
    return {
        "guardrails": {
            "available": bool(guardrail_rows),
            "total": total,
            "passed": passed,
            "false_accepts": false_accepts,
            "refused_total": len(refused),
            "false_refusals": false_refusals,
            "supported_total": len(supported),
            "blocked_before_model": blocked_before_model,
            "rows": guardrail_rows,
        },
        "output_tests": {
            "total": len(output_rows),
            "passed": sum(bool(row["passed"]) for row in output_rows),
            "rows": output_rows,
        },
    }


def output_test_rows():
    """Read structured deterministic output-test results."""
    if not os.path.exists(OUTPUT_TEST_RESULTS_PATH):
        return []
    with open(OUTPUT_TEST_RESULTS_PATH, encoding="utf-8") as handle:
        rows = json.load(handle).get("results", [])
    return [{
        "id": row["id"],
        "condition": row["condition"],
        "expected": "accept" if row["expected"] else "reject",
        "actual": "accept" if row["actual"] else "reject",
        "reason": row.get("reason"),
        "passed": bool(row["passed"]),
    } for row in rows]


@app.get("/")
def index():
    records = evaluation_records()
    exercise5 = exercise5_data()
    return render_template(
        "index.html",
        rows=model_rows(records),
        models=MODELS,
        category_summaries=category_summaries(records),
        evaluation_analysis=read_markdown("evaluation/ANALYSIS.md"),
        pipeline_analysis=read_markdown("evaluation/RAG_PIPELINE_ANALYSIS.md"),
        repository_analysis=read_markdown("evaluation/REPO_UNDERSTANDING.md"),
        exercise5=exercise5,
        guardrail_analysis=read_markdown("evaluation/GUARDRAIL_ANALYSIS.md"),
        output_test_analysis=read_markdown("evaluation/AI_OUTPUT_TEST_REPORT.md"),
    )


@app.get("/insights")
def insights():
    return render_template(
        "insights.html",
        models=MODELS,
        insights=preset_insight_data(),
    )


@app.get("/health")
def health():
    try:
        response = requests.get(f"{INGESTION_URL}/health", timeout=5)
        response.raise_for_status()
        return jsonify({"status": "ok", "ingestion": response.json()})
    except Exception as exc:
        return jsonify({"status": "degraded", "error": str(exc)}), 503


@app.post("/api/ask")
def ask():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    model = data.get("model", "all")
    if not question:
        return jsonify({"error": "question is required"}), 400

    if model != "all" and model not in MODELS:
        return jsonify({"error": f"unsupported model: {model}"}), 400

    target_models = MODELS if model == "all" else [model]

    def query_single_model(m):
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{LLM_URL}/ask",
                json={
                    "prompt": question,
                    "use_retrieval": True,
                    "k": 3,
                    "model": m,
                    "include_metrics": True,
                },
                timeout=600,
            )
            latency = round(time.perf_counter() - t0, 2)
            if resp.status_code == 200:
                result_json = resp.json()
                return {
                    "model": m,
                    "response": result_json.get("response", ""),
                    "retrieved_chunks": result_json.get("retrieved_chunks", []),
                    "retrieval_matches": result_json.get("retrieval_matches", []),
                    "sources": result_json.get("sources", []),
                    "metrics": result_json.get("metrics", {}),
                    "guardrail": result_json.get("guardrail", {}),
                    "latency_seconds": latency,
                    "status": result_json.get("status", "answered"),
                    "error": None,
                }
            else:
                try:
                    err_msg = resp.json().get("error", resp.text)
                except Exception:
                    err_msg = resp.text
                return {
                    "model": m,
                    "response": f"Model error ({resp.status_code}): {err_msg}",
                    "latency_seconds": latency,
                    "status": "error",
                    "error": err_msg,
                }
        except Exception as exc:
            latency = round(time.perf_counter() - t0, 2)
            return {
                "model": m,
                "response": f"Request error: {exc}",
                "latency_seconds": latency,
                "status": "error",
                "error": str(exc),
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(target_models)) as executor:
        future_to_model = {executor.submit(query_single_model, m): m for m in target_models}
        model_results = {}
        for future in concurrent.futures.as_completed(future_to_model):
            res = future.result()
            model_results[res["model"]] = res

    results = [model_results[m] for m in target_models]
    chunks = next((row.get("retrieved_chunks", []) for row in results if row.get("retrieved_chunks")), [])

    payload = {
        "question": question,
        "retrieved_chunks": chunks,
        "results": results,
    }
    if model != "all" and results:
        payload["response"] = results[0]["response"]
        payload["model"] = results[0]["model"]
        payload["status"] = results[0]["status"]
        payload["latency_seconds"] = results[0]["latency_seconds"]
    elif results:
        payload["response"] = results[0]["response"]
        payload["model"] = results[0]["model"]

    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
