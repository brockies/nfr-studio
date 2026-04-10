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
source venv/Scripts/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Option 2: React + FastAPI

Start the API from the repo root:

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Start the frontend from `frontend/`:

```bash
npm install
npm run dev
```

By default the frontend calls `http://localhost:8000`. Override with `VITE_API_BASE_URL` if needed.

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

## Notes

- `saved_runs/` is intended for local run output and is ignored by git.
- `.env` should stay local.
- The Streamlit app remains available as a fallback while the React UI continues to evolve.
