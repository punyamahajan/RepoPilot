"""
test_cli.py
-----------
Fastest way to sanity-check the Ollama connection without spinning up
Flask. Good for your own testing and for a quick live demo fallback.

Run:
    python test_cli.py
"""

from ollama_client import query_llm, list_available_models

def main():
    print("Checking Ollama connection...")
    try:
        models = list_available_models()
        print(f"Connected. Models available: {models}\n")
    except Exception as e:
        print(f"Could not reach Ollama: {e}")
        print("Make sure Ollama is running (`ollama serve`) and you've pulled a model")
        print("(`ollama pull codellama`).")
        return

    while True:
        prompt = input("Ask something ('q' to quit): ").strip()
        if prompt.lower() in ("q", "quit", "exit"):
            break
        if not prompt:
            continue
        answer = query_llm(prompt)
        print(f"\n--- Response ---\n{answer}\n")


if __name__ == "__main__":
    main()