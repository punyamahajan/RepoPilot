# RepoPilot Lab

## Structure
```
app/                       <- Person A
ingestion/                 <- Person B
data/sample_repo/          <- demo repo to index
integration_test.py
exercise3_rag_comparison.py
requirements.txt
```

## How to run

```
pip install -r requirements.txt
ollama pull codellama
ollama pull nomic-embed-text
ollama serve
```

Then, from repo root:

```
python integration_test.py
python exercise3_rag_comparison.py
```

Report saved to `reports/exercise3_rag_vs_no_rag.md`.

## Status

**Week 3**
- Ex.1 — App + Ollama: ✅ Done
- Ex.2 — Knowledge Base: ✅ Done
- Ex.3 — Retrieval + RAG: ✅ Done
- Ex.4 — Services/Orchestration: ❌ Not done
- Ex.5 — Docker: ❌ Not done

**Week 4**
- Ex.1 — Multi-model eval: ❌ Not done
- Ex.2 — Eval dataset: ❌ Not done
- Ex.3 — Quantitative eval: ❌ Not done
- Ex.4 — Results analysis: ❌ Not done
- Ex.5 — RAG pipeline analysis: ❌ Not done
- Ex.6 — Repo-level understanding: ❌ Not done