"""Confirm required Ollama models exist and pull any that are missing."""

import json
import os
import requests

BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
REQUIRED = [m.strip() for m in os.getenv("EVALUATION_MODELS", "codellama,starcoder2,qwen2.5-coder").split(",") if m.strip()]


def base_name(name):
    return name.split(":", 1)[0]


def main():
    tags = requests.get(f"{BASE_URL}/api/tags", timeout=15)
    tags.raise_for_status()
    installed = {base_name(m["name"]) for m in tags.json().get("models", [])}
    for model in REQUIRED:
        if base_name(model) in installed:
            print(f"ready: {model}")
            continue
        print(f"pulling: {model} (this can take several minutes)", flush=True)
        response = requests.post(f"{BASE_URL}/api/pull", json={"name": model, "stream": False}, timeout=3600)
        response.raise_for_status()
        print(json.dumps(response.json()))
    print("All evaluation models are ready:", ", ".join(REQUIRED))


if __name__ == "__main__":
    main()
