# NFR Studio

Basic starter structure for the NFR Studio project.

## Structure

- `app.py`: entry point for running the project locally.
- `agents/nfr_agent.py`: placeholder NFR agent implementation.
- `AGENTS.md`: brief notes about included agents.
- `requirements.txt`: Python dependencies.
- `.env`: local environment variables.

## Getting Started

1. Create a virtual environment if you do not already have one.
2. Activate the virtual environment.
3. Install dependencies from `requirements.txt`.
4. Start the Streamlit app.

### Windows (Git Bash)

To start the Streamlit app from Git Bash on Windows:

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
