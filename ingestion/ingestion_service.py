"""HTTP service for building and querying the repository vector index."""

import os
import threading

from flask import Flask, jsonify, request

import embeddings
from vectorstore import build_index, load_index


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
INDEX_PATH = os.getenv("INDEX_PATH", "data/index.json")
embeddings.OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embeddings"

app = Flask(__name__)
_store = None
_store_lock = threading.Lock()


def _load_existing_index():
    global _store
    if _store is None and os.path.exists(INDEX_PATH):
        _store = load_index(INDEX_PATH)
    return _store


@app.get("/health")
def health():
    with _store_lock:
        store = _load_existing_index()
        return jsonify({
            "status": "ok",
            "index_ready": store is not None,
            "chunks": len(store.chunks) if store is not None else 0,
        })


@app.post("/build-index")
def build_index_endpoint():
    global _store
    data = request.get_json(silent=True) or {}
    repo_path = data.get("repo_path", "")
    if not isinstance(repo_path, str) or not repo_path.strip():
        return jsonify({"error": "repo_path is required"}), 400
    if not os.path.isdir(repo_path):
        return jsonify({"error": f"repo_path is not a directory: {repo_path}"}), 400

    try:
        with _store_lock:
            _store = build_index(repo_path, save_path=INDEX_PATH)
            chunk_count = len(_store.chunks)
        return jsonify({
            "status": "built",
            "repo_path": repo_path,
            "index_path": INDEX_PATH,
            "chunks": chunk_count,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/search")
def search():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    k = data.get("k", 3)
    if not isinstance(query, str) or not query.strip():
        return jsonify({"error": "query is required"}), 400
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        return jsonify({"error": "k must be a positive integer"}), 400

    try:
        with _store_lock:
            store = _load_existing_index()
            if store is None:
                return jsonify({
                    "error": "index is not ready; call POST /build-index first"
                }), 409
            chunks = store.similarity_search(query, k=k)
        return jsonify({"query": query, "k": k, "chunks": chunks})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
