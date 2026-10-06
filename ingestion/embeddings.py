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

import os
import time

import requests

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
EMBED_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_EMBED_TIMEOUT", "180"))
EMBED_RETRIES = int(os.getenv("OLLAMA_EMBED_RETRIES", "3"))


def get_embedding(text: str, model: str = DEFAULT_EMBED_MODEL) -> list:
    """Returns the embedding vector (list of floats) for a piece of text."""
    payload = {"model": model, "prompt": text}
    last_error = None
    for attempt in range(1, EMBED_RETRIES + 1):
        try:
            resp = requests.post(
                OLLAMA_EMBED_URL,
                json=payload,
                timeout=EMBED_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding", [])
            if not embedding:
                raise ValueError("Ollama returned an empty embedding")
            return embedding
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < EMBED_RETRIES:
                time.sleep(attempt)
    raise RuntimeError(
        f"Embedding failed after {EMBED_RETRIES} attempts: {last_error}"
    ) from last_error


def get_embeddings_batch(texts: list, model: str = DEFAULT_EMBED_MODEL) -> list:
    """Ollama's embed endpoint takes one input at a time — loop over the list."""
    return [get_embedding(t, model) for t in texts]


if __name__ == "__main__":
    vec = get_embedding("def login(username, password): ...")
    print(f"Embedding length: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")
