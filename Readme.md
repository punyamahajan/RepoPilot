# RepoPilot Lab

RepoPilot Lab is a local, repository-aware coding assistant built with Python, Flask, Ollama, embeddings, and retrieval-augmented generation (RAG). It indexes a source repository, retrieves code related to a question, supplies that code to a selected local LLM, and displays the answer through HTTP APIs, a command-line orchestrator, or a browser dashboard.

The project also contains a repeatable evaluation suite that compares three Ollama code models using the same questions, prompts, repository index, and retrieved context.

## What the project provides

- Repository parsing and overlapping code chunking.
- Local embeddings and cosine-similarity retrieval.
- RAG answers grounded in retrieved source code.
- Three interchangeable local code models.
- Separate ingestion, LLM, dashboard, and evaluation services.
- A live browser UI for demonstrations.
- Quantitative model evaluation and qualitative RAG analysis.
- Docker Compose deployment while Ollama remains on the host.

## Architecture

There are four Docker services and one host dependency:

```text
Browser / curl / orchestrator.py
              |
              v
     Dashboard :5050 (demo UI)
              |
       +------+------+
       |             |
       v             v
Ingestion :5001   App/LLM :5000
       |             |
       |             v
       +------> Host Ollama :11434
          embeddings      generation

Evaluation runner (one-off container)
       |------> Ingestion :5001
       |------> App/LLM :5000 where required
       +------> Host Ollama :11434
```

Ollama is deliberately not containerized. The containers reach it through `host.docker.internal:11434`.

## How the main flows work

### Index-building flow

```text
Repository directory
  -> chunk_repo()
  -> overlapping source-code chunks
  -> get_embedding() using nomic-embed-text
  -> vectors plus chunk metadata
  -> data/index.json
```

`ingestion/chunking.py` walks supported code and documentation files. `ingestion/embeddings.py` asks Ollama for an embedding for each chunk. `ingestion/vectorstore.py` stores the vectors and source metadata in JSON.

### Live question-answering flow

```text
Question
  -> POST ingestion /search
  -> question embedding
  -> cosine similarity against indexed chunks
  -> top three source chunks
  -> POST app /ask with question, context, and selected model
  -> Ollama generation
  -> grounded response
```

The dashboard follows this flow directly. `orchestrator.py` provides the same flow from the command line. The LLM service can also perform retrieval itself when `/ask` receives `use_retrieval: true`.

### Evaluation flow

```text
24 labeled questions
  -> retrieve identical context once per question
  -> ask codellama, starcoder2, and qwen2.5-coder
  -> calculate accuracy, relevance, retrieval, hallucination,
     code-test, latency, tokens, CPU, and memory metrics
  -> evaluation/results.json
  -> aggregate tables and Markdown reports
  -> dashboard comparison view
```

Only the model changes during a comparison. The application, prompt construction, question, retrieved context, and knowledge base remain identical.

## Technologies used

| Technology | Purpose |
|---|---|
| Python 3.12 | Application and evaluation implementation |
| Flask | Ingestion, LLM, and dashboard HTTP services |
| Gunicorn | Production-style WSGI server inside containers |
| Ollama | Local model and embedding APIs |
| `codellama` | First code-generation model |
| `starcoder2` | Second comparison model |
| `qwen2.5-coder` | Third comparison model |
| `nomic-embed-text` | Repository, question, and response embeddings |
| NumPy | Vector storage and cosine-similarity calculations |
| Requests | Communication among Python services and Ollama |
| psutil | CPU and memory sampling during evaluation calls |
| Markdown | Rendering reports in the dashboard |
| HTML, CSS, JavaScript | Sortable dashboard table, chart, and live Ask UI |
| Docker Compose | Multi-service build, networking, startup ordering, and health checks |

## Project structure

```text
RepoPilot/
├── app/                         LLM HTTP service
│   ├── main.py                  GET /health and POST /ask
│   ├── ollama_client.py         Ollama generation client
│   ├── test_cli.py              Basic CLI test
│   └── Dockerfile
├── ingestion/                   Repository ingestion and retrieval service
│   ├── chunking.py              Walk and split repository files
│   ├── embeddings.py            Ollama embedding client
│   ├── vectorstore.py           JSON-backed vector index and similarity search
│   ├── ingestion_service.py     GET /health, POST /build-index, POST /search
│   └── Dockerfile
├── dashboard/                   Browser UI service
│   ├── app.py                   Results/report API and live RAG orchestration
│   ├── templates/index.html     Sortable table, bar chart, reports, Ask form
│   └── Dockerfile
├── evaluation/                  Week 4 evaluation suite
│   ├── eval_questions.json      24 questions across seven categories
│   ├── setup_models.py          Confirm or pull all comparison models
│   ├── run_models.py            Identical per-model calls and resource capture
│   ├── metrics.py               Metric implementations and definitions
│   ├── run_evaluation.py        Complete dataset runner; writes results.json
│   ├── analyze_results.py       Aggregates results and writes ANALYSIS.md
│   ├── rag_pipeline_analysis.py Writes RAG_PIPELINE_ANALYSIS.md
│   ├── multi_file_questions.py  Writes REPO_UNDERSTANDING.md
│   └── Dockerfile
├── data/
│   ├── sample_repo/             Small demonstration repository
│   └── index.json               Persisted vector index
├── reports/
│   └── exercise3_rag_vs_no_rag.md
├── orchestrator.py              Host CLI: retrieval service -> LLM service
├── integration_test.py          Direct service integration proof
├── exercise3_rag_comparison.py  Week 3 RAG versus no-RAG experiment
├── docker-compose.yml           All four services on one network
├── requirements.txt             Local/full dependencies
├── requirements-dashboard.txt   Focused dashboard image dependencies
├── requirements-evaluation.txt  Focused evaluator image dependencies
├── SERVICES.md                  Service and endpoint reference
└── README_WEEK4.md              Short pointer to this complete guide
```

Generated files such as `evaluation/results.json`, `evaluation/ANALYSIS.md`, `evaluation/RAG_PIPELINE_ANALYSIS.md`, and `evaluation/REPO_UNDERSTANDING.md` appear after their corresponding commands run.

## Prerequisites

Install:

- Python 3.10 or newer for local execution; Docker images use Python 3.12.
- Ollama.
- Docker Desktop or Docker Engine with Compose for the recommended setup.
- Enough disk space for three code models and the embedding model.

All commands below must be run from the repository root.

## Recommended setup: Docker Compose

### 1. Start Ollama on the host

Ollama may already be running if its desktop application is open. Otherwise:

```powershell
ollama serve
```

For container access, Ollama must listen beyond host loopback. On Windows PowerShell, set this before starting Ollama if Docker cannot reach it:

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

### 2. Install or confirm the models

Install the embedding model and use the setup script for the three generation models:

```powershell
ollama pull nomic-embed-text
python evaluation/setup_models.py
```

Confirm manually if desired:

```powershell
ollama list
```

The list should contain `nomic-embed-text`, `codellama`, `starcoder2`, and `qwen2.5-coder`.

### 3. Build and start the three long-running services

```powershell
docker-compose up --build -d
```

With the newer integrated Compose command, the equivalent is:

```powershell
docker compose up --build -d
```

Compose starts these services in dependency order:

| Service | Host URL | Role |
|---|---|---|
| `ingestion` | http://localhost:5001 | Index construction and search |
| `app` | http://localhost:5000 | LLM generation API |
| `dashboard` | http://localhost:5050 | Results and live demo UI |
| `evaluation` | One-off only | Benchmark and report runner |

Open **http://localhost:5050** in a browser.

### 4. Check service health

```powershell
curl.exe http://localhost:5001/health
curl.exe http://localhost:5000/health
curl.exe http://localhost:5050/health
docker-compose ps
```

The ingestion response should report `index_ready: true`. If it does not, build the sample index using the path visible inside its container:

```powershell
curl.exe -X POST http://localhost:5001/build-index `
  -H "Content-Type: application/json" `
  -d '{"repo_path":"/repopilot/data/sample_repo"}'
```

For Bash, use a single line or replace PowerShell backticks with backslashes.

### 5. Ask a question

Use the Ask form at http://localhost:5050, select a model, and submit a repository question.

You can also call the app service and let it retrieve context:

```powershell
curl.exe -X POST http://localhost:5000/ask `
  -H "Content-Type: application/json" `
  -d '{"prompt":"How is the payment fee calculated?","model":"codellama","use_retrieval":true}'
```

Or use the host orchestrator while the containers are running:

```powershell
python orchestrator.py "Which function verifies a password?" --model codellama
```

### 6. Run the full model evaluation

The evaluation service is under the `tools` profile because it is a one-off job:

```powershell
docker-compose --profile tools run --rm evaluation
```

This evaluates 24 questions against all three models, producing 72 generation calls. Runtime depends heavily on model size, available RAM, and CPU/GPU acceleration.

For a quick smoke test:

```powershell
docker-compose --profile tools run --rm evaluation `
  python evaluation/run_evaluation.py --limit 1 --models codellama
```

The smoke command writes `evaluation/results.json`, so run the full evaluation afterward before drawing model-comparison conclusions.

### 7. Generate all analysis reports

Run these after the full evaluation:

```powershell
docker-compose --profile tools run --rm evaluation python evaluation/analyze_results.py
docker-compose --profile tools run --rm evaluation python evaluation/rag_pipeline_analysis.py
docker-compose --profile tools run --rm evaluation python evaluation/multi_file_questions.py
```

Refresh http://localhost:5050 to see the latest results. The evaluation and report directories are bind-mounted, so rebuilding the dashboard image is unnecessary.

### 8. View logs and stop

```powershell
docker-compose logs -f ingestion app dashboard
docker-compose down
```

## Run everything locally without Docker

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Linux/macOS, activate with `source .venv/bin/activate`.

### 2. Start Ollama and prepare models

```powershell
ollama serve
```

In another terminal with the virtual environment active:

```powershell
ollama pull nomic-embed-text
python evaluation/setup_models.py
```

### 3. Start the ingestion service

Terminal 2:

```powershell
python ingestion/ingestion_service.py
```

Build the index if `/health` reports it is unavailable:

```powershell
curl.exe -X POST http://localhost:5001/build-index `
  -H "Content-Type: application/json" `
  -d '{"repo_path":"data/sample_repo"}'
```

### 4. Start the LLM service

Terminal 3:

```powershell
python app/main.py
```

### 5. Start the dashboard

Terminal 4:

```powershell
python dashboard/app.py
```

Open http://localhost:5050.

### 6. Run evaluation locally

With ingestion still running:

```powershell
python evaluation/run_evaluation.py
python evaluation/analyze_results.py
```

With both ingestion and app services running:

```powershell
python evaluation/rag_pipeline_analysis.py
python evaluation/multi_file_questions.py
```

Stop each local server with `Ctrl+C`.

## API reference

### Ingestion service

`GET /health`

Returns service and index readiness.

`POST /build-index`

```json
{"repo_path": "data/sample_repo"}
```

`POST /search`

```json
{"query": "How is the payment fee calculated?", "k": 3}
```

### LLM service

`GET /health`

Checks the service's connection to host Ollama and lists available models.

`POST /ask` with automatic retrieval:

```json
{
  "prompt": "What does login do?",
  "model": "codellama",
  "use_retrieval": true,
  "k": 3
}
```

`POST /ask` with supplied context:

```json
{
  "prompt": "Explain this code",
  "context": "auth.py (chunk 0): ...",
  "model": "starcoder2",
  "use_retrieval": false
}
```

### Dashboard service

- `GET /`: dashboard page.
- `GET /health`: dashboard-to-ingestion connectivity.
- `POST /api/ask`: live UI endpoint; accepts `question` and `model`.

## Evaluation metrics

| Metric | Calculation |
|---|---|
| Correctness/accuracy | Fraction of expected keywords found as case-insensitive substrings in the response |
| Relevance | Cosine similarity between response and question embeddings |
| Retrieval quality | Whether the top retrieved chunk comes from `expected_file` |
| Hallucination rate | Fraction of responses containing function/file claims absent from retrieved context |
| Test-pass rate | Fraction of applicable generated Python functions that pass the specified expression |
| Response latency | Wall-clock seconds around one `query_llm()` call |
| Token usage | Ollama `prompt_eval_count + eval_count` |
| CPU and memory | Mean Python evaluator CPU percentage and RSS MiB sampled during the call |

CPU and memory describe the evaluation client, not the separate host Ollama daemon. Keyword accuracy and hallucination detection are intentionally simple heuristics; use the qualitative reports for deeper interpretation.

## Using another target repository

Place or mount the repository beneath `data/`, then rebuild the index. For example, if it is at `data/my_repo`:

```powershell
curl.exe -X POST http://localhost:5001/build-index `
  -H "Content-Type: application/json" `
  -d '{"repo_path":"/repopilot/data/my_repo"}'
```

Update `evaluation/eval_questions.json` so each question, expected answer, and expected file describes the new repository. This is essential: evaluation scores are only meaningful when the ground truth matches the indexed code.

## Environment variables

| Variable | Default | Used by |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` locally | App, ingestion, evaluation |
| `INGESTION_SERVICE_URL` | `http://localhost:5001` locally | App, dashboard, evaluation |
| `LLM_SERVICE_URL` | `http://localhost:5000` locally | Dashboard and qualitative analyses |
| `INDEX_PATH` | `data/index.json` | Ingestion service |
| `EVALUATION_MODELS` | `codellama,starcoder2,qwen2.5-coder` | Setup, evaluator, dashboard |
| `RESULTS_PATH` | `evaluation/results.json` | Dashboard |

## Troubleshooting

### App is unhealthy or Ollama is unreachable

- Confirm `ollama list` works on the host.
- Confirm http://localhost:11434/api/tags opens on the host.
- Restart Ollama with `OLLAMA_HOST=0.0.0.0:11434` for Docker access.
- Check `docker-compose logs app`.

### Search says the index is not ready

Call `/build-index` using the correct local or container path. The `data/` directory is bind-mounted in Compose, so the rebuilt index persists on the host.

### A selected model is missing

Run:

```powershell
python evaluation/setup_models.py
```

Then verify with `ollama list`.

### Dashboard has no comparison rows

Run the full evaluation to create `evaluation/results.json`, then refresh the page.

### Linux cannot resolve the host Ollama address

The Compose file includes `host.docker.internal:host-gateway`, supported by modern Docker Engine. On older installations, upgrade Docker or use host networking and change `OLLAMA_BASE_URL` appropriately.

## Exercise status

- Week 3 Exercises 1–5: complete.
- Week 4 model comparison, evaluation dataset, metrics, analysis, RAG analysis, and repository understanding: implemented.
- Dashboard and four-service Docker deployment: implemented.
