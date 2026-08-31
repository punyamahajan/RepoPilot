"""
embeddings.py
-------------
Person B — Week 3, Exercise 2 (part 2): Embeddings

Calls Ollama's embedding endpoint so the whole pipeline (LLM +
embeddings) stays on one tool — matches the brief's "Ollama + Code
Llama + APIs" stack instead of pulling in OpenAI/HuggingFace for just
this piece.

Before using this, pull an embedding model once:
    ollama pull nomic-embed-text
"""

import requests

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
DEFAULT_EMBED_MODEL = "nomic-embed-text"


def get_embedding(text: str, model: str = DEFAULT_EMBED_MODEL) -> list:
    """Returns the embedding vector (list of floats) for a piece of text."""
    payload = {"model": model, "prompt": text}
    resp = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json().get("embedding", [])


def get_embeddings_batch(texts: list, model: str = DEFAULT_EMBED_MODEL) -> list:
    """Ollama's embed endpoint takes one input at a time — loop over the list."""
    return [get_embedding(t, model) for t in texts]


if __name__ == "__main__":
    vec = get_embedding("def login(username, password): ...")
    print(f"Embedding length: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")