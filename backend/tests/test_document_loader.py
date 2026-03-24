"""
Tests for src/document_loader.py

Covers:
- _split_into_chunks: edge cases (empty, short, exact, long, overlap)
- load_documents: txt/md loading, unsupported files skipped, empty files skipped,
                  missing folder raises, PDF/DOCX failures handled gracefully
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.document_loader import (
    DocumentChunk,
    _split_into_chunks,
    load_documents,
)


# ── _split_into_chunks ─────────────────────────────────────────────────────

class TestSplitIntoChunks:
    def test_empty_string_returns_no_chunks(self):
        assert _split_into_chunks("") == []

    def test_whitespace_only_returns_no_chunks(self):
        assert _split_into_chunks("   \n\t  ") == []

    def test_single_word(self):
        chunks = _split_into_chunks("hello")
        assert chunks == ["hello"]

    def test_short_text_produces_one_chunk(self):
        text = " ".join(["word"] * 50)
        chunks = _split_into_chunks(text, chunk_size=800, overlap=150)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_exact_chunk_size_produces_one_chunk(self):
        text = " ".join(["word"] * 800)
        chunks = _split_into_chunks(text, chunk_size=800, overlap=150)
        assert len(chunks) == 1

    def test_long_text_produces_multiple_chunks(self):
        text = " ".join(["word"] * 2000)
        chunks = _split_into_chunks(text, chunk_size=800, overlap=150)
        assert len(chunks) > 1

    def test_overlap_means_words_appear_in_consecutive_chunks(self):
        # Build deterministic text: word0, word1, ..., word999
        words = [f"w{i}" for i in range(1000)]
        text = " ".join(words)
        chunks = _split_into_chunks(text, chunk_size=100, overlap=20)

        # The last 20 words of chunk N should appear at the start of chunk N+1
        for i in range(len(chunks) - 1):
            tail = chunks[i].split()[-20:]
            head = chunks[i + 1].split()[:20]
            assert tail == head, f"Overlap missing between chunk {i} and {i+1}"

    def test_each_chunk_no_larger_than_chunk_size(self):
        text = " ".join(["word"] * 3000)
        chunks = _split_into_chunks(text, chunk_size=200, overlap=30)
        for chunk in chunks:
            assert len(chunk.split()) <= 200

    def test_all_words_present_across_chunks(self):
        words = [f"unique_{i}" for i in range(500)]
        text = " ".join(words)
        chunks = _split_into_chunks(text, chunk_size=100, overlap=20)
        combined = " ".join(chunks)
        for word in words:
            assert word in combined

    def test_custom_chunk_size_respected(self):
        text = " ".join(["a"] * 300)
        chunks = _split_into_chunks(text, chunk_size=50, overlap=0)
        assert len(chunks) == 6   # 300 / 50 = 6 exact chunks

    def test_zero_overlap(self):
        text = " ".join([str(i) for i in range(100)])
        chunks = _split_into_chunks(text, chunk_size=10, overlap=0)
        assert len(chunks) == 10
        # No word appears in two consecutive chunks
        for i in range(len(chunks) - 1):
            assert not set(chunks[i].split()) & set(chunks[i + 1].split())


# ── load_documents ─────────────────────────────────────────────────────────

class TestLoadDocuments:
    def test_loads_txt_files(self, docs_dir):
        chunks = load_documents(docs_dir)
        sources = {c.source for c in chunks}
        assert "report_q1.txt" in sources
        assert "strategy_note.txt" in sources

    def test_loads_md_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notes.md").write_text("# Strategy\nGrow revenue by 10%.", encoding="utf-8")
            chunks = load_documents(tmp)
            assert any(c.source == "notes.md" for c in chunks)

    def test_skips_unsupported_file_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "data.csv").write_text("col1,col2\n1,2", encoding="utf-8")
            Path(tmp, "image.png").write_bytes(b"\x89PNG\r\n")
            Path(tmp, "valid.txt").write_text("Some valid content here.", encoding="utf-8")
            chunks = load_documents(tmp)
            sources = {c.source for c in chunks}
            assert "data.csv" not in sources
            assert "image.png" not in sources
            assert "valid.txt" in sources

    def test_skips_empty_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "empty.txt").write_text("", encoding="utf-8")
            Path(tmp, "whitespace.txt").write_text("   \n\t  ", encoding="utf-8")
            chunks = load_documents(tmp)
            sources = {c.source for c in chunks}
            assert "empty.txt" not in sources
            assert "whitespace.txt" not in sources

    def test_missing_folder_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="Documents folder not found"):
            load_documents("/nonexistent/path/to/docs")

    def test_chunk_metadata_is_consistent(self, docs_dir):
        chunks = load_documents(docs_dir)
        by_source: dict[str, list[DocumentChunk]] = {}
        for c in chunks:
            by_source.setdefault(c.source, []).append(c)

        for source, source_chunks in by_source.items():
            expected_total = source_chunks[0].total_chunks
            for i, chunk in enumerate(source_chunks):
                assert chunk.chunk_index == i, f"{source}: wrong chunk_index"
                assert chunk.total_chunks == expected_total, f"{source}: inconsistent total_chunks"

    def test_returns_document_chunk_objects(self, docs_dir):
        chunks = load_documents(docs_dir)
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        for c in chunks:
            assert isinstance(c.text, str) and len(c.text) > 0
            assert isinstance(c.source, str)
            assert isinstance(c.chunk_index, int)
            assert isinstance(c.total_chunks, int)

    def test_pdf_load_failure_is_skipped_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Write a file that is not a valid PDF
            Path(tmp, "broken.pdf").write_bytes(b"not a real pdf")
            Path(tmp, "valid.txt").write_text("Fallback content.", encoding="utf-8")
            # Should not raise; broken PDF is skipped, valid.txt is loaded
            chunks = load_documents(tmp)
            sources = {c.source for c in chunks}
            assert "valid.txt" in sources

    def test_multiple_files_all_chunks_have_text(self, docs_dir):
        chunks = load_documents(docs_dir)
        for c in chunks:
            assert c.text.strip(), f"Empty chunk from {c.source} index {c.chunk_index}"

    def test_custom_chunk_size_produces_more_chunks(self, docs_dir):
        chunks_small = load_documents(docs_dir, chunk_size=10, overlap=0)
        chunks_large = load_documents(docs_dir, chunk_size=800, overlap=0)
        assert len(chunks_small) > len(chunks_large)
