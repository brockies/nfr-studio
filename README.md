# Architecture Assurance Studio

Architecture Assurance Studio helps teams generate, validate, and strengthen non-functional requirements, then connect them to controls, evidence, and review-ready assurance outputs.

The repository currently supports two local app paths:

- `app.py`: the original Streamlit UI
- `backend/` + `frontend/`: the newer FastAPI + React UI

Both paths still share the same core agent prompts and saved-run model, but the React + FastAPI path is now the main product surface.

## What It Does

- Generate a structured NFR pack from a plain-English system description
- Validate an existing NFR set against a supplied system description
- Run a multi-step agent workflow covering:
  - gap clarification
  - diagram generation
  - NFR generation or validation
  - prioritisation
  - test criteria
  - conflict detection
  - remediation
  - compliance and evidence mapping
- Produce compliance outputs that include:
  - framework applicability
  - evidence planning
  - proof gaps
  - evidence crosswalks
  - confidence improvement guidance
- Support stakeholder-focused readouts for architecture, security/compliance, delivery, and executive audiences
- Save runs locally, reload them later, and refine them with additional context
- Ask grounded follow-up questions about the current run
- Download the full pack or individual sections as Markdown

## Current Product Direction

The product has moved beyond "just an NFR generator".

Current positioning:

> Tell me not just what requirements I need, but what I will need to prove later.

That means the app now focuses on:

- architecture assurance
- compliance/evidence planning
- project-specific retrieval context
- stakeholder-ready summaries
- visual workflow and system-diagram support

## Project Structure

- `app.py`: Streamlit UI
- `backend/`: FastAPI API for the React app
- `frontend/`: React + Tailwind UI
- `backend/orchestrator.py`: lightweight deterministic workflow runner
- `backend/pipeline.py`: workflow preparation, attachment handling, and orchestration wiring
- `agents/nfr_agent.py`: OpenAI-backed prompts and agent helpers
- `utils/redaction.py`: redaction helpers
- `utils/attachments.py`: attachment extraction helpers
- `utils/chunking.py`: chunking helpers for retrieval ingestion
- `utils/rag_manager.py`: project-scoped embed/ingest/retrieve manager
- `backend/config/assessment_definitions.json`: config-driven framework pack and profile definitions
- `saved_runs/`: local saved output packs
- `docs/product-backlog.md`: current product roadmap
- `AGENTS.md`: project-specific agent guidance

## Requirements

- Python
  - recommended: 3.12 where possible for smoother dependency support
  - the current repo venv may also be running on 3.13 locally
- A Python virtual environment
- Node.js and npm for the React frontend
- An `OPENAI_API_KEY` in `.env` if you are using OpenAI-backed inference and embeddings

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

### Windows / Git Bash Note

If you are using Git Bash on Windows, it is safest to run the backend with the repo venv explicitly:

```bash
source venv/Scripts/activate
python -m uvicorn backend.main:app --reload
```

If needed, you can also use the full path:

```bash
/c/Users/<you>/projects/nfr-studio/venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

## Workflow Overview

### Generate Mode

The generate workflow currently runs these steps:

1. Gap Clarification
2. Diagram Generation
3. NFR Generation
4. Scoring and Priority
5. Test Acceptance Criteria
6. Conflict Detection
7. Remediation
8. Compliance & Evidence Mapping

### Validate Mode

The validate workflow currently runs these steps:

1. Gap Clarification
2. NFR Validation
3. Remediation
4. Compliance & Evidence Mapping

These flows are now executed through the lightweight orchestrator in `backend/orchestrator.py`.

## Retrieval / RAG Model

The app now uses a **project-scoped retrieval model** for user-supplied context.

### Current Retrieval Rules

- Supporting attachments uploaded during a run are processed, chunked, embedded, and stored in a **project-specific Chroma collection**
- Retrieval only uses the collection for the current `Project` name
- Shared client/document corpora have been retired from the active product flow

This means:

- Project A attachments do not become retrieval context for Project B
- Different clients should remain isolated as long as they do not reuse the same project name/slug

### Chroma Storage

- Chroma persists locally to `.chroma/`
- Project collections are named using the `project_kb__...` prefix
- The app includes a lightweight **Project Collections** explorer in the React UI for inspecting stored chunks and metadata

### Important Scope Note

The old shared knowledge base flow has been retired from the active app experience.

- shared KB upload/reindex endpoints now return `410 Gone`
- the UI now focuses on project collections instead of a shared corpus

## Embeddings Configuration

- Default: OpenAI embeddings (`text-embedding-3-small`)
- Override with `RAG_OPENAI_MODEL` if needed
- Optional local embeddings mode:
  - set `RAG_EMBEDDINGS_PROVIDER=local`
  - optionally set `RAG_LOCAL_MODEL=sentence-transformers/all-MiniLM-L6-v2`
  - install local embedding dependencies as needed

## Diagrams

Generate mode can now produce a PlantUML system-context style artifact.

- The backend generates PlantUML source
- The frontend can render it if a PlantUML server URL is configured

Example frontend env:

```env
VITE_PLANTUML_SERVER_URL=https://www.plantuml.com/plantuml
```

For sensitive environments, point this at a trusted/self-hosted PlantUML server instead of the public service.

## Privacy / Deployment Positioning

The React UI now includes a privacy-mode selector to show possible deployment paths:

- Cloud
- Local
- Private

This is currently **UI-only** and does not yet change backend routing, but it is intended to signal future support for:

- hosted OpenAI-style inference
- local/private-hosted Llama-style inference
- private or air-gapped enterprise deployments

## React UI Coverage

- Generate and validate flows
- Live agent status via background job polling
- Visual orchestrator/pipeline progress
- PlantUML diagram tab
- Attachment processing and attachment warnings
- Redaction previews and server-side masking
- Saved run list, load, save, rename, and project grouping
- Refine and rerun with additional context
- Grounded follow-up chat
- Stakeholder views
- Compliance & evidence views
- Markdown downloads
- Generate-mode visual summaries
- Validate-mode insight summaries
- Usage summary cards

## Saved Runs

- Runs are saved locally as Markdown packs in `saved_runs/`
- Sidebar grouping is driven by the `Project` field on the run
- If no project is set, the run is grouped under `No Project`
- Refinement creates a new run version rather than overwriting the original

## Smoke Tests

Run the small local smoke suite with:

```bash
bash scripts/run_smoke_tests.sh
```

There is also frontend build verification:

```bash
cd frontend
npm run build
```

## Security Guardrails

- Local secret files such as `.env` and `.env.*` are ignored by git
- Generated run output in `saved_runs/` is ignored by git
- The app masks common sensitive values before model submission
- Project-scoped retrieval is used to reduce cross-client document leakage risk

## Notes

- `saved_runs/` is intended for local run output and is ignored by git
- `.env` should stay local
- The Streamlit app remains available as a fallback while the React UI continues to evolve
- The frontend build currently succeeds with one non-blocking CSS minification warning that still needs cleanup
