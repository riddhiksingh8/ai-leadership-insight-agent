"""
Embedder: encodes text chunks using a local sentence-transformers model
and stores them in a simple in-memory vector store with cosine similarity search.
"""

from __future__ import annotations

import json
import os
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from src.document_loader import DocumentChunk


CACHE_FILE = ".vector_store.pkl"
MODEL_NAME = "all-MiniLM-L6-v2"   # ~80 MB, fast, good quality


@dataclass
class VectorEntry:
    text: str
    source: str
    chunk_index: int
    total_chunks: int
    embedding: np.ndarray


class VectorStore:
    """
    In-memory vector store backed by a local pickle cache.

    The cache is keyed by a fingerprint of the document folder's
    mtime/size so it is automatically invalidated when files change.
    """

    def __init__(self) -> None:
        self._entries: list[VectorEntry] = []
        self._model = None   # lazy-loaded

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"  Loading embedding model '{MODEL_NAME}'...")
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        model = self._get_model()
        embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return embeddings / norms

    # ------------------------------------------------------------------
    # Build / cache
    # ------------------------------------------------------------------

    @staticmethod
    def _folder_fingerprint(folder: str) -> str:
        """A simple fingerprint based on filenames + sizes + mtimes."""
        items = []
        for p in sorted(Path(folder).iterdir()):
            if p.is_file() and p.name != CACHE_FILE:   # exclude the cache itself
                stat = p.stat()
                items.append(f"{p.name}:{stat.st_size}:{stat.st_mtime:.0f}")
        return "|".join(items)

    def build(self, chunks: list["DocumentChunk"], folder: str) -> None:
        """Embed all chunks and cache the result to disk."""
        cache_path = Path(folder) / CACHE_FILE
        fingerprint = self._folder_fingerprint(folder)

        # Try to load from cache
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    cached = pickle.load(f)
                if cached.get("fingerprint") == fingerprint:
                    self._entries = cached["entries"]
                    print(f"  Loaded {len(self._entries)} vectors from cache.")
                    return
            except Exception:
                pass  # Cache corrupt or version mismatch — rebuild

        print(f"  Embedding {len(chunks)} chunks...")
        texts = [c.text for c in chunks]
        embeddings = self._embed(texts)

        self._entries = [
            VectorEntry(
                text=chunk.text,
                source=chunk.source,
                chunk_index=chunk.chunk_index,
                total_chunks=chunk.total_chunks,
                embedding=embeddings[i],
            )
            for i, chunk in enumerate(chunks)
        ]

        # Save cache
        try:
            with open(cache_path, "wb") as f:
                pickle.dump({"fingerprint": fingerprint, "entries": self._entries}, f)
            print(f"  Cached {len(self._entries)} vectors.")
        except Exception as e:
            print(f"  [warn] Could not write cache: {e}")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 6) -> list[VectorEntry]:
        """Return the top-k most similar chunks to the query."""
        if not self._entries:
            return []

        query_emb = self._embed([query])[0]           # (dim,)
        matrix = np.stack([e.embedding for e in self._entries])  # (N, dim)
        scores = matrix @ query_emb                   # cosine similarity (already normalized)

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [self._entries[i] for i in top_indices]
