"""Persistent Chroma vectors, Ollama embeddings, and a transparent lexical baseline."""

import hashlib
import math
import os
import re

import requests


def tokens(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    return set(re.findall(r'[a-z][a-z0-9]{2,}', text.lower().replace('_', ' '))) - {
        'the', 'and', 'for', 'from', 'with', 'this', 'that', 'return', 'import', 'change', 'def'}


def lexical_search(query, chunks, k=12):
    terms = tokens(query)
    scored = []
    for chunk in chunks:
        found = tokens(chunk['file'] + ' ' + chunk['text'])
        overlap = terms & found
        if overlap:
            score = len(overlap) / math.sqrt(max(len(terms) * len(found), 1))
            scored.append({**chunk, 'score': round(score, 4), 'retrieval': 'keyword'})
    return sorted(scored, key=lambda c: (-c['score'], c['file'], c['start']))[:k]


class SemanticIndex:
    def __init__(self, directory, repository_id):
        import chromadb
        self.model = os.getenv('CODEIMPACT_EMBED_MODEL', 'nomic-embed-text')
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
        client = chromadb.PersistentClient(path=str(directory))
        model_hash = hashlib.sha256(self.model.encode()).hexdigest()[:10]
        self.collection = client.get_or_create_collection(
            f'repo-{repository_id}-{model_hash}', metadata={'hnsw:space': 'cosine'}, embedding_function=None)

    def embed(self, texts):
        response = requests.post(f'{self.base_url}/api/embed', json={
            'model': self.model, 'input': texts, 'truncate': True, 'keep_alive': '5m'}, timeout=180)
        response.raise_for_status()
        vectors = response.json().get('embeddings', [])
        if len(vectors) != len(texts) or any(not vector for vector in vectors):
            raise ValueError('Ollama did not return one embedding per chunk.')
        return vectors

    def sync(self, chunks, progress=lambda value: None):
        existing = set(self.collection.get(include=[])['ids'])
        wanted = {c['id'] for c in chunks}
        pending = [c for c in chunks if c['id'] not in existing]
        for start in range(0, len(pending), 12):
            batch = pending[start:start + 12]
            vectors = self.embed([f"{c['file']} {c['symbol']}\n{c['text']}" for c in batch])
            self.collection.upsert(ids=[c['id'] for c in batch], embeddings=vectors,
                                   documents=[c['text'] for c in batch],
                                   metadatas=[{k: c[k] for k in ('file', 'start', 'end', 'symbol', 'kind')} for c in batch])
            progress(f'Embedded {min(start + 12, len(pending))}/{len(pending)} changed chunks')
        if existing - wanted:
            self.collection.delete(ids=sorted(existing - wanted))
        return {'chunks': len(chunks), 'embedded': len(pending), 'cached': len(wanted & existing), 'model': self.model}

    def search(self, query, k=12):
        if not self.collection.count():
            return []
        result = self.collection.query(query_embeddings=self.embed([query]),
                                       n_results=min(k, self.collection.count()),
                                       include=['documents', 'metadatas', 'distances'])
        return [{**meta, 'id': cid, 'text': text, 'score': round(1 - distance, 4), 'retrieval': 'semantic'}
                for cid, meta, text, distance in zip(result['ids'][0], result['metadatas'][0],
                                                     result['documents'][0], result['distances'][0])]
