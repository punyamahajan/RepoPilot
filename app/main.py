"""RepoPilot LLM Service exposing health and question-answering APIs."""

import os

import requests
from flask import Flask, jsonify, request

import ollama_client
from ollama_client import query_llm


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "http://localhost:5001"
).rstrip("/")
ollama_client.OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"

app = Flask(__name__)


@app.get("/health")
def health():
    """Report whether the service can reach Ollama."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        return jsonify({"status": "ok", "ollama_models": models})
    except Exception as exc:
        return jsonify({"status": "ollama_unreachable", "error": str(exc)}), 503


@app.post("/ask")
def ask():
    """Answer a prompt using supplied context or context fetched over HTTP."""
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    context_was_provided = "context" in data
    context = data.get("context", "")
    model = data.get("model", "codellama")
    use_retrieval = data.get("use_retrieval", not context_was_provided)

    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "prompt is required"}), 400
    prompt = prompt.strip()
    if not isinstance(context, str):
        return jsonify({"error": "context must be a string"}), 400
    if not isinstance(use_retrieval, bool):
        return jsonify({"error": "use_retrieval must be a boolean"}), 400

    try:
        retrieved_chunks = []
        if use_retrieval:
            k = data.get("k", 3)
            if not isinstance(k, int) or isinstance(k, bool) or k < 1:
                return jsonify({"error": "k must be a positive integer"}), 400
            retrieval_response = requests.post(
                f"{INGESTION_SERVICE_URL}/search",
                json={"query": prompt, "k": k},
                timeout=60,
            )
            retrieval_response.raise_for_status()
            retrieved_chunks = retrieval_response.json().get("chunks", [])
            context = "\n\n".join(retrieved_chunks)

        answer = query_llm(prompt, context=context, model=model)
        return jsonify({
            "prompt": prompt,
            "model": model,
            "used_rag": bool(context),
            "retrieved_chunks": retrieved_chunks,
            "response": answer,
        })
    except requests.RequestException as exc:
        return jsonify({"error": f"upstream service request failed: {exc}"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
