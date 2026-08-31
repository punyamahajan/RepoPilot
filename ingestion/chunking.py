"""
chunking.py
------------
Person B — Week 3, Exercise 2 (part 1): Documents -> Chunking

Walks a target repository, filters to code-relevant files, and splits
each file into overlapping text chunks ready for embedding.
"""

import os

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".rs",
    ".md", ".json", ".yml", ".yaml",
}

SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}


def walk_repo(repo_path: str) -> list:
    """Returns [(file_path, file_text), ...] for every code-relevant file in the repo."""
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1]
            if ext in CODE_EXTENSIONS:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    if text.strip():
                        files.append((fpath, text))
                except Exception:
                    continue
    return files


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    """Splits text into overlapping chunks of ~chunk_size characters."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def chunk_repo(repo_path: str, chunk_size: int = 800, overlap: int = 100) -> list:
    """
    Full Documents -> Chunking step.
    Returns [{"file": rel_path, "chunk_id": i, "text": chunk}, ...]
    ready to be embedded by embeddings.py.
    """
    all_chunks = []
    for fpath, text in walk_repo(repo_path):
        rel_path = os.path.relpath(fpath, repo_path)
        for i, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
            all_chunks.append({"file": rel_path, "chunk_id": i, "text": chunk})
    return all_chunks


if __name__ == "__main__":
    import sys
    import json
    repo = sys.argv[1] if len(sys.argv) > 1 else "../data/sample_repo"
    chunks = chunk_repo(repo)
    print(f"Found {len(chunks)} chunks from {repo}")
    print(json.dumps(chunks[:2], indent=2))