"""
Leadership Insight Agent: answers questions grounded in company documents.

Uses:
- sentence-transformers       for local semantic retrieval
- llama-3.3-70b-versatile     (via Groq) for grounded answer generation
"""

from __future__ import annotations

import os
from typing import Generator

import groq

from src.document_loader import load_documents
from src.embedder import VectorStore

# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI Leadership Insight Agent — a trusted advisor to executive leadership.

Your role is to provide clear, accurate, and actionable answers about the organization's
performance, strategy, and operations **strictly based on the internal company documents
provided to you**.

Guidelines:
1. Ground every statement in the provided document excerpts. Cite the source document(s).
2. If the documents do not contain enough information to answer confidently, say so clearly
   rather than speculating.
3. Quantify where possible (percentages, figures, trends).
4. Keep answers concise but complete — executive-level clarity.
5. If multiple documents address the question, synthesize them coherently.
6. Flag any contradictions or data gaps you notice across documents.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────────────────

class LeadershipInsightAgent:
    """
    End-to-end RAG agent for leadership Q&A.

    1. Loads & chunks documents from a folder.
    2. Builds / restores a local vector store.
    3. For each question, retrieves the most relevant chunks and
       asks Groq LLM to produce a grounded answer.
    """

    def __init__(
        self,
        documents_folder: str,
        top_k: int = 6,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        self.documents_folder = documents_folder
        self.top_k = top_k
        self.model = model
        self._store = VectorStore()
        self._client = groq.Groq(
            api_key=os.environ.get("GROQ_API_KEY")
        )

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load documents and build (or restore) the vector store."""
        print("\n[1/2] Loading documents...")
        chunks = load_documents(self.documents_folder)
        if not chunks:
            raise RuntimeError(
                f"No supported documents found in '{self.documents_folder}'.\n"
                "Add .txt, .md, .pdf, or .docx files and try again."
            )
        print(f"      {len(chunks)} chunks from {len({c.source for c in chunks})} file(s).")

        print("\n[2/2] Building vector index...")
        self._store.build(chunks, self.documents_folder)
        print("      Ready.\n")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def _build_user_message(self, question: str, top_k: int) -> str | None:
        """Retrieve relevant chunks and build the user message. Returns None if no results."""
        results = self._store.search(question, top_k=top_k)
        if not results:
            return None

        context_parts = []
        seen_sources: set[str] = set()
        for entry in results:
            header = f"[Source: {entry.source} | chunk {entry.chunk_index + 1}/{entry.total_chunks}]"
            context_parts.append(f"{header}\n{entry.text}")
            seen_sources.add(entry.source)

        context_block = "\n\n---\n\n".join(context_parts)
        sources_listed = ", ".join(sorted(seen_sources))

        return (
            f"The following excerpts are from internal company documents "
            f"({sources_listed}):\n\n"
            f"{context_block}\n\n"
            f"---\n\n"
            f"Leadership question: {question}"
        )

    def ask_stream(self, question: str, top_k: int | None = None) -> Generator[str, None, None]:
        """Yield answer text chunks as they stream from Groq."""
        if top_k is None:
            top_k = self.top_k

        user_message = self._build_user_message(question, top_k)
        if user_message is None:
            yield "No relevant information found in the loaded documents."
            return

        stream = self._client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    def ask(self, question: str, top_k: int | None = None) -> str:
        """
        Answer *question* using retrieved document context + Groq LLM.

        Streams to stdout in real-time and returns the full answer string.
        """
        answer_parts: list[str] = []
        for chunk in self.ask_stream(question, top_k=top_k):
            print(chunk, end="", flush=True)
            answer_parts.append(chunk)
        print()  # newline after streamed output
        return "".join(answer_parts)
