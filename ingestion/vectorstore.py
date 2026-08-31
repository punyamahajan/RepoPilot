"""
vectorstore.py
--------------
Person B — Week 3, Exercise 2 (part 3): Vector Representation + storage,
and the retrieval half of "Vector Similarity" that Exercise 3 needs.

A minimal in-memory vector store with cosine-similarity search — no
external vector DB required, keeps the ingestion pipeline dependency-
light (just numpy). This is enough to satisfy the brief's pipeline;
swap in Chroma later only if you want to show a "real" vector DB.

IMPORTANT — interface contract with Person C:
    build_index(repo_path) -> VectorStore
    load_index(path)       -> VectorStore
    vectorstore.similarity_search(query: str, k: int) -> list[str]

This matches stub_vectorstore.py exactly, so Person C's retrieval.py
needs ZERO code changes beyond swapping the import line.
"""

import json
import os
import numpy as np

from chunking import chunk_repo
from embeddings import get_embedding, get_embeddings_batch


class VectorStore:
    def __init__(self):
        self.chunks = []       # [{"file": ..., "chunk_id": ..., "text": ...}, ...]
        self.vectors = None    # numpy array, shape (n_chunks, embedding_dim)

    def add(self, chunks: list, embed_model: str = "nomic-embed-text"):
        texts = [c["text"] for c in chunks]
        vecs = get_embeddings_batch(texts, model=embed_model)
        self.chunks.extend(chunks)
        new_vecs = np.array(vecs, dtype=np.float32)
        self.vectors = new_vecs if self.vectors is None else np.vstack([self.vectors, new_vecs])

    def similarity_search(self, query: str, k: int = 3) -> list:
        """
        Query -> embedding -> cosine similarity against every stored chunk
        -> top-k chunk texts, each prefixed with its source file (so
        Person A's/C's citation requirement — file + line/chunk — is easy
        to satisfy downstream).
        """
        if self.vectors is None or len(self.chunks) == 0:
            return []
        query_vec = np.array(get_embedding(query), dtype=np.float32)
        sims = self._cosine_sim(query_vec, self.vectors)
        top_k_idx = np.argsort(sims)[::-1][:k]
        results = []
        for idx in top_k_idx:
            c = self.chunks[idx]
            results.append(f"{c['file']} (chunk {c['chunk_id']}):\n{c['text']}")
        return results

    @staticmethod
    def _cosine_sim(query_vec, matrix):
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8)
        return matrix_norm @ query_norm

    def save(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "chunks": self.chunks,
                "vectors": self.vectors.tolist() if self.vectors is not None else [],
            }, f)

    @classmethod
    def load(cls, path: str) -> "VectorStore":
        vs = cls()
        with open(path, "r") as f:
            data = json.load(f)
        vs.chunks = data["chunks"]
        vs.vectors = np.array(data["vectors"], dtype=np.float32) if data["vectors"] else None
        return vs


def build_index(repo_path: str, save_path: str = "../data/index.json", embed_model: str = "nomic-embed-text") -> VectorStore:
    """
    Documents -> Chunking -> Embeddings -> Vector Representation, in one call.
    This is Person B's headline deliverable for Exercise 2.
    """
    print(f"Walking and chunking {repo_path}...")
    chunks = chunk_repo(repo_path)
    print(f"Found {len(chunks)} chunks. Embedding with {embed_model}...")

    vs = VectorStore()
    vs.add(chunks, embed_model=embed_model)

    vs.save(save_path)
    print(f"Index built and saved to {save_path}")
    return vs


def load_index(path: str = "../data/index.json") -> VectorStore:
    """Loads a previously built index. Same name Person C's stub already expects."""
    return VectorStore.load(path)


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "../data/sample_repo"
    vs = build_index(repo)
    print("\nTest query: 'authentication login'")
    for r in vs.similarity_search("authentication login", k=3):
        print("\n---\n", r)