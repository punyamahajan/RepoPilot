# CodeImpact implementation plan and acceptance checks

Proposal scope: preserve the RepoPilot application and add repository-wide change analysis using React, FastAPI, LangChain, Ollama/Code Llama, Chroma, Docker, evaluation, and optional CI automation.

1. Repository intake: read supported source/tests/docs, honor ignored files, reject traversal/symlinks, create line-addressable chunks, capture staged/unstaged/untracked/deleted changes.
2. Impact mapping: build Python import/call relationships, JS/TS import patterns, API route metadata and literal file references; traverse every reachable consumer; retain old edges for deletions.
3. Semantic retrieval: cache content-addressed Ollama embeddings in Chroma, remove stale chunks, retrieve relevant evidence; keep a measurable keyword baseline.
4. Reasoned reports: classify review priority, attach dependency paths and sources, recommend existing tests and mitigations; constrain LLM output to cited files/evidence; report failures and uncertainty.
5. Product/API: React impact map, change inputs, file inspection, tests/fixes, AI reasoning, citations, export, report history, observable jobs, and opt-in watcher.
6. Operations: isolated Docker service plus startup instructions; CLI with optional trusted test execution; PR analysis/artifact/comment workflow.
7. Validation: existing tests, focused graph/Git/API/output validation tests, executable demo tests, frontend build/browser checks, real local embeddings/generation, ten-case precision/recall/F1 benchmark.

Out of scope for guarantees: compiler-complete analysis of every language, dynamic runtime dependencies, automatic remediation, public multi-user hosting, and claiming every possible impact can be known statically.
