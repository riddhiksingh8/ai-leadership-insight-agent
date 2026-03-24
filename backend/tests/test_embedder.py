"""
Tests for src/embedder.py

Covers:
- _folder_fingerprint: determinism, changes on file modification
- VectorStore.build: embeds chunks, creates VectorEntry objects, writes cache
- VectorStore.build: cache hit avoids re-embedding
- VectorStore.search: returns top-k, ordering by similarity, handles edge cases
- Embedding normalisation (unit vectors)
"""

import pickle
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from src.document_loader import DocumentChunk
from src.embedder import CACHE_FILE, VectorEntry, VectorStore


# ── helpers ────────────────────────────────────────────────────────────────

def _make_unit_vector(dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def _mock_model(embeddings: np.ndarray):
    """Return a mock SentenceTransformer that yields *embeddings* on encode()."""
    model = MagicMock()
    model.encode.return_value = embeddings
    return model


# ── _folder_fingerprint ────────────────────────────────────────────────────

class TestFolderFingerprint:
    def test_returns_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = VectorStore._folder_fingerprint(tmp)
            assert isinstance(fp, str)

    def test_empty_folder_gives_empty_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = VectorStore._folder_fingerprint(tmp)
            assert fp == ""

    def test_deterministic_for_same_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("hello", encoding="utf-8")
            fp1 = VectorStore._folder_fingerprint(tmp)
            fp2 = VectorStore._folder_fingerprint(tmp)
            assert fp1 == fp2

    def test_changes_when_file_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp_before = VectorStore._folder_fingerprint(tmp)
            Path(tmp, "new.txt").write_text("content", encoding="utf-8")
            fp_after = VectorStore._folder_fingerprint(tmp)
            assert fp_before != fp_after

    def test_changes_when_file_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, "doc.txt")
            p.write_text("original", encoding="utf-8")
            fp1 = VectorStore._folder_fingerprint(tmp)
            p.write_text("modified content that is longer", encoding="utf-8")
            fp2 = VectorStore._folder_fingerprint(tmp)
            assert fp1 != fp2

    def test_includes_filename_in_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "alpha.txt").write_text("x", encoding="utf-8")
            fp = VectorStore._folder_fingerprint(tmp)
            assert "alpha.txt" in fp


# ── VectorStore.build ──────────────────────────────────────────────────────

class TestVectorStoreBuild:
    def _fake_embeddings(self, n: int, dim: int = 384) -> np.ndarray:
        rng = np.random.default_rng(0)
        raw = rng.standard_normal((n, dim)).astype(np.float32)
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        return raw / norms

    def test_creates_one_entry_per_chunk(self, sample_chunks):
        store = VectorStore()
        fake_embs = self._fake_embeddings(len(sample_chunks))

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(store, "_embed", return_value=fake_embs):
                store.build(sample_chunks, tmp)

        assert len(store._entries) == len(sample_chunks)

    def test_entry_text_matches_chunk_text(self, sample_chunks):
        store = VectorStore()
        fake_embs = self._fake_embeddings(len(sample_chunks))

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(store, "_embed", return_value=fake_embs):
                store.build(sample_chunks, tmp)

        for entry, chunk in zip(store._entries, sample_chunks):
            assert entry.text == chunk.text
            assert entry.source == chunk.source
            assert entry.chunk_index == chunk.chunk_index

    def test_cache_file_written_after_build(self, sample_chunks):
        store = VectorStore()
        fake_embs = self._fake_embeddings(len(sample_chunks))

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(store, "_embed", return_value=fake_embs):
                store.build(sample_chunks, tmp)

            cache_path = Path(tmp) / CACHE_FILE
            assert cache_path.exists()

    def test_cache_hit_skips_embed(self, sample_chunks):
        store = VectorStore()
        fake_embs = self._fake_embeddings(len(sample_chunks))

        # Use a single persistent temp dir so both builds see the same path
        with tempfile.TemporaryDirectory() as tmp:
            # First build — embeds and writes cache
            with patch.object(store, "_embed", return_value=fake_embs) as mock_embed:
                store.build(sample_chunks, tmp)
            assert mock_embed.call_count == 1

            # Second build on a fresh store — should load from cache, skip _embed
            store2 = VectorStore()
            with patch.object(store2, "_embed", return_value=fake_embs) as mock_embed2:
                store2.build(sample_chunks, tmp)
                mock_embed2.assert_not_called()

            assert len(store2._entries) == len(sample_chunks)

    def test_cache_miss_when_folder_changes(self, sample_chunks):
        store = VectorStore()
        fake_embs = self._fake_embeddings(len(sample_chunks))

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(store, "_embed", return_value=fake_embs):
                store.build(sample_chunks, tmp)

            # Add a new file to invalidate cache
            Path(tmp, "newfile.txt").write_text("new content", encoding="utf-8")

            store2 = VectorStore()
            with patch.object(store2, "_embed", return_value=fake_embs) as mock_embed2:
                store2.build(sample_chunks, tmp)
                mock_embed2.assert_called_once()

    def test_embeddings_stored_as_numpy_arrays(self, sample_chunks):
        store = VectorStore()
        fake_embs = self._fake_embeddings(len(sample_chunks))

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(store, "_embed", return_value=fake_embs):
                store.build(sample_chunks, tmp)

        for entry in store._entries:
            assert isinstance(entry.embedding, np.ndarray)
            assert entry.embedding.ndim == 1


# ── VectorStore.search ─────────────────────────────────────────────────────

class TestVectorStoreSearch:
    def _store_with_entries(self, entries: list[VectorEntry]) -> VectorStore:
        store = VectorStore()
        store._entries = entries
        return store

    def test_empty_store_returns_empty_list(self):
        store = VectorStore()
        with patch.object(store, "_embed", return_value=np.array([[1.0] + [0.0] * 383])):
            results = store.search("anything", top_k=3)
        assert results == []

    def test_returns_at_most_top_k(self, sample_vectors):
        store = self._store_with_entries(sample_vectors)
        query_emb = np.array([sample_vectors[0].embedding])

        with patch.object(store, "_embed", return_value=query_emb):
            results = store.search("revenue", top_k=2)

        assert len(results) <= 2

    def test_returns_all_when_top_k_exceeds_store_size(self, sample_vectors):
        store = self._store_with_entries(sample_vectors)
        query_emb = np.array([sample_vectors[0].embedding])

        with patch.object(store, "_embed", return_value=query_emb):
            results = store.search("any query", top_k=100)

        assert len(results) == len(sample_vectors)

    def test_most_similar_chunk_ranked_first(self, sample_vectors):
        """Query with an embedding identical to entry[1] → entry[1] should rank first."""
        store = self._store_with_entries(sample_vectors)
        target_emb = sample_vectors[1].embedding
        query_emb = np.array([target_emb])

        with patch.object(store, "_embed", return_value=query_emb):
            results = store.search("cloud revenue", top_k=3)

        assert results[0].text == sample_vectors[1].text

    def test_results_are_vector_entry_objects(self, sample_vectors):
        store = self._store_with_entries(sample_vectors)
        query_emb = np.array([sample_vectors[0].embedding])

        with patch.object(store, "_embed", return_value=query_emb):
            results = store.search("revenue", top_k=2)

        assert all(isinstance(r, VectorEntry) for r in results)

    def test_search_with_top_k_1(self, sample_vectors):
        store = self._store_with_entries(sample_vectors)
        query_emb = np.array([sample_vectors[2].embedding])

        with patch.object(store, "_embed", return_value=query_emb):
            results = store.search("AI strategy", top_k=1)

        assert len(results) == 1
        assert results[0].text == sample_vectors[2].text

    def test_similarity_scores_are_descending(self, sample_vectors):
        """Scores from dot-product should be non-increasing across results."""
        store = self._store_with_entries(sample_vectors)
        query_emb = np.array([sample_vectors[0].embedding])

        with patch.object(store, "_embed", return_value=query_emb):
            results = store.search("question", top_k=len(sample_vectors))

        # Compute scores manually and verify ordering
        scores = [float(query_emb[0] @ r.embedding) for r in results]
        assert scores == sorted(scores, reverse=True)


# ── embedding normalisation ────────────────────────────────────────────────

class TestEmbedNormalisation:
    def test_output_vectors_are_unit_length(self, sample_chunks):
        """_embed must produce L2-normalised vectors so cosine sim = dot product."""
        raw_output = np.array([
            [3.0, 4.0] + [0.0] * 382,   # norm = 5 → should become [0.6, 0.8, ...]
            [1.0, 0.0] + [0.0] * 382,   # already unit
        ], dtype=np.float32)

        store = VectorStore()
        mock_model = MagicMock()
        mock_model.encode.return_value = raw_output

        with patch.object(store, "_get_model", return_value=mock_model):
            result = store._embed(["text a", "text b"])

        norms = np.linalg.norm(result, axis=1)
        np.testing.assert_allclose(norms, np.ones(len(norms)), atol=1e-5)

    def test_zero_vector_does_not_cause_division_error(self):
        """A zero embedding vector (degenerate case) should not raise."""
        zero_output = np.zeros((1, 384), dtype=np.float32)
        store = VectorStore()
        mock_model = MagicMock()
        mock_model.encode.return_value = zero_output

        with patch.object(store, "_get_model", return_value=mock_model):
            result = store._embed(["empty"])   # should not raise

        assert result.shape == (1, 384)
