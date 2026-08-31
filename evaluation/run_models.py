"""Run an identical question and context through each configured Ollama model."""

import os
import sys
import threading
import time

import psutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import ollama_client  # noqa: E402

MODELS = [m.strip() for m in os.getenv(
    "EVALUATION_MODELS", "codellama,starcoder2,qwen2.5-coder"
).split(",") if m.strip()]
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
ollama_client.OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"


def _sample_resources(stop, samples):
    process = psutil.Process()
    process.cpu_percent(None)
    while not stop.wait(0.1):
        samples.append((process.cpu_percent(None), process.memory_info().rss / 1024 / 1024))


def run_model(question: str, context: str, model: str) -> dict:
    """Call query_llm once and capture wall time, Ollama tokens, and client resources."""
    samples, stop = [], threading.Event()
    sampler = threading.Thread(target=_sample_resources, args=(stop, samples), daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        response = ollama_client.query_llm(question, context=context, model=model)
        error = None
    except Exception as exc:
        response, error = "", str(exc)
    finally:
        latency = time.perf_counter() - started
        stop.set()
        sampler.join(timeout=1)
    metadata = dict(ollama_client.LAST_RESPONSE_METADATA) if not error else {}
    return {
        "model": model, "response": response, "error": error,
        "latency_seconds": latency,
        "prompt_tokens": metadata.get("prompt_eval_count", 0),
        "completion_tokens": metadata.get("eval_count", 0),
        "total_tokens": metadata.get("prompt_eval_count", 0) + metadata.get("eval_count", 0),
        "cpu_percent_avg": sum(x[0] for x in samples) / len(samples) if samples else 0.0,
        "memory_mb_avg": sum(x[1] for x in samples) / len(samples) if samples else psutil.Process().memory_info().rss / 1024 / 1024,
    }


def run_models(question: str, context: str = "", models=None) -> list:
    """Run the same inputs sequentially; only the model name differs."""
    return [run_model(question, context, model) for model in (models or MODELS)]


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--context", default="")
    parser.add_argument("--models", nargs="+", default=MODELS)
    args = parser.parse_args()
    print(json.dumps(run_models(args.question, args.context, args.models), indent=2))
