# NFR Studio

NFR Studio generates, validates, and improves non-functional requirements (NFRs) using an AI-assisted workflow.

The repository currently supports two local app paths:

- `app.py`: the original Streamlit UI
- `backend/` + `frontend/`: the newer FastAPI + React UI

Both paths use the same core agent prompts and saved-run model.

## Features

- Generate a structured NFR pack from a plain-English system description.
- Validate an existing NFR set against a supplied system description.
- Run a multi-step analysis workflow covering clarification, NFR generation or validation, prioritisation, test criteria, conflicts, remediation, and compliance mapping.
- Add supporting attachments such as PDFs, notes, and architecture diagrams to enrich the analysis context.
- Preview redaction and mask common sensitive values before model submission.
- Save runs locally, reload them later, and refine them with additional context.
- Ask grounded follow-up questions about the current run.
- Download the full pack or individual sections as Markdown.

## Project Structure

- `app.py`: Streamlit UI
- `backend/`: FastAPI API for the React app
- `frontend/`: React + Tailwind UI
- `agents/nfr_agent.py`: OpenAI-backed prompts and agent helpers
- `utils/redaction.py`: redaction helpers
- `utils/attachments.py`: attachment extraction helpers
- `utils/chunking.py`: knowledge base chunking helpers (RAG)
- `utils/rag_manager.py`: embed/ingest/retrieve manager (RAG)
- `scripts/ingest_knowledge_base.py`: CLI to index the knowledge base (RAG)
- `knowledge_base/`: markdown knowledge base (projects + compliance) (RAG)
- `saved_runs/`: local saved output packs
- `AGENTS.md`: project-specific agent guidance

## Requirements

- Python
- A virtual environment for Python dependencies
- Node.js and npm for the React frontend
- An `OPENAI_API_KEY` in `.env`

Example `.env`:

```env
OPENAI_API_KEY=your_key_here
```

Do not commit `.env` or any other sensitive credentials.

## Getting Started

### Option 1: Streamlit

```bash
python -m venv venv
source venv/bin/activate
# Windows (PowerShell): venv\Scripts\Activate.ps1
python -m pip install -r requirements-streamlit.txt
python -m streamlit run app.py
```

### Option 2: React + FastAPI

Start the API from the repo root:

```bash
python -m venv venv
source venv/bin/activate
# Windows (PowerShell): venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Start the frontend from `frontend/`:

```bash
npm install
npm run dev
```

By default the frontend calls `http://localhost:8000`. Override with `VITE_API_BASE_URL` if needed.

### One-Command Demo Run

You can start the backend + frontend with:

```bash
bash scripts/run_demo.sh
```

## RAG Knowledge Base (MVP)

NFR Studio can optionally retrieve insights from past retail/ecom projects stored under `knowledge_base/`.

### Knowledge Base Layout

- `knowledge_base/projects/*.md`: past project NFRs / learnings
- `knowledge_base/compliance/*.md`: lightweight compliance notes / checklists

Each project file supports YAML frontmatter, for example:

```md
---
project_id: "retail_fashion_001"
industry: "fashion_ecommerce"
tech_stack: ["shopify_plus", "headless"]
scale: "100k_orders_month"
lessons: ["image_cdn_critical", "black_friday_50x_load"]
---
```

### Indexing (ChromaDB)

The vector store persists locally to `.chroma/` (gitignored).

During ingestion, documents are chunked to roughly 500-1000 tokens per chunk (estimated) and stored with metadata such as:
`project_type`, `industry`, `tech_stack`, `nfr_category`, and `lesson_learned` (derived from frontmatter/heuristics for MVP).

You can ingest in any of these ways:

1) CLI:

```bash
python scripts/ingest_knowledge_base.py
```

2) React UI:

Open the **Admin: Knowledge Base** expander and use **Upload + Reindex** or **Reindex Existing Files**.

3) API endpoints (for tooling/automation):

- `GET /api/kb/status`
- `POST /api/kb/ingest`
- `POST /api/kb/upload` (multipart: `project_file`, `target=projects|compliance`)

### Retrieval + Provenance

- During **Generate** runs, the backend retrieves the top 5 relevant knowledge base chunks (semantic search with a lightweight keyword overlap rerank) and injects them into the NFR generation prompt.
- The UI shows a "Based on insights from: Project X, Y, Z" banner and a **Knowledge Base** tab with retrieved snippets.
- The NFR generator prompt asks the model to cite relevant `project_id` values in a "Based on insights from" column when a retrieved source influenced an NFR.

### Embeddings Configuration

- Default: OpenAI embeddings (`text-embedding-3-small`) to match the existing OpenAI integration.
- Override OpenAI embedding model with `RAG_OPENAI_MODEL` if needed.
- Optional local mode:
  - Set `RAG_EMBEDDINGS_PROVIDER=local`
  - Optionally set `RAG_LOCAL_MODEL=sentence-transformers/all-MiniLM-L6-v2`
  - Install local embedding deps: `python -m pip install -r requirements-local-embeddings.txt`

### Chunking

Chunking uses LangChain's text splitters. If `tiktoken` is installed, chunk sizes/overlap are token-based; otherwise they fall back to a character-based approximation.

## React UI Coverage

- Generate and validate flows
- Live agent status via background job polling
- Attachment processing and attachment warnings
- Redaction previews and server-side masking
- Saved run list, load, save, and project grouping
- Refine and rerun with additional context
- Grounded follow-up chat
- Markdown downloads
- Generate-mode visual summaries
- Validate-mode insight summaries
- Usage summary cards

## Saved Runs

- Runs are saved locally as Markdown packs in `saved_runs/`.
- Sidebar grouping is driven by the `Project` field on the run.
- If no project is set, the run is grouped under `No Project`.
- Refinement creates a new run version rather than overwriting the original.

## Security Guardrails

- Local secret files such as `.env` and `.env.*` are ignored by git.
- Generated run output in `saved_runs/` is ignored by git.
- GitHub Actions runs a Gitleaks secret scan on pushes, pull requests, and manual workflow runs.

## Notes

- `saved_runs/` is intended for local run output and is ignored by git.
- `.env` should stay local.
- The Streamlit app remains available as a fallback while the React UI continues to evolve.
