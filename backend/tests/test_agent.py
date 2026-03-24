"""
Tests for src/agent.py

Covers:
- LeadershipInsightAgent.load: calls document loader + vector store build,
  raises on empty folder
- LeadershipInsightAgent.ask: builds correct prompt, streams answer,
  cites sources, handles no-results case
- System prompt content
- Context block construction
"""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

from src.agent import SYSTEM_PROMPT, LeadershipInsightAgent
from src.document_loader import DocumentChunk
from src.embedder import VectorEntry


# ── stream event helpers ───────────────────────────────────────────────────

def _text_delta_event(text: str):
    event = MagicMock()
    event.type = "content_block_delta"
    event.delta.type = "text_delta"
    event.delta.text = text
    return event


def _thinking_delta_event(thinking: str):
    event = MagicMock()
    event.type = "content_block_delta"
    event.delta.type = "thinking_delta"
    event.delta.thinking = thinking
    return event


def _other_event(event_type: str):
    event = MagicMock()
    event.type = event_type
    return event


@contextmanager
def _mock_stream(events):
    """Context manager that yields an iterable of mock stream events."""
    stream = MagicMock()
    stream.__iter__ = MagicMock(return_value=iter(events))
    stream.__enter__ = MagicMock(return_value=stream)
    stream.__exit__ = MagicMock(return_value=False)
    yield stream


# ── fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_vector_entries():
    rng = np.random.default_rng(7)

    def _unit(seed):
        v = rng.standard_normal(384).astype(np.float32)
        return v / np.linalg.norm(v)

    return [
        VectorEntry(
            text="Revenue grew 12% YoY driven by cloud subscriptions.",
            source="annual_report.txt",
            chunk_index=0,
            total_chunks=3,
            embedding=_unit(0),
        ),
        VectorEntry(
            text="APAC region grew 14% and is the fastest-growing market.",
            source="q3_report.txt",
            chunk_index=1,
            total_chunks=2,
            embedding=_unit(1),
        ),
    ]


@pytest.fixture
def agent(docs_dir):
    """Agent pointed at the shared temp docs_dir fixture."""
    return LeadershipInsightAgent(
        documents_folder=docs_dir,
        top_k=3,
        model="claude-opus-4-6",
    )


# ── system prompt ──────────────────────────────────────────────────────────

class TestSystemPrompt:
    def test_system_prompt_is_non_empty(self):
        assert len(SYSTEM_PROMPT.strip()) > 0

    def test_system_prompt_mentions_grounding(self):
        assert "document" in SYSTEM_PROMPT.lower()

    def test_system_prompt_instructs_citation(self):
        text = SYSTEM_PROMPT.lower()
        assert "cite" in text or "source" in text

    def test_system_prompt_instructs_honesty_on_gaps(self):
        text = SYSTEM_PROMPT.lower()
        assert "not" in text or "gap" in text or "insufficient" in text or "do not" in text


# ── LeadershipInsightAgent.load ────────────────────────────────────────────

class TestAgentLoad:
    def test_load_succeeds_with_valid_docs(self, agent, sample_chunks):
        with (
            patch("src.agent.load_documents", return_value=sample_chunks),
            patch.object(agent._store, "build") as mock_build,
        ):
            agent.load()
            mock_build.assert_called_once_with(sample_chunks, agent.documents_folder)

    def test_load_raises_on_empty_document_folder(self, agent):
        with patch("src.agent.load_documents", return_value=[]):
            with pytest.raises(RuntimeError, match="No supported documents"):
                agent.load()

    def test_load_reports_chunk_count(self, agent, sample_chunks, capsys):
        with (
            patch("src.agent.load_documents", return_value=sample_chunks),
            patch.object(agent._store, "build"),
        ):
            agent.load()
            captured = capsys.readouterr()
            assert str(len(sample_chunks)) in captured.out

    def test_load_calls_load_documents_with_folder_path(self, agent, sample_chunks):
        with (
            patch("src.agent.load_documents", return_value=sample_chunks) as mock_ld,
            patch.object(agent._store, "build"),
        ):
            agent.load()
            mock_ld.assert_called_once_with(agent.documents_folder)


# ── LeadershipInsightAgent.ask ─────────────────────────────────────────────

class TestAgentAsk:
    def _setup_store(self, agent, entries):
        agent._store._entries = entries

    def test_returns_streamed_text(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [
            _text_delta_event("Revenue "),
            _text_delta_event("grew 12%."),
            _other_event("message_stop"),
        ]

        with (
            patch.object(agent._store, "search", return_value=mock_vector_entries),
            patch.object(agent._client.messages, "stream") as mock_stream_method,
        ):
            mock_stream_method.return_value.__enter__ = MagicMock(return_value=iter(events))
            mock_stream_method.return_value.__exit__ = MagicMock(return_value=False)

            result = agent.ask("What is the revenue trend?")

        assert "Revenue" in result
        assert "grew 12%." in result

    def test_ignores_thinking_delta_events(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [
            _thinking_delta_event("Internal reasoning..."),
            _text_delta_event("Final answer."),
        ]

        with (
            patch.object(agent._store, "search", return_value=mock_vector_entries),
            patch.object(agent._client.messages, "stream") as mock_stream_method,
        ):
            mock_stream_method.return_value.__enter__ = MagicMock(return_value=iter(events))
            mock_stream_method.return_value.__exit__ = MagicMock(return_value=False)

            result = agent.ask("What is revenue?")

        assert "Internal reasoning" not in result
        assert "Final answer." in result

    def test_returns_no_results_message_when_store_empty(self, agent):
        with patch.object(agent._store, "search", return_value=[]):
            result = agent.ask("What is the revenue?")
        assert "No relevant information" in result

    def test_user_message_contains_question(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [_text_delta_event("Answer.")]
        captured_messages = []

        def fake_stream(**kwargs):
            captured_messages.append(kwargs["messages"])
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=iter(events))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        with patch.object(agent._store, "search", return_value=mock_vector_entries):
            with patch.object(agent._client.messages, "stream", side_effect=fake_stream):
                agent.ask("What is our APAC growth?")

        user_content = captured_messages[0][0]["content"]
        assert "What is our APAC growth?" in user_content

    def test_user_message_contains_retrieved_chunk_text(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [_text_delta_event("Answer.")]
        captured_messages = []

        def fake_stream(**kwargs):
            captured_messages.append(kwargs["messages"])
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=iter(events))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        with patch.object(agent._store, "search", return_value=mock_vector_entries):
            with patch.object(agent._client.messages, "stream", side_effect=fake_stream):
                agent.ask("Revenue question?")

        user_content = captured_messages[0][0]["content"]
        for entry in mock_vector_entries:
            assert entry.text in user_content

    def test_user_message_contains_source_filenames(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [_text_delta_event("Answer.")]
        captured_messages = []

        def fake_stream(**kwargs):
            captured_messages.append(kwargs["messages"])
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=iter(events))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        with patch.object(agent._store, "search", return_value=mock_vector_entries):
            with patch.object(agent._client.messages, "stream", side_effect=fake_stream):
                agent.ask("Revenue?")

        user_content = captured_messages[0][0]["content"]
        assert "annual_report.txt" in user_content
        assert "q3_report.txt" in user_content

    def test_claude_called_with_correct_model(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [_text_delta_event("Answer.")]
        captured_kwargs = {}

        def fake_stream(**kwargs):
            captured_kwargs.update(kwargs)
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=iter(events))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        with patch.object(agent._store, "search", return_value=mock_vector_entries):
            with patch.object(agent._client.messages, "stream", side_effect=fake_stream):
                agent.ask("Revenue?")

        assert captured_kwargs["model"] == "claude-opus-4-6"

    def test_claude_called_with_system_prompt(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [_text_delta_event("Answer.")]
        captured_kwargs = {}

        def fake_stream(**kwargs):
            captured_kwargs.update(kwargs)
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=iter(events))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        with patch.object(agent._store, "search", return_value=mock_vector_entries):
            with patch.object(agent._client.messages, "stream", side_effect=fake_stream):
                agent.ask("Revenue?")

        assert captured_kwargs["system"] == SYSTEM_PROMPT

    def test_claude_called_with_adaptive_thinking(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        events = [_text_delta_event("Answer.")]
        captured_kwargs = {}

        def fake_stream(**kwargs):
            captured_kwargs.update(kwargs)
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=iter(events))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        with patch.object(agent._store, "search", return_value=mock_vector_entries):
            with patch.object(agent._client.messages, "stream", side_effect=fake_stream):
                agent.ask("Revenue?")

        assert captured_kwargs.get("thinking") == {"type": "adaptive"}

    def test_search_called_with_question_and_top_k(self, agent, mock_vector_entries):
        events = [_text_delta_event("Answer.")]

        with patch.object(agent._store, "search", return_value=mock_vector_entries) as mock_search:
            with patch.object(agent._client.messages, "stream") as mock_sm:
                mock_sm.return_value.__enter__ = MagicMock(return_value=iter(events))
                mock_sm.return_value.__exit__ = MagicMock(return_value=False)
                agent.ask("Growth question?")

        mock_search.assert_called_once_with("Growth question?", top_k=agent.top_k)

    def test_empty_question_still_calls_search(self, agent):
        with patch.object(agent._store, "search", return_value=[]) as mock_search:
            agent.ask("")
        mock_search.assert_called_once_with("", top_k=agent.top_k)

    def test_concatenates_all_text_deltas(self, agent, mock_vector_entries):
        self._setup_store(agent, mock_vector_entries)
        tokens = ["The ", "revenue ", "grew ", "12%."]
        events = [_text_delta_event(t) for t in tokens]

        with (
            patch.object(agent._store, "search", return_value=mock_vector_entries),
            patch.object(agent._client.messages, "stream") as mock_sm,
        ):
            mock_sm.return_value.__enter__ = MagicMock(return_value=iter(events))
            mock_sm.return_value.__exit__ = MagicMock(return_value=False)
            result = agent.ask("Revenue?")

        assert result == "".join(tokens)
