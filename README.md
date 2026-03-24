# AI Leadership Insight Agent

An AI-powered assistant that answers executive leadership questions grounded in your company's internal documents — annual reports, quarterly reviews, strategy notes, and operational updates.

## How It Works

1. **Ingests** documents from a folder (PDF, DOCX, TXT, MD)
2. **Chunks & embeds** them locally using `sentence-transformers`
3. **Retrieves** the most relevant passages for each question via cosine similarity
4. **Generates** a concise, cited answer using `claude-opus-4-6` with adaptive thinking

No data leaves your machine except for the retrieved context sent to Claude's API.

---

## Project Structure

```
.
├── main.py                          # CLI entry point
├── requirements.txt
├── .env.example                     # API key template
├── src/
│   ├── document_loader.py           # File ingestion and chunking
│   ├── embedder.py                  # Local vector store (sentence-transformers)
│   └── agent.py                     # RAG orchestration + Claude streaming
└── documents/                       # Put your company documents here
    ├── annual_report_2024.txt        # Sample documents included
    ├── q3_2024_quarterly_report.txt
    ├── strategy_2025.txt
    └── operational_update_oct2024.txt
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> The first run downloads the `all-MiniLM-L6-v2` embedding model (~80 MB). Subsequent runs use a local cache.

### 2. Set your Anthropic API key

```bash
cp .env.example .env
# Edit .env and add your key:
# ANTHROPIC_API_KEY=sk-ant-...
```

Or export it directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Add your documents

Drop any `.txt`, `.md`, `.pdf`, or `.docx` files into the `documents/` folder. Sample documents are included so you can run it immediately.

### 4. Run

**Interactive mode** (ask multiple questions):

```bash
python main.py
```

**Single question:**

```bash
python main.py --question "What is our current revenue trend?"
```

**Custom documents folder:**

```bash
python main.py --docs ./my_company_docs
```

---

## Example Questions

```
What is our current revenue trend?
Which departments are underperforming?
What were the key risks highlighted in the last quarter?
What is our strategic outlook for next year?
How is customer satisfaction trending?
```

---

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `--docs` | `./documents` | Folder containing company documents |
| `--question`, `-q` | *(interactive)* | Ask a single question and exit |
| `--top-k` | `6` | Number of document chunks to retrieve per query |
| `--model` | `claude-opus-4-6` | Claude model to use |

---

## Architecture

### Document Loading (`document_loader.py`)

Reads all supported files from the documents folder and splits them into overlapping 800-word chunks (150-word overlap). This window size balances retrieval precision with enough surrounding context for meaningful answers.

Supported formats: `.txt`, `.md`, `.pdf` (via `pypdf`), `.docx` (via `python-docx`)

### Vector Store (`embedder.py`)

Chunks are encoded with the `all-MiniLM-L6-v2` sentence-transformers model — a lightweight (80 MB), locally-run model that produces high-quality semantic embeddings. Embeddings are L2-normalised and stored in memory; retrieval is a fast matrix dot product (cosine similarity).

The vector store is serialised to `.vector_store.pkl` inside the documents folder. It is automatically invalidated and rebuilt whenever file names, sizes, or modification times change — so re-running after adding a document does not re-embed unchanged files unnecessarily.

### Agent (`agent.py`)

For each question:

1. The query is embedded and the top-k most similar chunks are retrieved.
2. Each chunk is labelled with its source filename and chunk index, then assembled into a context block.
3. Claude receives the context block plus the question under a strict grounding system prompt that instructs it to cite sources, quantify where possible, and flag gaps or contradictions.
4. The answer is streamed token-by-token to the terminal using `claude-opus-4-6` with adaptive thinking enabled, so Claude reasons before responding.

---

## Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)
- Internet access on first run (to download the embedding model)

### Dependencies

| Package | Purpose |
|---|---|
| `anthropic` | Claude API client |
| `sentence-transformers` | Local semantic embeddings |
| `numpy` | Cosine similarity search |
| `pypdf` | PDF text extraction |
| `python-docx` | DOCX text extraction |
| `rich` | Pretty terminal output |
| `python-dotenv` | `.env` file support |

---

## Limitations

- **Context window**: Each query sends up to 6 retrieved chunks (~4,800 words) to Claude. Very large documents with sparse coverage may need `--top-k` increased.
- **Scanned PDFs**: Image-based PDFs (scans) are not supported — only text-layer PDFs are readable by `pypdf`. Use OCR pre-processing if needed.
- **No conversation memory**: Each question is independent. The agent does not maintain session history across questions.
