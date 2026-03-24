"""
Shared pytest fixtures.
"""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.document_loader import DocumentChunk
from src.embedder import VectorEntry


# ── temp documents folder ──────────────────────────────────────────────────

@pytest.fixture
def docs_dir():
    """A temporary directory pre-populated with sample .txt documents."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "report_q1.txt").write_text(
            "Revenue grew 12% year-over-year in Q1. "
            "The cloud segment was the fastest growing at 25%. "
            "Operating margin improved to 18% from 15%.",
            encoding="utf-8",
        )
        Path(tmp, "strategy_note.txt").write_text(
            "Our 2025 strategy focuses on AI-first product development. "
            "We plan to enter three new geographic markets: Japan, Brazil, and India. "
            "R&D investment will increase by 20% to $500 million.",
            encoding="utf-8",
        )
        yield tmp


@pytest.fixture
def sample_chunks():
    """A small list of DocumentChunks for use in embedder/agent tests."""
    return [
        DocumentChunk(
            text="Revenue grew 12% year-over-year.",
            source="report_q1.txt",
            chunk_index=0,
            total_chunks=1,
        ),
        DocumentChunk(
            text="Cloud segment revenue increased by 25%.",
            source="report_q1.txt",
            chunk_index=1,
            total_chunks=2,
        ),
        DocumentChunk(
            text="Our strategy focuses on AI-first product development.",
            source="strategy_note.txt",
            chunk_index=0,
            total_chunks=1,
        ),
    ]


@pytest.fixture
def sample_vectors(sample_chunks):
    """Pre-built VectorEntry list with random normalised embeddings."""
    rng = np.random.default_rng(42)
    entries = []
    for chunk in sample_chunks:
        raw = rng.standard_normal(384).astype(np.float32)
        emb = raw / np.linalg.norm(raw)
        entries.append(
            VectorEntry(
                text=chunk.text,
                source=chunk.source,
                chunk_index=chunk.chunk_index,
                total_chunks=chunk.total_chunks,
                embedding=emb,
            )
        )
    return entries


@pytest.fixture(autouse=True)
def _no_real_api_key(monkeypatch):
    """Prevent tests from accidentally using a real API key."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-key")
