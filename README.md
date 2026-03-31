# NFR Studio

NFR Studio is a Streamlit application for generating, validating, and improving non-functional requirements (NFRs) using an AI-assisted workflow.

It supports both greenfield analysis from a system description and review of existing NFR sets, then layers on prioritisation, test criteria, conflict analysis, remediation, and compliance mapping.

## Features

- Generate a structured NFR pack from a plain-English system description.
- Validate an existing NFR set against a supplied system description.
- Run a multi-step analysis workflow covering:
  - gap clarification
  - NFR generation or validation
  - priority scoring
  - test acceptance criteria
  - conflict detection
  - remediation suggestions
  - compliance mapping
- Save runs locally and reload them from the sidebar.
- Refine a loaded run by adding more context and rerunning as a new version.
- Ask grounded follow-up questions about the current run in the `Ask` tab.
- Download the full pack or individual output sections as Markdown.
- Optionally redact common sensitive values before sending content to OpenAI.

## Project Structure

- `app.py`: main Streamlit UI and workflow orchestration.
- `agents/nfr_agent.py`: OpenAI-backed agent prompts and helper functions.
- `utils/redaction.py`: input redaction helpers.
- `saved_runs/`: local saved output packs.
- `AGENTS.md`: project-specific agent guidance.
- `requirements.txt`: Python dependencies.
- `.env`: local environment variables.

## Requirements

- Python
- A virtual environment for local dependencies
- An OpenAI API key in `.env`

Example `.env`:

```env
OPENAI_API_KEY=your_key_here
```

Do not commit `.env` or any other sensitive credentials.

## Getting Started

1. Create a virtual environment if you do not already have one.
2. Activate the virtual environment.
3. Install dependencies from `requirements.txt`.
4. Add your `OPENAI_API_KEY` to `.env`.
5. Start the Streamlit app.

### Windows (Git Bash)

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## How To Use

### Generate Mode

Use `Generate NFR Pack` when you have a system description and want the application to produce a full NFR pack.

Outputs include:

- clarification of missing context and assumptions
- generated NFRs by category
- priority matrix
- test acceptance criteria
- conflicts and trade-offs
- remediation suggestions
- compliance mapping

### Validate Mode

Use `Validate Existing NFRs` when you already have an NFR set and want the application to review it.

Outputs include:

- coverage and gap analysis
- vague or non-measurable NFR identification
- remediation guidance
- compliance mapping

## Saved Runs And Refinement

- Runs can be saved locally as Markdown packs.
- Saved runs appear in the sidebar and can be reloaded later.
- Loaded runs can be refined by adding more context in `Add More Context`.
- Refinement creates a new run version rather than overwriting the original.

## Ask Tab

Each completed run includes an `Ask` tab where you can ask grounded follow-up questions about the outputs currently on screen.

Examples:

- Which NFRs matter most for MVP?
- What should I clarify with stakeholders next?
- Rewrite the security NFRs more tightly.

## Downloads

The application currently supports Markdown downloads for:

- the full pack
- individual analysis sections

Additional export options, such as Excel, can be added by extending the Python backend and Streamlit UI.

## Notes

- `saved_runs/` is intended for local run output and is ignored by git.
- `.env` is also ignored by git and should stay local.
- The application is built in Streamlit, so UI and backend changes are made in Python.
