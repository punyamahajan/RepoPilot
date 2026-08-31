# RepoPilot service reference

RepoPilot uses three long-running HTTP services, one one-off evaluation service, and host Ollama.

| Compose service | Port | Responsibility | Depends on |
|---|---:|---|---|
| `ingestion` | 5001 | Build/load the vector index and retrieve similar chunks | Host Ollama embeddings |
| `app` | 5000 | Construct grounded prompts and request model responses | Ingestion and host Ollama generation |
| `dashboard` | 5050 | Display results/reports and provide the live Ask UI | Ingestion and app |
| `evaluation` | None | Run benchmarks and generate analysis files | Ingestion, app where required, and host Ollama |
| Host Ollama | 11434 | Serve generation and embedding models | Host machine |

## Internal Compose addresses

- Dashboard to ingestion: `http://ingestion:5001`
- Dashboard to app: `http://app:5000`
- App to ingestion: `http://ingestion:5001`
- Containers to Ollama: `http://host.docker.internal:11434`

Compose health checks ensure ingestion is healthy before app starts, and both ingestion and app are healthy before dashboard starts.

## Endpoints

### Ingestion

- `GET /health`
- `POST /build-index` with `{"repo_path":"..."}`
- `POST /search` with `{"query":"...","k":3}`

### App/LLM

- `GET /health`
- `POST /ask` with a prompt, model, and either supplied context or `use_retrieval: true`

### Dashboard

- `GET /`
- `GET /health`
- `POST /api/ask` with `{"question":"...","model":"codellama"}`

See [Readme.md](Readme.md) for full architecture, startup, verification, evaluation, and troubleshooting instructions.
