# Person A — Application + Ollama Integration

Covers Week 3, Exercise 1:

```
User -> Application -> API -> Ollama -> Code Llama -> Response
```

## Files

- `app/ollama_client.py` — core wrapper. `query_llm(prompt, context="", model="codellama")` is the function everyone else builds on top of.
- `app/main.py` — Flask API exposing `POST /ask` and `GET /health`.
- `app/test_cli.py` — no-server sanity check, useful for quick manual testing or a live-demo fallback.
- `requirements.txt` — `flask`, `requests`.

## Setup

1. Install Ollama: https://ollama.com/download
2. Pull the model:
   ```
   ollama pull codellama
   ```
   (For Week 4 Exercise 1 you'll also want `ollama pull starcoder2` and a third model, e.g. `ollama pull deepseek-coder`.)
3. Start Ollama (usually runs automatically after install; if not: `ollama serve`)
4. Install Python deps:
   ```
   pip install -r requirements.txt
   ```

## Running it

**Option A — quick CLI test:**
```
cd app
python test_cli.py
```

**Option B — as a service (matches the "Application + API" framing for the brief):**
```
cd app
python main.py
```
Then in another terminal:
```
curl -X POST http://localhost:5000/ask \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What does a REST API do?"}'
```

Health check:
```
curl http://localhost:5000/health
```

## Interface contract (for Person B / Person C)

Don't change this signature without a heads-up in the group chat:

```python
query_llm(prompt: str, context: str = "", model: str = "codellama") -> str
```

- Person C calls this with `context` = whatever they retrieved from the vectorstore. Leaving `context=""` gives the no-RAG baseline response for the RAG-vs-no-RAG comparison (Week 3, Ex.3).
- `model` lets anyone rerun the same prompt against a different pulled model for Week 4, Ex.1 — no code changes needed, just pass a different string.

## Suggested repo layout (once merged with B and C)

```
/app          <- this folder (Person A)
/ingestion    <- Person B: chunking, embeddings, vectorstore build
/retrieval    <- Person C: RAG logic, context assembly
/data         <- shared: target repo + eval questions
requirements.txt
```