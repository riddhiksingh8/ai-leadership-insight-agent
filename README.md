# AI Leadership Insight Agent

A RAG-powered Q&A system that lets executive leadership ask natural language questions over internal company documents. Upload PDFs, Word docs, or text files and get grounded, cited answers in real time.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq (Llama 3.3 70B) — free tier |
| Embeddings | sentence-transformers (local, no API needed) |
| Backend | FastAPI + Python |
| Frontend | Next.js 14 + Tailwind CSS |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
ai-leadership/
├── backend/
│   ├── src/
│   │   ├── agent.py            # RAG orchestration + Groq streaming
│   │   ├── document_loader.py  # PDF / DOCX / TXT / MD ingestion & chunking
│   │   └── embedder.py         # Local vector store with cosine similarity
│   ├── tests/                  # Pytest test suite
│   ├── app.py                  # FastAPI server
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js App Router (layout, page, globals)
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx   # Streaming chat UI
│   │   │   └── DocumentPanel.tsx   # Upload / delete documents
│   │   └── lib/api.ts          # All backend API calls
│   ├── next.config.js
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── create_test_pdf.py          # Generates sample reports for testing
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### 1. Set up environment

```bash
cp .env.example .env
# Add your Groq API key to .env:
# GROQ_API_KEY=gsk_...
```

### 2. Generate test documents (optional)

```bash
pip install fpdf2
python create_test_pdf.py
```

This creates 3 sample PDFs in `backend/documents/`:
- `q1_2025_report.pdf` — Financial performance & sales
- `strategy_2025.pdf` — Annual strategy & OKRs
- `hr_culture_report.pdf` — People & culture metrics

### 3. Run locally

**Terminal 1 — Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Running with Docker

```bash
docker compose up --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000](http://localhost:8000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Server + agent status |
| `GET` | `/documents` | List uploaded documents |
| `POST` | `/documents/upload` | Upload a document |
| `DELETE` | `/documents/{filename}` | Delete a document |
| `POST` | `/ask` | Ask a question (full response) |
| `POST` | `/ask/stream` | Ask a question (SSE streaming) |

### Example

```bash
# Upload a document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@report.pdf"

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is our revenue trend?"}'
```

---

## How It Works

1. **Upload** — Documents are chunked into ~800-word overlapping segments
2. **Embed** — Each chunk is embedded locally using `all-MiniLM-L6-v2` (no external API)
3. **Retrieve** — On each question, the top-k most relevant chunks are retrieved via cosine similarity
4. **Generate** — The chunks + question are sent to Groq (Llama 3.3 70B), which streams a grounded answer citing the source documents

Embeddings are cached to disk so re-indexing only happens when documents change.

---

## Supported Document Formats

`.pdf` `.docx` `.txt` `.md`
