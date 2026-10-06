# RepoPilot completion plan and task status

This plan covers the existing application through Week 4 and the guardrail/output-testing exercise that follows it. All work is local; no commit or push is part of this plan.

## Completed tasks

- [x] Verify the local Python environment, Ollama, embedding model, three code models, vector index, and service health.
- [x] Preserve one application, knowledge base, prompt construction, and evaluation conditions across models.
- [x] Complete the Week 3 RAG-versus-no-RAG experiment with quantitative retrieval, accuracy, and grounding analysis.
- [x] Use one 24-question dataset across seven software-engineering categories and all three models.
- [x] Capture correctness, relevance, retrieval quality, hallucination, generated-code test results, latency, tokens, client resources, Ollama resources, and GPU resources.
- [x] Run all 72 model-question combinations successfully and checkpoint results after every response.
- [x] Produce category-wise quantitative winners and quality/latency/resource trade-off analysis.
- [x] Produce question → retrieved context → response RAG-pipeline traces, including retrieval and generation failures.
- [x] Evaluate five repository-level, multi-file questions and document current vector-RAG limitations.
- [x] Add deterministic input guardrails for scope, safety, prompt injection, length, model allow-list, and retrieval depth.
- [x] Add retrieval guardrails that require similarity and lexical evidence before model generation.
- [x] Add generated-output checks for emptiness, length, relevance, unsupported file/function claims, and insufficiency signals.
- [x] Prevent direct external context from bypassing trusted retrieval.
- [x] Measure guardrail effectiveness on 17 cases, including canonical multi-file questions, and record without/with-guardrail examples.
- [x] Add ten deterministic AI-output acceptance tests with explicit pass/fail criteria, including format, unsupported relationships, and unsupported cross-component workflow checks.
- [x] Add a controlled lower-k RAG trace that demonstrates important context being missed.
- [x] Expose Week 4, RAG, repository, guardrail, and output-test reports in the dashboard.
- [x] Update the CLI orchestrator and documentation for the guarded API flow.
- [x] Run unit tests, compilation checks, live API checks, CLI smoke tests, and dashboard rendering checks.

## Reproduction sequence

1. Start Ollama and confirm `codellama`, `starcoder2`, `qwen2.5-coder`, and `nomic-embed-text`.
2. Start ingestion on port 5001, the guarded app on port 5000, and the dashboard on port 5050.
3. Run `python evaluation/run_evaluation.py` and `python evaluation/analyze_results.py`.
4. Run `python exercise3_rag_comparison.py`, `python evaluation/rag_pipeline_analysis.py`, and `python evaluation/multi_file_questions.py`.
5. Run `python evaluation/run_guardrail_evaluation.py` and `python evaluation/run_output_tests.py`.
6. Run `python -m unittest discover -s tests -v` and verify all service health endpoints.
7. Open `http://127.0.0.1:5050/` and test supported, insufficient-evidence, and out-of-scope questions.
