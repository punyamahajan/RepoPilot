"""Run an identical question and context through each configured Ollama model."""

import os
import shutil
import subprocess
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
NVIDIA_SMI = shutil.which("nvidia-smi")


def _sample_resources(stop, samples):
    """Sample the evaluator, Ollama processes, and NVIDIA GPU during one request."""
    client = psutil.Process()
    client.cpu_percent(None)
    ollama_processes = {}
    last_gpu = (0.0, 0.0)
    tick = 0

    while not stop.wait(0.2):
        if tick % 5 == 0:
            for process in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    label = " ".join([
                        process.info.get("name") or "",
                        *[str(x) for x in (process.info.get("cmdline") or [])],
                    ]).lower()
                    if "ollama" in label and process.pid not in ollama_processes:
                        process.cpu_percent(None)
                        ollama_processes[process.pid] = process
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
            last_gpu = _gpu_sample()

        ollama_cpu = 0.0
        ollama_memory = 0.0
        for pid, process in list(ollama_processes.items()):
            try:
                ollama_cpu += process.cpu_percent(None)
                ollama_memory += process.memory_info().rss / 1024 / 1024
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                ollama_processes.pop(pid, None)

        samples.append({
            "client_cpu": client.cpu_percent(None),
            "client_memory": client.memory_info().rss / 1024 / 1024,
            "ollama_cpu": ollama_cpu,
            "ollama_memory": ollama_memory,
            "gpu_utilization": last_gpu[0],
            "gpu_memory": last_gpu[1],
        })
        tick += 1


def _gpu_sample():
    """Return average GPU utilization and total allocated VRAM in MiB."""
    if not NVIDIA_SMI:
        return 0.0, 0.0
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        result = subprocess.run(
            [
                NVIDIA_SMI,
                "--query-gpu=utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
            creationflags=creation_flags,
        )
        rows = []
        for line in result.stdout.splitlines():
            values = [part.strip() for part in line.split(",")]
            if len(values) == 2:
                rows.append((float(values[0]), float(values[1])))
        if not rows:
            return 0.0, 0.0
        return sum(row[0] for row in rows) / len(rows), sum(row[1] for row in rows)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0, 0.0


def _sample_mean(samples, key, fallback=0.0):
    return sum(sample[key] for sample in samples) / len(samples) if samples else fallback


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
        "cpu_percent_avg": _sample_mean(samples, "client_cpu"),
        "memory_mb_avg": _sample_mean(
            samples,
            "client_memory",
            psutil.Process().memory_info().rss / 1024 / 1024,
        ),
        "ollama_cpu_percent_avg": _sample_mean(samples, "ollama_cpu"),
        "ollama_memory_mb_avg": _sample_mean(samples, "ollama_memory"),
        "gpu_utilization_percent_avg": _sample_mean(samples, "gpu_utilization"),
        "gpu_memory_mb_avg": _sample_mean(samples, "gpu_memory"),
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
