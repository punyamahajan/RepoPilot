# CodeImpact AI & RepoPilot Lab — Master Project Documentation

> **Intelligent Repository Reasoning, Change Impact Prediction, and Multi-Model Evaluation**  
> *Version: 2.4.0 · Architecture: Unified Microservices & Motion UI Platform · License: MIT*

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Core Subsystems](#3-core-subsystems)
   - [3.1 Repository Ingestion & Vector Retrieval](#31-repository-ingestion--vector-retrieval)
   - [3.2 CodeImpact Change Intelligence Engine](#32-codeimpact-change-intelligence-engine)
   - [3.3 Multi-Model Benchmark Suite & Oscilloscope](#33-multi-model-benchmark-suite--oscilloscope)
   - [3.4 Zero-Trust Guardrails & Acceptance Testing](#34-zero-trust-guardrails--acceptance-testing)
   - [3.5 Motion UI Visual Platform](#35-motion-ui-visual-platform)
4. [Service Topology & Ports](#4-service-topology--ports)
5. [Repository Structure](#5-repository-structure)
6. [Getting Started & Operations](#6-getting-started--operations)
7. [API Specification](#7-api-specification)
8. [CI/CD & GitHub Actions Integration](#8-cicd--github-actions-integration)
9. [Empirical Evaluation Findings](#9-empirical-evaluation-findings)
10. [Design Boundaries & Safety Guarantees](#10-design-boundaries--safety-guarantees)

---

## 1. Executive Summary

Modern software codebases are intricate dependency webs. When developers modify a function, class, schema, or configuration, understanding the **blast radius**—the ripple effect across callers, downstream services, documentation, and regression tests—is traditionally slow, manual, and error-prone. Standard grep or keyword search surfaces exact syntax matches but misses semantic relationships, while traditional compiler graphs miss cross-boundary context.

**CodeImpact AI** (built atop **RepoPilot Lab**) unifies:
1. **Repository-Aware RAG (Retrieval-Augmented Generation)**: Grounded code question answering across local LLMs.
2. **Deterministic AST + Semantic Change Impact Analysis**: Hybrid dependency graph traversal paired with Code Llama reasoning to predict impacted files, calculate risk levels, and pinpoint regression tests before merging.
3. **Multi-Model Benchmark Suite**: Rigorous, reproducible benchmarking comparing `CodeLlama`, `StarCoder2`, and `Qwen2.5-Coder` across 24 software engineering tasks with an interactive Motion-inspired oscilloscope.
4. **Deterministic Pre- & Post-Model Guardrails**: Zero-trust request routing, prompt refusal, and output validation to prevent hallucinated advice from reaching developers.
5. **Motion UI Design System**: A unified single-page dashboard featuring a 60 FPS interactive HTML5 ASCII vector flow field, dev-tool plus-terminal cards, and real-time AST binding.

---

## 2. High-Level Architecture

The platform combines deterministic graph analysis, local embedding vector spaces, and local LLMs via Ollama:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          DEVELOPER INTERFACES                          │
│   • Motion UI Dashboard (:5050)           • React Fast Studio (:5070) │
│   • CLI (codeimpact.cli)                  • GitHub Actions PR Bot     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST / JSON
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     CODEIMPACT API & SERVICE LAYER                     │
│  [Flask / FastAPI Orchestration] • [Serialized Async Job Queue]        │
│  [Content-Hash Report Store]     • [Debounced Filesystem Watcher]      │
└───────────────┬───────────────────┬───────────────────┬────────────────┘
                │                   │                   │
                ▼                   ▼                   ▼
┌──────────────────────┐  ┌──────────────────┐  ┌───────────────────────┐
│   STATIC ANALYSIS    │  │ SEMANTIC VECTORS │  │      LOCAL LLMS       │
│ • Python AST Imports │  │ • Ollama         │  │ • Code Llama (7B)     │
│ • Call Hierarchy     │  │   nomic-embed    │  │ • StarCoder2 (7B)     │
│ • JS/TS Module Refs  │  │ • ChromaDB Store │  │ • Qwen2.5-Coder (7B)  │
│ • API Route Scanners │  │ • BM25 Keywords  │  │ Host Port :11434      │
└───────────────┬──────┘  └─────────┬────────┘  └───────────┬───────────┘
                │                   │                       │
                └─────────────────┐ │ ┌─────────────────────┘
                                  ▼ ▼ ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     CHANGE IMPACT SYNTHESIS ENGINE                     │
│  1. Identify Changed Seeds (Git Diff / Proposed Files)                 │
│  2. Reverse Transitive Dependency Traversal (Blast Radius)             │
│  3. Evidence Retrieval & Citation Grounding (Function Chunks)          │
│  4. Deterministic Risk Classification (High / Medium / Low)            │
│  5. Recommended Regression Test Selection & Markdown/JSON Export      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   DETERMINISTIC GUARDRAILS FIREWALL                    │
│  • Pre-Model Input Scope Checks    • Retrieval-Sufficiency Thresholds  │
│  • AI Output Acceptance Validator  • Hallucination Decline Heuristics  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Subsystems

### 3.1 Repository Ingestion & Vector Retrieval
- **AST & Chunk Parsing (`ingestion/chunking.py`, `codeimpact/repository.py`)**: Traverses supported source code (`.py`, `.js`, `.ts`, `.tsx`, `.json`, `.md`), skips generated artifacts (`.venv`, `node_modules`, binaries, `.git`), and divides files into overlapping structural chunks with explicit line-number references.
- **Local Embeddings (`ingestion/embeddings.py`, `codeimpact/retrieval.py`)**: Uses Ollama's `nomic-embed-text` model to embed source chunks locally without external network exposure.
- **Storage**: Persistent JSON vectors (`data/index.json`) for RepoPilot baseline queries, paired with ChromaDB vector storage for CodeImpact.

### 3.2 CodeImpact Change Intelligence Engine
- **Input Modalities**:
  1. *Describe*: Freeform natural-language prompt or proposed patch snippet.
  2. *Paste Diff*: Standard Unified Git diff.
  3. *Select File*: Choose existing repository file from the active project.
  4. *Git Changes*: Automatic comparison of working tree (staged, unstaged, untracked) against `HEAD`.
- **Hybrid Blast Radius Resolution**:
  - **Deterministic AST Graph (`codeimpact/graph.py`)**: Traces direct imports, indirect consumer chains, API route mappings, and symbol references.
  - **Semantic Retrieval**: Queries the vector store for semantic similarity (e.g., related test fixtures or documentation).
- **Conservative Risk Scoring**:
  - `HIGH`: Components touching authentication, session management, billing, migrations, public API endpoints, or possessing large downstream fan-outs.
  - `MEDIUM`: Standard application logic, utility modules, and domain helpers.
  - `LOW`: Isolated unit tests, documentation, or static style assets.
- **Evidence-Grounded AI Review (`codeimpact/engine.py`)**: Code Llama synthesizes findings *only* when supported by retrieved chunk citations; hallucinations or invalid citations are intercepted.

### 3.3 Multi-Model Benchmark Suite & Oscilloscope
- **Evaluated Models**: `codellama`, `starcoder2`, and `qwen2.5-coder`.
- **Benchmark Scale**: 24 standardized software engineering questions evaluated under identical conditions (code explanation, dependency tracing, bug detection, RAG retrieval).
- **Tracked Metrics**:
  - **Accuracy** (Ground-truth alignment)
  - **Relevance** (Semantic cosine similarity of response)
  - **Latency** (Inference elapsed time in seconds)
  - **Tokens** (Prompt + generated token efficiency)
  - **Hallucination Rate** (Ungrounded assertions)
  - **Test Pass Rate** (Code generation acceptance)
- **Interactive Oscilloscope**:
  - 5 Segmented tabs (`ACCURACY`, `RELEVANCE`, `LATENCY`, `TOKENS`, `HALLUCINATION`).
  - Smooth Bezier splines with real-time `requestAnimationFrame` lerp interpolation.
  - Vertical tracking cursor with individual glowing halos for CodeLlama (`#818cf8`), StarCoder2 (`#38bdf8`), and Qwen2.5 (`#fbd509`).
  - Interactive legend with dynamic model metric readouts.

### 3.4 Zero-Trust Guardrails & Acceptance Testing
- **Pre-Model Input Firewall**: Inspects queries prior to invoking local LLMs; unsupported queries (out-of-domain, non-code requests) are refused deterministically to save GPU/CPU cycles.
- **Retrieval Sufficiency**: Rejects generation when semantic similarity scores fall below confidence thresholds.
- **AI Output Validation**: Verifies generated advice against structural acceptance rules and decline heuristics.
- **Audited Metrics**:
  - Expected decisions passed: `11/12`
  - False acceptance rate: `0/6` (100% of unsupported requests refused)
  - False refusal rate: `1/6`
  - Pre-model blocks: `6/6` (100% of refused requests halted before LLM)
  - Output checks passed: `7/7`

### 3.5 Motion UI Visual Platform
- Styled to mirror **[Motion.dev](https://motion.dev/ui)** aesthetics:
  - **Canvas Hero**: 60 FPS HTML5 ASCII vector flow field with procedural curl wave equations responding to pointer velocity and wake turbulence.
  - **Color Palette**: Deep obsidian backgrounds (`#06080d`, `#0b0f19`), Motion Vibrant Yellow (`#fbd509`), electric cyan, and purple accents.
  - **Dev-Tool Plus-Terminals**: Window-frame cards with macOS dots (`dot-r`, `dot-y`, `dot-g`), file path headers, and live radar scan badges.
  - **Sticky Topbar**: Starts transparent over the hero and smoothly morphs to dark blurred frosted obsidian glass (`.scrolled`) when scrolling through content.

---

## 4. Service Topology & Ports

| Service Name | Port | Technology | Purpose |
| :--- | :--- | :--- | :--- |
| **Motion Dashboard** | `5050` | Flask, HTML5, Canvas, CSS | Unified single-page platform (Telemetry, Q&A, Impact, Benchmarks, Guardrails) |
| **CodeImpact Fast API** | `5070` | FastAPI, React / Vite, Uvicorn | Standalone change analyzer API, Vite UI, and background worker queue |
| **RepoPilot Ingestion** | `5001` | Flask, Gunicorn | Chunking, nomic-embed embeddings, and index persistence |
| **RepoPilot LLM App** | `5000` | Flask, Gunicorn | RAG completion generation and multi-model query router |
| **Host Ollama Engine** | `11434` | Ollama (Host) | Local inference for CodeLlama, StarCoder2, Qwen2.5, and nomic-embed |

---

## 5. Repository Structure

```
RepoPilot/
├── codeimpact/                         # Change Impact Intelligence Engine
│   ├── api.py                          # FastAPI service, job queue, watcher
│   ├── engine.py                       # Impact graph merger & AI review logic
│   ├── graph.py                        # Python AST & JS/TS dependency parser
│   ├── repository.py                   # Bounded repo traversal, git diff reader
│   ├── retrieval.py                    # ChromaDB vector store & BM25 retrieval
│   ├── cli.py                          # Command-line interface for CI & terminals
│   ├── evaluate.py                     # Precision/Recall benchmark harness
│   ├── frontend/                       # React + Vite studio application
│   └── tests/                          # Test suite for impact engine
│
├── dashboard/                          # Unified Motion UI Dashboard Platform
│   ├── app.py                          # Flask backend, telemetry provider, API
│   ├── static/                         # Legacy assets and script bundles
│   └── templates/
│       └── index.html                  # Master Motion UI template (Hero, Q&A, Oscilloscope)
│
├── evaluation/                         # Multi-Model Benchmark Suite
│   ├── results.json                    # 24-question empirical raw results
│   ├── guardrail_results.json          # Exercise 5 firewall test evidence
│   ├── AI_OUTPUT_TEST_RESULTS.json     # Acceptance policy evaluations
│   └── analyze_results.py              # Aggregation and category winner rankings
│
├── ingestion/                          # RepoPilot Ingestion Microservice
│   ├── chunking.py                     # Overlapping code chunk generator
│   ├── embeddings.py                   # nomic-embed-text Ollama bridge
│   └── vectorstore.py                  # JSON vector index serialization
│
├── app/                                # RepoPilot Core LLM Microservice
│   ├── llm.py                          # Local LLM completion provider
│   ├── rag.py                          # Context grounding and prompt synthesis
│   └── guardrails.py                   # Input and output validation checks
│
├── data/
│   ├── codeimpact_demo/                # Executable fixture repository (auth, checkout, etc.)
│   └── sample_repo/                    # Baseline test repository
│
├── .github/workflows/
│   └── codeimpact.yml                  # PR Change Impact bot workflow
│
├── docker-compose.yml                  # 4-Service container deployment
├── CODEIMPACT.md                       # Quickstart and CLI manual
└── MASTER_DOCUMENTATION.md             # This comprehensive master file
```

---

## 6. Getting Started & Operations

### 6.1 Prerequisites
- **Docker Desktop** (running on host)
- **Ollama** installed on host with required models:
  ```powershell
  ollama pull codellama
  ollama pull nomic-embed-text
  ollama pull starcoder2
  ollama pull qwen2.5-coder
  ```

### 6.2 Launch via Docker Compose (Recommended)
From PowerShell in the project root:
```powershell
docker compose up -d
```
- Open **http://localhost:5050/** to access the unified Motion UI dashboard.
- Services start with volume mounts; code edits reflect immediately (restart containers after template modifications if caching is active).

### 6.3 Standalone CodeImpact Service
To start the dedicated FastAPI + React service on port 5070:
```powershell
powershell -ExecutionPolicy Bypass -File codeimpact/start.ps1
```

### 6.4 CLI Usage
Run change impact analysis directly from your terminal:
```powershell
# Analyze working tree git changes against HEAD without calling LLM:
python -m codeimpact.cli --repo . --git --no-llm

# Analyze a specific modified file with full AI review:
python -m codeimpact.cli --repo . --file app/llm.py --description "Upgrade model parameters"

# Run traced regression tests automatically:
python -m codeimpact.cli --repo . --git --run-tests
```

---

## 7. API Specification

### Unified Dashboard & Telemetry (`:5050`)
- `GET /`: Serves the primary Motion UI dashboard.
- `GET /api/benchmark/series`: Returns 24-point evaluation curves across all models for `accuracy`, `relevance`, `latency`, `tokens`, and `hallucination`.
- `POST /api/query`: Submits a Code Q&A prompt to all models simultaneously.
- `POST /api/impact/analyze`: Submits a change description or diff to the impact engine.
- `GET /api/reports`: Lists historical persisted impact reports.
- `GET /api/reports/{id}`: Retrieves complete JSON impact report.
- `GET /api/reports/{id}/markdown`: Downloads report as standard Markdown.

### CodeImpact FastAPI Service (`:5070`)
- `POST /api/analyze`: Queues asynchronous impact analysis job.
- `GET /api/jobs/{id}`: Polls analysis job status and progress.
- `POST /api/watch`: Toggles automatic filesystem watcher on/off.
- `GET /api/overview`: Returns target repository file counts, test ratios, and token estimates.

---

## 8. CI/CD & GitHub Actions Integration

The repository includes a production-ready workflow in [`.github/workflows/codeimpact.yml`](.github/workflows/codeimpact.yml):
1. **Trigger**: Runs automatically on Pull Requests to `main` and manual workflow dispatches.
2. **Analysis**: Evaluates the incoming Git diff against the base branch.
3. **Test Tracing**: Detects and executes affected Python test files using `pytest`.
4. **Pull Request Bot**: Posts an evidence-grounded Change Impact Report directly as a PR comment with risk badges, affected components, and recommended testing checklists.

---

## 9. Empirical Evaluation Findings

From our audited 24-question benchmark run recorded in [`evaluation/results.json`](evaluation/results.json):

| Model | Accuracy | Relevance | Avg Latency | Avg Tokens | Hallucination Rate | Test Pass Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Qwen2.5 Coder** | **70.8%** | 0.795 | 5.58 s | **665.0** | 33.3% | **66.7%** |
| **Code Llama** | 63.9% | **0.798** | 5.47 s | 879.5 | **16.7%** | 33.3% |
| **StarCoder2** | 50.0% | 0.606 | **5.09 s** | 891.0 | **16.7%** | 0.0% |

### Key Takeaways:
- **Accuracy Leader**: `Qwen2.5 Coder` achieved the highest accuracy (70.8%) and lowest token footprint (665 tokens/query).
- **Grounding Leader**: `Code Llama` and `StarCoder2` tied for the lowest hallucination rate (16.7%), demonstrating superior adherence to retrieved RAG evidence.
- **Speed Leader**: `StarCoder2` exhibited the lowest inference latency (5.09s), though at the cost of reasoning accuracy on complex tasks.

---

## 10. Design Boundaries & Safety Guarantees

1. **Read-Only Guarantees**: The analyzer mounts target repositories read-only. It never modifies user code, never commits patches automatically, and never runs untested code via the Web API.
2. **Deterministic Risk Separation**: Risk classifications (`High`, `Medium`, `Low`) are generated by transparent AST heuristic rules, never opaque LLM guesses. AI suggestions are explicitly cited and marked separately.
3. **Local Privacy**: All embeddings and model inferences run completely on the host Ollama runtime; no source code or prompts leave the developer's local environment.
4. **Citation Integrity**: The LLM review prompt enforces strict evidence IDs; assertions lacking source citations are pruned before presentation.

---

*Authored by the CodeImpact AI / RepoPilot Engineering Team.*
