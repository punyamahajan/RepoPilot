"""RepoPilot LLM Service exposing health and question-answering APIs."""

import os
import re

import requests
from flask import Flask, jsonify, request

try:
    from . import ollama_client
    from .guardrails import (
        MAX_RETRIEVAL_K,
        REFUSALS,
        GuardrailDecision,
        validate_input,
        validate_output,
        validate_retrieval,
    )
    from .ollama_client import query_llm, query_llm_with_metrics
except ImportError:  # Direct execution: python app/main.py
    import ollama_client
    from guardrails import (
        MAX_RETRIEVAL_K,
        REFUSALS,
        GuardrailDecision,
        validate_input,
        validate_output,
        validate_retrieval,
    )
    from ollama_client import query_llm, query_llm_with_metrics


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "http://localhost:5001"
).rstrip("/")
ollama_client.OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
ALLOWED_MODELS = {
    value.strip()
    for value in os.getenv(
        "ALLOWED_MODELS", "codellama,starcoder2,qwen2.5-coder"
    ).split(",")
    if value.strip()
}
app = Flask(__name__)


def refusal_response(prompt, model, decision, status_code=200, **metadata):
    metrics = metadata.pop("metrics", {})
    payload = {
        "status": "refused",
        "prompt": prompt if isinstance(prompt, str) else "",
        "model": model,
        "used_rag": metadata.pop("used_rag", False),
        "retrieved_chunks": metadata.pop("retrieved_chunks", []),
        "retrieval_matches": metadata.pop("retrieval_matches", []),
        "sources": metadata.pop("sources", []),
        "response": decision.message or REFUSALS[decision.reason_code],
        "metrics": metrics,
        "guardrail": decision.as_dict(llm_invoked=metadata.pop("llm_invoked", False), **metadata),
    }
    return jsonify(payload), status_code


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
    """Apply guardrails, retrieve trusted context, generate, then validate output."""
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    context_was_provided = "context" in data
    model = data.get("model", "codellama")
    use_retrieval = data.get("use_retrieval", True)
    include_metrics = data.get("include_metrics", False)

    input_decision = validate_input(prompt)
    if not input_decision.allowed:
        code = 400 if input_decision.reason_code == "INVALID_INPUT" else 413 if input_decision.reason_code == "INPUT_TOO_LONG" else 200
        return refusal_response(prompt, model, input_decision, code)
    prompt = prompt.strip()
    if not isinstance(use_retrieval, bool):
        return jsonify({"error": "use_retrieval must be a boolean"}), 400
    if not isinstance(include_metrics, bool):
        return jsonify({"error": "include_metrics must be a boolean"}), 400
    if not isinstance(model, str) or model not in ALLOWED_MODELS:
        decision = GuardrailDecision(False, "input", "UNSUPPORTED_MODEL", REFUSALS["UNSUPPORTED_MODEL"], ["model_allowlist"])
        return refusal_response(prompt, str(model), decision, 400)
    if context_was_provided:
        decision = GuardrailDecision(False, "input", "UNTRUSTED_CONTEXT", REFUSALS["UNTRUSTED_CONTEXT"], ["trusted_retrieval_only"])
        return refusal_response(prompt, model, decision, 400)
    if not use_retrieval:
        decision = GuardrailDecision(False, "input", "UNTRUSTED_CONTEXT", REFUSALS["UNTRUSTED_CONTEXT"], ["retrieval_required"])
        return refusal_response(prompt, model, decision, 400)

    try:
        k = data.get("k", 3)
        if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= MAX_RETRIEVAL_K:
            return jsonify({"error": f"k must be an integer from 1 to {MAX_RETRIEVAL_K}"}), 400
        retrieval_response = requests.post(
            f"{INGESTION_SERVICE_URL}/search",
            json={"query": prompt, "k": k},
            timeout=240,
        )
        retrieval_response.raise_for_status()
        retrieval_payload = retrieval_response.json()
        matches = retrieval_payload.get("matches", [])
        retrieved_chunks = retrieval_payload.get("chunks", [])
        retrieval_decision = validate_retrieval(prompt, matches)
        sources = list(dict.fromkeys(match.get("file", "") for match in matches if match.get("file")))
        if not retrieval_decision.allowed:
            return refusal_response(
                prompt,
                model,
                retrieval_decision,
                retrieved_chunks=retrieved_chunks,
                retrieval_matches=matches,
                sources=sources,
                top_score=retrieval_payload.get("top_score"),
            )
        context = "\n\n".join(retrieved_chunks)

        metrics = {}

        def generate(generation_prompt):
            if include_metrics:
                model_result = query_llm_with_metrics(
                    generation_prompt, context=context, model=model, timeout=600
                )
                generated = model_result.pop("response")
                return generated, model_result
            return query_llm(generation_prompt, context=context, model=model, timeout=600), {}

        answer, metrics = generate(prompt)
        output_decision = validate_output(prompt, answer, context)
        output_retry = False
        output_sanitized = False

        def sanitize_code_only(candidate_answer, candidate_decision):
            if candidate_decision.allowed or not re.search(
                r"\b(?:write|generate|create|unit\s+test)\b", prompt, re.IGNORECASE
            ):
                return candidate_answer, candidate_decision, False
            code_block = re.search(
                r"```(?:[A-Za-z0-9_+.-]+)?[ \t]*\r?\n?.*?```",
                candidate_answer,
                re.DOTALL,
            )
            if not code_block:
                return candidate_answer, candidate_decision, False
            sanitized_answer = code_block.group(0).strip()
            sanitized_decision = validate_output(prompt, sanitized_answer, context)
            if not sanitized_decision.allowed:
                return candidate_answer, candidate_decision, False
            return sanitized_answer, sanitized_decision, True

        answer, output_decision, output_sanitized = sanitize_code_only(
            answer, output_decision
        )
        if not output_decision.allowed:
            output_retry = True
            retry_prompt = (
                f"{prompt}\n\n"
                "Correct the previous attempt. For a factual question, return exactly one sentence "
                "using only facts and relationships explicitly shown in the repository evidence. "
                "For a code-generation request, return one complete balanced Markdown code block "
                "and no prose. Do not invent files, existing functions, call edges, security flows, "
                "or cross-component behavior."
            )
            answer, retry_metrics = generate(retry_prompt)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens", "total_duration_ns"):
                metrics[key] = int(metrics.get(key, 0) or 0) + int(retry_metrics.get(key, 0) or 0)
            output_decision = validate_output(prompt, answer, context)
            answer, output_decision, retry_sanitized = sanitize_code_only(
                answer, output_decision
            )
            output_sanitized = output_sanitized or retry_sanitized
        if not output_decision.allowed:
            return refusal_response(
                prompt,
                model,
                output_decision,
                retrieved_chunks=retrieved_chunks,
                retrieval_matches=matches,
                sources=sources,
                llm_invoked=True,
                used_rag=True,
                output_retry=output_retry,
                output_sanitized=output_sanitized,
                top_score=retrieval_payload.get("top_score"),
                metrics=metrics,
            )
        return jsonify({
            "status": "answered",
            "prompt": prompt,
            "model": model,
            "used_rag": True,
            "retrieved_chunks": retrieved_chunks,
            "retrieval_matches": matches,
            "sources": sources,
            "response": answer,
            "metrics": metrics,
            "guardrail": output_decision.as_dict(
                llm_invoked=True,
                top_score=retrieval_payload.get("top_score"),
                input_checks=input_decision.checks,
                retrieval_checks=retrieval_decision.checks,
                output_retry=output_retry,
                output_sanitized=output_sanitized,
            ),
        })
    except requests.RequestException as exc:
        return jsonify({"error": f"upstream service request failed: {exc}"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
