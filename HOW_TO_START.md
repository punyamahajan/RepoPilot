# How to Rebuild and Start RepoPilot

This guide uses **Windows PowerShell** and Docker Compose, which is the recommended way to run the complete project.

Run every command from the repository root:

```powershell
cd C:\Users\lenovo\RepoPilot
```

## 1. Prerequisites

Install and start:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose
- [Ollama](https://ollama.com/)
- Python 3.10 or newer (needed for the model setup script and optional CLI)

Check that they are available:

```powershell
docker --version
docker compose version
ollama --version
python --version
```

## 2. Start Ollama

Ollama must run on the host because all RepoPilot containers connect to it.

If the Ollama desktop application is already running, first try:

```powershell
ollama list
```

If Ollama is not running, open a separate PowerShell window and run:

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

Keep that window open. Setting `OLLAMA_HOST` allows the Docker containers to reach Ollama.

## 3. Download the required models

In another PowerShell window, from the repository root, run:

```powershell
ollama pull nomic-embed-text
python evaluation/setup_models.py
ollama list
```

The final list should include:

- `nomic-embed-text`
- `codellama`
- `starcoder2`
- `qwen2.5-coder`

Model downloads can be large and may take several minutes.

## 4. Rebuild and start everything

Stop old RepoPilot containers, rebuild every image, and start the three long-running services:

```powershell
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d
```

For an ordinary rebuild after changing code, the shorter command is enough:

```powershell
docker compose up --build -d
```

The running services are:

| Service | Address | Purpose |
|---|---|---|
| Ingestion | http://localhost:5001 | Builds and searches the repository index |
| App | http://localhost:5000 | Sends grounded prompts to Ollama |
| Dashboard | http://localhost:5050 | Web interface and evaluation results |

The `evaluation` container is a one-off tool, so it is not left running.

## 5. Check that the services are ready

```powershell
docker compose ps
curl.exe http://localhost:5001/health
curl.exe http://localhost:5000/health
curl.exe http://localhost:5050/health
```

All three containers should become `healthy`. The app health response should show the installed Ollama models.

## 6. Build or refresh the repository index

The included `data/index.json` may load automatically. Check the ingestion health response from the previous step. If `index_ready` is `false`, or if files in `data/sample_repo` changed, rebuild it:

```powershell
curl.exe -X POST http://localhost:5001/build-index `
  -H "Content-Type: application/json" `
  -d '{"repo_path":"/repopilot/data/sample_repo"}'
```

The path above is intentionally the path **inside the ingestion container**. A successful response reports `"status":"built"` and the number of indexed chunks.

## 7. Open and test RepoPilot

Open the dashboard:

```text
http://localhost:5050
```

Ask a question in the web interface, such as:

```text
How is the payment fee calculated?
```

You can also test the API directly:

```powershell
curl.exe -X POST http://localhost:5000/ask `
  -H "Content-Type: application/json" `
  -d '{"prompt":"How is the payment fee calculated?","model":"codellama","use_retrieval":true}'
```

Or use the Python CLI while the containers are running:

```powershell
python orchestrator.py "Which function verifies a password?" --model codellama
```

## 8. Run the evaluation suite (optional)

First run one question with one model as a smoke test:

```powershell
docker compose --profile tools run --rm evaluation `
  python evaluation/run_evaluation.py --limit 1 --models codellama
```

Then run the complete evaluation:

```powershell
docker compose --profile tools run --rm evaluation
```

The full run evaluates 24 questions with three models (72 model calls), so it can take a long time. It writes `evaluation/results.json`.

Generate all reports after the full run:

```powershell
docker compose --profile tools run --rm evaluation python evaluation/analyze_results.py
docker compose --profile tools run --rm evaluation python evaluation/rag_pipeline_analysis.py
docker compose --profile tools run --rm evaluation python evaluation/multi_file_questions.py
```

Refresh http://localhost:5050 afterward. The generated results and reports are bind-mounted, so the dashboard does not need another rebuild.

## 9. Logs, restart, and shutdown

Follow logs from all long-running services:

```powershell
docker compose logs -f ingestion app dashboard
```

Press `Ctrl+C` to stop following logs; the containers continue running.

Restart all services:

```powershell
docker compose restart
```

Stop and remove the RepoPilot containers and network:

```powershell
docker compose down
```

This does not delete the host files under `data`, `evaluation`, or `reports`.

## Quick start for later use

After the first successful setup, the usual startup is only:

```powershell
cd C:\Users\lenovo\RepoPilot
ollama list
docker compose up -d
docker compose ps
```

Then open http://localhost:5050.

## Troubleshooting

### App is unhealthy or Ollama is unreachable

Confirm that Ollama is running and listening for container connections:

```powershell
curl.exe http://localhost:11434/api/tags
```

If necessary, stop Ollama and restart it in a PowerShell window with:

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

Then restart the containers:

```powershell
docker compose restart
```

### A required model is missing

```powershell
ollama pull nomic-embed-text
python evaluation/setup_models.py
ollama list
```

### Index is not ready

Run the build-index command in step 6, then check:

```powershell
curl.exe http://localhost:5001/health
```

### A port is already in use

RepoPilot requires ports `5000`, `5001`, and `5050`. Stop the program using the conflicting port, or change the host-side port in `docker-compose.yml` and rebuild.

### A container exits or never becomes healthy

```powershell
docker compose ps -a
docker compose logs --tail 200 ingestion app dashboard
```

Fix the reported error and rebuild:

```powershell
docker compose up --build -d
```

### Completely recreate only the Docker stack

This recreates images and containers but preserves repository files and the downloaded Ollama models:

```powershell
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d --force-recreate
```
