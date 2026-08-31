"""
main.py
-------
The "Application + API" layer of the pipeline:

    User -> Application -> API -> Ollama -> Code Llama -> Response

Exposes a single POST /ask endpoint. Right now `context` is optional and
usually empty (that's Exercise 1 — no RAG yet). Once Person C's
retrieval module is ready, it'll call query_llm() the same way this
file does, just with a real `context` string instead of "".

Run:
    python main.py
Then in another terminal:
    curl -X POST http://localhost:5000/ask \
         -H "Content-Type: application/json" \
         -d '{"prompt": "What does a REST API do?"}'
"""

from flask import Flask, request, jsonify
from ollama_client import query_llm, list_available_models

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Quick check that the app is up and Ollama is reachable."""
    try:
        models = list_available_models()
        return jsonify({"status": "ok", "ollama_models": models})
    except Exception as e:
        return jsonify({"status": "ollama_unreachable", "error": str(e)}), 503


@app.route("/ask", methods=["POST"])
def ask():
    """
    Body:
        {
          "prompt": "required — the user's question",
          "context": "optional — retrieved context, empty for no-RAG mode",
          "model": "optional — defaults to codellama"
        }
    """
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    context = data.get("context", "")
    model = data.get("model", "codellama")

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    try:
        answer = query_llm(prompt, context=context, model=model)
        return jsonify({
            "prompt": prompt,
            "model": model,
            "used_rag": bool(context),
            "response": answer,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)