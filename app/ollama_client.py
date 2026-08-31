"""
ollama_client.py
-----------------
Thin wrapper around Ollama's local REST API. This is Person A's core
deliverable for Week 3, Exercise 1:

    User -> Application -> API -> Ollama -> Code Llama -> Response

Person C (retrieval/RAG) will call `query_llm(prompt, context)` and pass
in whatever context they pull from the vectorstore — so don't change
this function's signature without telling C.
"""

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "codellama"


def query_llm(prompt: str, context: str = "", model: str = DEFAULT_MODEL, timeout: int = 120) -> str:
    """
    Send a prompt (optionally with retrieved context) to a model served
    by Ollama and return the plain-text response.

    Args:
        prompt: the user's question.
        context: retrieved context to prepend (empty string = no-RAG mode,
                 useful for the "RAG vs no-RAG" comparison in Exercise 3).
        model: any model already pulled locally via `ollama pull <model>`.
               Used as-is in Week 4 Exercise 1 when swapping models
               (codellama, starcoder2, deepseek-coder, etc.).
        timeout: seconds to wait before giving up (Code Llama can be slow
                 on CPU-only machines — raise this if you see timeouts).

    Returns:
        The model's generated text.
    """
    if context:
        full_prompt = (
            f"Use the following context to answer the question. "
            f"If the context does not contain the answer, say so rather "
            f"than guessing.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{prompt}"
        )
    else:
        full_prompt = prompt

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def list_available_models() -> list:
    """
    Returns the models currently pulled and available in the local
    Ollama installation. Useful for Week 4 Exercise 1 (multi-model
    evaluation) to confirm codellama / starcoder2 / etc. are ready
    before running the comparison.
    """
    resp = requests.get("http://localhost:11434/api/tags", timeout=10)
    resp.raise_for_status()
    models = resp.json().get("models", [])
    return [m["name"] for m in models]


if __name__ == "__main__":
    # Quick manual sanity check: `python ollama_client.py`
    print("Available models:", list_available_models())
    test_response = query_llm("What is a REST API, in one sentence?")
    print("\nTest response:\n", test_response)