"""RepoPilot results and live RAG demonstration dashboard."""

import json
import os
import sys

import markdown
import requests
from flask import Flask, jsonify, render_template, request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from evaluation.analyze_results import aggregate_results

RESULTS_PATH = os.getenv("RESULTS_PATH", os.path.join(ROOT, "evaluation", "results.json"))
INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:5001").rstrip("/")
LLM_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5000").rstrip("/")
MODELS = [x.strip() for x in os.getenv("EVALUATION_MODELS", "codellama,starcoder2,qwen2.5-coder").split(",") if x.strip()]
app = Flask(__name__)


def read_markdown(relative_path):
    path = os.path.join(ROOT, relative_path)
    if not os.path.exists(path):
        return "<p>Run the corresponding analysis script to generate this report.</p>"
    with open(path, encoding="utf-8") as handle:
        return markdown.markdown(handle.read(), extensions=["fenced_code", "tables"])


def model_rows():
    if not os.path.exists(RESULTS_PATH):
        return []
    with open(RESULTS_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)
    aggregates = aggregate_results(payload.get("results", payload))
    return [{"model": model, **values} for model, values in aggregates.items()]


@app.get("/")
def index():
    return render_template("index.html", rows=model_rows(), models=MODELS,
                           rag_comparison=read_markdown("reports/exercise3_rag_vs_no_rag.md"),
                           pipeline_analysis=read_markdown("evaluation/RAG_PIPELINE_ANALYSIS.md"))


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
    question, model = str(data.get("question", "")).strip(), data.get("model", MODELS[0])
    if not question:
        return jsonify({"error": "question is required"}), 400
    if model not in MODELS:
        return jsonify({"error": "unsupported model"}), 400
    try:
        retrieval = requests.post(f"{INGESTION_URL}/search", json={"query": question, "k": 3}, timeout=60)
        retrieval.raise_for_status()
        chunks = retrieval.json().get("chunks", [])
        response = requests.post(f"{LLM_URL}/ask", json={"prompt": question, "context": "\n\n".join(chunks), "use_retrieval": False, "model": model}, timeout=240)
        response.raise_for_status()
        result = response.json()
        result["retrieved_chunks"] = chunks
        return jsonify(result)
    except requests.RequestException as exc:
        return jsonify({"error": f"pipeline request failed: {exc}"}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
