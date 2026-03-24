"""
AI Leadership Insight Agent — FastAPI server.

Start with:
    uvicorn app:app --reload

Endpoints:
    GET  /health                  — health check
    GET  /documents               — list uploaded documents
    POST /documents/upload        — upload a document (.txt .md .pdf .docx)
    DELETE /documents/{filename}  — delete a document
    POST /ask                     — ask a question (full response)
    POST /ask/stream              — ask a question (Server-Sent Events stream)
"""

from __future__ import annotations

import json
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent import LeadershipInsightAgent

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

DOCS_FOLDER = Path(os.getenv("DOCS_FOLDER", "documents"))
TOP_K = int(os.getenv("TOP_K", "6"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

# ─────────────────────────────────────────────────────────────────────────────
# Agent singleton
# ─────────────────────────────────────────────────────────────────────────────

_agent: LeadershipInsightAgent | None = None


def _reload_agent() -> None:
    """(Re)initialize the agent from the current documents folder."""
    global _agent
    docs = [f for f in DOCS_FOLDER.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS]
    if not docs:
        _agent = None
        return
    agent = LeadershipInsightAgent(documents_folder=str(DOCS_FOLDER), top_k=TOP_K, model=MODEL)
    agent.load()
    _agent = agent


def _get_agent() -> LeadershipInsightAgent:
    if _agent is None:
        raise HTTPException(
            status_code=503,
            detail="No documents loaded yet. Upload at least one document first via POST /documents/upload",
        )
    return _agent


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
    DOCS_FOLDER.mkdir(exist_ok=True)
    _reload_agent()  # load existing docs on startup if any
    yield


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Leadership Insight Agent",
    description="RAG-powered Q&A over your company documents using Groq + Llama 3.3",
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    top_k: int = TOP_K


class AskResponse(BaseModel):
    question: str
    answer: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["General"])
def health():
    """Check if the server is running and the agent is ready."""
    return {
        "status": "ok",
        "agent_ready": _agent is not None,
        "model": MODEL,
        "docs_folder": str(DOCS_FOLDER),
    }


@app.get("/documents", tags=["Documents"])
def list_documents():
    """List all uploaded documents."""
    files = sorted(
        f.name for f in DOCS_FOLDER.iterdir()
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
    )
    return {"documents": files, "count": len(files)}


@app.post("/documents/upload", tags=["Documents"], status_code=201)
def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (.txt, .md, .pdf, .docx).
    The agent is automatically reloaded after upload.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    dest = DOCS_FOLDER / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    _reload_agent()
    return {"message": f"'{file.filename}' uploaded and agent reloaded.", "filename": file.filename}


@app.delete("/documents/{filename}", tags=["Documents"])
def delete_document(filename: str):
    """Delete a document and reload the agent."""
    target = DOCS_FOLDER / filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"'{filename}' not found.")
    target.unlink()
    _reload_agent()
    return {"message": f"'{filename}' deleted and agent reloaded."}


@app.post("/ask", response_model=AskResponse, tags=["Q&A"])
def ask(request: AskRequest):
    """Ask a question and get the full answer at once."""
    agent = _get_agent()
    answer = agent.ask(request.question, top_k=request.top_k)
    return AskResponse(question=request.question, answer=answer)


@app.post("/ask/stream", tags=["Q&A"])
def ask_stream(request: AskRequest):
    """
    Ask a question and receive the answer as a Server-Sent Events stream.

    Each event looks like:  data: {"text": "..."}
    Stream ends with:       data: [DONE]
    """
    agent = _get_agent()

    def generate():
        for chunk in agent.ask_stream(request.question, top_k=request.top_k):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
