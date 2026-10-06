# CodeImpact AI

CodeImpact extends the existing RepoPilot project with repository change analysis. RepoPilot's Week 3–5 application, evaluation data, and dashboard stay available on port 5050. The new React dashboard and FastAPI service run on port 5070.

## Start locally

Start Docker Desktop and Ollama, then run from PowerShell:

```powershell
cd C:\code\RepoPilot
ollama pull codellama
ollama pull nomic-embed-text
powershell -ExecutionPolicy Bypass -File codeimpact/start.ps1
```

The models only need downloading once. If Ollama is not running, use `ollama serve` in a separate terminal. Open **http://127.0.0.1:5070/**. Subsequent runs can use `codeimpact/start.ps1 -NoBuild` when source has not changed. To rebuild only CodeImpact: `docker compose up --build -d codeimpact`. Stop with `docker compose stop` (saved reports and indexes remain in the named volume). Do not use `down -v` if you want to retain reports.

## Use the application

1. Leave repository as `.` to analyze RepoPilot, or select a subdirectory such as `data/codeimpact_demo`. The overview shows source/test/documentation coverage.
2. Choose Describe (natural-language change or code snippet), Paste diff, Select file, or Git changes. Git changes compares staged, unstaged, and untracked supported files against HEAD.
3. Select semantic retrieval and AI reasoning as needed, then Analyze impact. First indexing embeds source chunks; subsequent jobs reuse unchanged Chroma vectors.
4. Inspect changed, direct, and transitive consumer files in the impact map. Click a file to see a source-backed dependency path, API routes, risk reasons, and symbols in scope.
5. Review proposed mitigations and recommended tests. AI findings cite source evidence; related semantic candidates are explicitly unconfirmed.
6. Export Markdown or reopen saved reports from the sidebar. JSON is available at `/api/reports/{id}`.
7. Turn on Watch repository for automatic analysis after edits stabilize. Watching is opt-in per service session; it starts observing future changes and compares reports to HEAD. It uses graph/semantic analysis by default to avoid repeated LLM generations. Enable AI review through Analyze when ready.

The repository is mounted read-only. The analyzer never edits it and the web API never executes tests or model-generated commands. The CLI has an explicit `--run-tests` option for a trusted repository.

## Architecture and implementation

```text
React dashboard / CLI / PR workflow
                  |
             FastAPI job queue
                  |
  Git diff + source/test/doc snapshot
                  |
       AST + module dependency graph
                  |                 
  Function/line chunks -> Ollama embeddings -> persistent Chroma
                  |                            |
       reverse dependency traversal + semantic retrieval
                  |
          LangChain prompt -> Code Llama via Ollama
                  |
    citation validation + conservative risk rules
                  |
       impact map + tests + Markdown / JSON report
```

`codeimpact/repository.py` handles bounded reads, .gitignore, symlink exclusion, Git comparisons, and chunks with line references. `graph.py` resolves Python imports and imported calls, JavaScript/TypeScript relative imports, literal file references, and Python API routes. `retrieval.py` keeps persistent Chroma vectors; it uses Ollama's `/api/embed` and an explicit keyword baseline. `engine.py` merges dependency paths, retrieval evidence, risk signals, and validated AI suggestions. `api.py` provides a serialized background job queue, persistent reports, and a debounced watcher. The UI uses React with locally built Vite assets.

Risk is deliberately transparent: security/payment/migration names, API handlers, and broad downstream reach elevate a component to High; other executable code is Medium; tests/docs are Low. These are review-priority heuristics, not proof of a defect. AI risks are shown separately from the deterministic report risk.

### Coverage boundaries

- Supported source, documentation, and configuration extensions are listed in `repository.py`. Dependency parsing is strongest for Python; JS/TS imports are pattern-based. Other languages are searchable but do not have full compiler dependency resolution.
- Default limits: 2,500 files and 250 KB per file, with excluded/skipped files reported. Generated directories, binaries, `.env` files, keys, the existing vector index, and lock files are excluded. Long/minified source lines are shortened for embedding context; AST parsing uses original text.
- Paths in a pasted diff are resolved against the chosen repository; the diff is analyzed as a proposal and is never applied. Use Git changes for deleted files to retain base-revision dependency edges.
- API routes and symbols are candidates within impacted files. File dependencies do not prove that every symbol changes.
- No static graph or RAG pipeline can guarantee all possible runtime effects. Dynamic loading, reflection, event buses, external APIs, and implicit service contracts can be missed.
- AI findings must reference existing evidence IDs in the provided context and the cited file. This validates citation integrity, not the factual correctness of every sentence. Human review is required.
- Failed embeddings or generation are surfaced in the report. Graph/keyword results remain available and are never represented as successful AI analysis.
- Reports are tied to a content fingerprint; reopening a report shows its historical snapshot, not a newly analyzed repository state. Jobs are in memory and reset on restart; completed reports persist.
- The local service has no multi-user authentication. It binds to localhost in Compose. Do not expose it publicly without authentication and an explicit repository access policy.

## CLI and reproducibility

Use a separate Python environment to preserve existing dependencies:

```powershell
python -m venv .codeimpact/venv
.codeimpact/venv/Scripts/python -m pip install -r codeimpact/requirements.txt
.codeimpact/venv/Scripts/python -m codeimpact.cli --repo . --file app/ollama_client.py --description "Change response metadata"
.codeimpact/venv/Scripts/python -m codeimpact.cli --repo . --git --no-semantic --no-llm
.codeimpact/venv/Scripts/python -m codeimpact.cli --repo . --git --base main --head HEAD --run-tests
.codeimpact/venv/Scripts/python -m codeimpact.evaluate --semantic
```

For native UI development: `cd codeimpact/frontend`, `npm ci`, `npm run build`; then run `.codeimpact/venv/Scripts/python -m uvicorn codeimpact.api:app --host 127.0.0.1 --port 5070` from the root. `npm run dev` proxies API calls to port 5070.

For a container CLI using the checked-out project:

```powershell
docker compose exec -w /workspace codeimpact python -m codeimpact.cli --repo . --file app/ollama_client.py --no-semantic --no-llm --output /state/cli-report
docker compose exec -w /workspace codeimpact python -m pytest -p no:cacheprovider codeimpact/tests data/codeimpact_demo/tests -q
```

The CLI runs only traced Python test files using `python -m pytest -- <paths>` with no shell. JavaScript and other test frameworks are recommended for manual execution. Do not run repository tests unless you trust the repository, since tests are executable code.

## Evaluation

`codeimpact/evaluation/cases.json` contains ten hand-labelled changes covering authentication policy, registration, password reset, fees, checkout, and reporting. The executable fixture is `data/codeimpact_demo`. The same cases are used for keyword top-5 retrieval, reverse dependency analysis, and optionally graph-plus-semantic candidates.

Precision = TP / predicted affected files. Recall = TP / expected affected files. F1 = 2PR / (P+R). Results are macro-averaged, with per-case false positives/negatives and latency in JSON. A graph-perfect score on this small fixture is a regression check; it is not evidence of general production accuracy or of LLM superiority. AI quality needs a separately reviewed, larger benchmark.

## Pull requests

`.github/workflows/codeimpact.yml` runs application/analyzer tests, analyzes PR changes, runs traced Python tests, and uploads Markdown/JSON artifacts. On same-repository PRs a separate restricted reporting job posts or updates one report comment. Fork PRs receive artifacts without a write-token comment job. GitHub-hosted CI explicitly uses graph and keyword analysis because no local Ollama service is present; local runs provide the full semantic/LLM path.

The workflow is implemented in the repository; it only executes once these changes are pushed and a PR or manual workflow run triggers it. No PR or remote workflow was created as part of local implementation.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CODEIMPACT_REPO_ROOT` | project root; `/workspace` in Docker | Boundary for browsable repositories |
| `CODEIMPACT_STATE_DIR` | `.codeimpact`; `/state` in Docker | Reports and Chroma storage |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local model service |
| `CODEIMPACT_EMBED_MODEL` | `nomic-embed-text` | Embedding model; separate collection per model |
| `CODEIMPACT_MODELS` | `codellama,starcoder2,qwen2.5-coder` | Allowed review models |
| `CODEIMPACT_LLM_TIMEOUT` | 240 | Generation timeout in seconds |

To analyze a different host directory in Docker, change only the CodeImpact source volume `.:/workspace:ro` to the desired directory; keep `/workspace` as the container repository root.

Implementation API references: [Chroma supplied embeddings](https://docs.trychroma.com/docs/collections/add-data), [Ollama embedding endpoint](https://docs.ollama.com/api/embed), [FastAPI background work](https://fastapi.tiangolo.com/tutorial/background-tasks/).
