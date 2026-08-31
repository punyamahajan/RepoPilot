# RepoPilot Lab — Person A + Person B (+ integration)

Covers Week 3, Exercise 1 (App + Ollama) and Exercise 2 (Knowledge Base).

## Repo layout

```
app/                <- Person A: Ollama wrapper + Flask API
  ollama_client.py
  main.py
  test_cli.py
ingestion/           <- Person B: chunking, embeddings, vectorstore
  chunking.py
  embeddings.py
  vectorstore.py
data/
  sample_repo/       <- small demo repo (auth.py, payment.py, models.py) to index right away
  index.json          <- generated after you build the index (not committed — see .gitignore below)
integration_test.py   <- proves A + B talk to each other correctly
requirements.txt
```

## Setup

1. Install Ollama: https://ollama.com/download
2. Pull models:
   ```
   ollama pull codellama          # for generation
   ollama pull nomic-embed-text   # for embeddings
   ```
   (For Week 4 Ex.1 also pull `starcoder2` and one more, e.g. `deepseek-coder`.)
3. Start Ollama (`ollama serve` if it's not already running)
4. Install Python deps:
   ```
   pip install -r requirements.txt
   ```

## Person A — `app/`

`query_llm(prompt, context="", model="codellama")` in `ollama_client.py` is the function everyone builds on. `main.py` wraps it in a Flask `/ask` endpoint. `test_cli.py` is a no-server sanity check.

```
cd app
python test_cli.py          # quick manual test
# or
python main.py               # run as a service, then curl localhost:5000/ask
```

## Person B — `ingestion/`

`build_index(repo_path)` in `vectorstore.py` runs the full Documents -> Chunking -> Embeddings -> Vector Representation pipeline and saves the result to disk. `load_index(path)` reloads it later without re-embedding everything.

```
cd ingestion
python vectorstore.py ../data/sample_repo
```
This chunks the sample repo, embeds every chunk via Ollama, saves to `../data/index.json`, and runs a test query so you can see retrieval working.

To index the **real target repo** once you've picked one for the project, just point it at that path instead:
```
python vectorstore.py /path/to/target/repo
```

## Connecting A + B — `integration_test.py`

This is the real proof the two halves work together — no stubs, actual `query_llm()` calls fed with actual retrieved context from the vectorstore:

```
Question -> vectorstore.similarity_search() [B] -> context -> query_llm() [A] -> response
```

Run from the **repo root** (not from inside `app/` or `ingestion/`):
```
python integration_test.py
```

First run builds the index from `data/sample_repo` (takes a few seconds — it's embedding 3 small files) and caches it to `data/index.json`. Every run after that loads the cached index instantly. Delete `data/index.json` if you change the sample repo or switch to the real target repo and want a fresh index.

It runs three test questions and prints, for each: the question, the retrieved context chunks, and the final LLM response — exactly the `Question -> Retrieved Context -> LLM Response` log format Exercise 3 and the Week 4 RAG-analysis exercise both want. Good idea to save this output to a file for your report.

**Why this works without any restructuring:** `integration_test.py` adds both `app/` and `ingestion/` to `sys.path` before importing, so each module keeps its simple, flat `from ollama_client import query_llm` / `from chunking import chunk_repo` style — nobody had to rewrite their imports to package form.

## Interface contract (for Person C)

Don't change these signatures without a heads-up in the group chat — Person C's `retrieval.py` is built against stub versions of both and expects to swap in these exact ones on integration day:

```python
# app/ollama_client.py
query_llm(prompt: str, context: str = "", model: str = "codellama") -> str

# ingestion/vectorstore.py
build_index(repo_path: str) -> VectorStore
load_index(path: str) -> VectorStore
VectorStore.similarity_search(query: str, k: int = 3) -> list[str]
```

## .gitignore suggestion

```
data/index.json
__pycache__/
*.pyc
.venv/
```
(Don't commit the generated index — everyone should be able to rebuild it locally from `data/sample_repo` or the real target repo.)