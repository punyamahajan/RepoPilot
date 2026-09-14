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
    question = str(data.get("question", "")).strip()
    model = data.get("model", "all")
    if not question:
        return jsonify({"error": "question is required"}), 400

    if model != "all" and model not in MODELS:
        return jsonify({"error": f"unsupported model: {model}"}), 400

    try:
        retrieval = requests.post(f"{INGESTION_URL}/search", json={"query": question, "k": 3}, timeout=60)
        retrieval.raise_for_status()
        chunks = retrieval.json().get("chunks", [])
        context = "\n\n".join(chunks)
    except requests.RequestException as exc:
        return jsonify({"error": f"retrieval request failed: {exc}"}), 502

    target_models = MODELS if model == "all" else [model]

    def query_single_model(m):
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{LLM_URL}/ask",
                json={"prompt": question, "context": context, "use_retrieval": False, "model": m},
                timeout=600,
            )
            latency = round(time.perf_counter() - t0, 2)
            if resp.status_code == 200:
                result_json = resp.json()
                return {
                    "model": m,
                    "response": result_json.get("response", ""),
                    "latency_seconds": latency,
                    "status": "ok",
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
