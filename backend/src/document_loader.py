"""
Document loader: ingests PDF, DOCX, TXT, and MD files from a folder.
Splits them into overlapping chunks for retrieval.
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocumentChunk:
    """A chunk of text from a source document."""
    text: str
    source: str          # filename
    chunk_index: int
    total_chunks: int


def _load_txt(path: Path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _load_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        print(f"  [warn] Could not read PDF {path.name}: {e}")
        return ""


def _load_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        print(f"  [warn] Could not read DOCX {path.name}: {e}")
        return ""


LOADERS = {
    ".txt":  _load_txt,
    ".md":   _load_txt,
    ".pdf":  _load_pdf,
    ".docx": _load_docx,
}


def _split_into_chunks(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Split text into overlapping word-level chunks."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks


def load_documents(folder: str, chunk_size: int = 800, overlap: int = 150) -> list[DocumentChunk]:
    """
    Load all supported documents from *folder* and return a flat list of chunks.

    Supported formats: .txt, .md, .pdf, .docx
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Documents folder not found: {folder}")

    all_chunks: list[DocumentChunk] = []
    files = sorted(folder_path.iterdir())

    for file_path in files:
        suffix = file_path.suffix.lower()
        loader = LOADERS.get(suffix)
        if loader is None:
            continue

        print(f"  Loading {file_path.name}...")
        raw_text = loader(file_path)
        if not raw_text.strip():
            print(f"  [warn] Empty content in {file_path.name}, skipping.")
            continue

        chunks = _split_into_chunks(raw_text, chunk_size, overlap)
        for i, chunk_text in enumerate(chunks):
            all_chunks.append(DocumentChunk(
                text=chunk_text,
                source=file_path.name,
                chunk_index=i,
                total_chunks=len(chunks),
            ))

    return all_chunks
