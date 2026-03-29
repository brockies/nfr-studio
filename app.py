"""
app.py - NFR Studio
Expanded pipeline for NFR generation, review, remediation, and compliance mapping.
Run with: streamlit run app.py
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from agents.nfr_agent import MODEL_NAME, estimate_usage_cost
from utils.redaction import RedactionResult, redact_text, summarize_redaction

SAVE_DIR = Path("saved_runs")
SAVE_DIR.mkdir(exist_ok=True)

# â”€â”€ Page config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.set_page_config(
    page_title="NFR Studio",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

# â”€â”€ Custom CSS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown("""
<style>
  html, body, [class*="css"] {
    font-family: -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif;
    color: #1E293B;
  }
  .block-container { padding-top: 0.5rem !important; padding-left: 2rem !important; }
  header[data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebarCollapseButton"] { display: block !important; }
  .stApp { background: #E2E8F0; }

  [data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E2E8F0 !important;
    min-width: 280px !important; max-width: 280px !important;
  }
  [data-testid="stSidebar"] > div:first-child {
    padding-top: 0.5rem !important;
    padding-left: 0.75rem !important; padding-right: 0.75rem !important;
  }
  [data-testid="stSidebar"] * { color: #1E293B !important; }
  [data-testid="stSidebar"] .stButton button {
    background: #2563EB !important; border: 1px solid #2563EB !important;
    color: #FFFFFF !important; border-radius: 7px !important;
    font-size: 0.88rem !important; padding: 0.65rem 1rem !important;
    min-height: 42px !important; transition: all 0.15s ease !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
  }
  [data-testid="stSidebar"] .stButton button *,
  [data-testid="stSidebar"] .stButton button div,
  [data-testid="stSidebar"] .stButton button span,
  [data-testid="stSidebar"] .stButton button p {
    color: #FFFFFF !important;
  }
  [data-testid="stSidebar"] .stButton button:hover {
    background: #1D4ED8 !important; border-color: #1D4ED8 !important; color: #FFFFFF !important;
  }
  [data-testid="stSidebar"] .stButton button[kind="primary"],
  [data-testid="stSidebar"] .stButton button[kind="primary"] * {
    background: #2563EB !important;
    color: #FFFFFF !important; border: 1px solid #2563EB !important; font-weight: 600 !important;
  }
  .saved-run-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 0.8rem 0.9rem;
    margin: 0.55rem 0 0.35rem 0;
  }
  .saved-run-card .title {
    color: #0F172A;
    font-size: 0.84rem;
    font-weight: 600;
    line-height: 1.35;
    word-break: break-word;
  }
  .saved-run-card .meta {
    color: #94A3B8;
    font-size: 0.73rem;
    margin-top: 0.3rem;
  }

  .header-block {
    padding: 0.4rem 0 1.2rem 0; border-bottom: 1px solid #E2E8F0;
    margin-bottom: 1.4rem; position: relative;
  }
  .header-block::after {
    content: ''; position: absolute; bottom: -1px; left: 0;
    width: 56px; height: 2px;
    background: linear-gradient(90deg, #6366F1, #38BDF8); border-radius: 2px;
  }
  .header-block h1 {
    font-size: 1.75rem; font-weight: 700; letter-spacing: -0.5px;
    color: #0F172A; margin: 0;
  }
  .header-block p { color: #94A3B8; margin: 0.35rem 0 0 0; font-size: 0.88rem; }

  /* Agent cards */
  .agent-card {
    display: flex; align-items: center; gap: 1rem;
    padding: 0.9rem 1.2rem; border-radius: 8px; margin-bottom: 0.5rem;
    font-size: 1.05rem; font-weight: 500; border: 1px solid transparent;
  }
  .agent-card.waiting { background: #F8FAFC; color: #94A3B8; border-color: #E2E8F0; }
  .agent-card.running { background: #EFF6FF; color: #3B82F6; border-color: #BFDBFE; }
  .agent-card.done    { background: #F0FDF4; color: #16A34A; border-color: #BBF7D0; }
  .agent-card .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
  .agent-card.waiting .dot { background: #CBD5E1; }
  .agent-card.running .dot { background: #3B82F6; animation: pulse-ring 1.2s infinite; }
  .agent-card.done    .dot { background: #16A34A; }
  .agent-card strong { font-weight: 700; }

  @keyframes pulse-ring {
    0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 rgba(59,130,246,0.4); }
    50%       { opacity: 0.8; transform: scale(1.3); box-shadow: 0 0 0 4px rgba(59,130,246,0); }
  }

  /* Metrics */
  [data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  [data-testid="stMetricLabel"] {
    font-size: 0.72rem !important; color: #94A3B8 !important;
    text-transform: uppercase; letter-spacing: 0.8px;
    font-family: 'Courier New', monospace !important;
  }
  [data-testid="stMetricValue"] {
    font-size: 2.2rem !important; font-weight: 700 !important;
    color: #0F172A !important; line-height: 1.1 !important;
  }

  /* Tabs */
  button[role="tab"] {
    font-size: 0.95rem !important; font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important; color: #475569 !important;
  }
  button[role="tab"][aria-selected="true"] { color: #4338CA !important; font-weight: 700 !important; }
  .stTabs [data-baseweb="tab-list"] {
    border-bottom: 2px solid #E2E8F0 !important;
    gap: 0.5rem !important; margin-bottom: 1rem !important;
  }
  .stTabs [data-baseweb="tab-highlight"] { background-color: #4338CA !important; }

  /* Buttons */
  .stButton button[kind="primary"] {
    background: #2563EB !important;
    border: 1px solid #2563EB !important; color: #FFFFFF !important; font-weight: 600 !important;
    border-radius: 7px !important; box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
  }
  .stButton button {
    background: #2563EB !important;
    border: 1px solid #2563EB !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-radius: 7px !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
  }
  .stButton button *,
  .stButton button div,
  .stButton button span,
  .stButton button p {
    color: #FFFFFF !important;
  }
  .stButton button:hover {
    background: #1D4ED8 !important;
    border-color: #1D4ED8 !important;
    color: #FFFFFF !important;
  }

  /* Text areas */
  [data-testid="stTextArea"] textarea {
    background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important; color: #1E293B !important; font-size: 0.9rem !important;
  }
  [data-testid="stTextArea"] textarea:focus {
    border-color: #6366F1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
  }

  /* Download */
  [data-testid="stDownloadButton"] button {
    background: #2563EB !important; border: 1px solid #2563EB !important;
    color: #FFFFFF !important; border-radius: 7px !important;
    font-weight: 600 !important; box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
  }
  [data-testid="stDownloadButton"] button *,
  [data-testid="stDownloadButton"] button div,
  [data-testid="stDownloadButton"] button span,
  [data-testid="stDownloadButton"] button p {
    color: #FFFFFF !important;
  }
  [data-testid="stDownloadButton"] button:hover {
    background: #1D4ED8 !important; border-color: #1D4ED8 !important; color: #FFFFFF !important;
  }

  /* Markdown */
  .stMarkdown p, .stMarkdown li { color: #334155 !important; }
  .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
    color: #0F172A !important;
    font-family: -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
  }
  .stMarkdown strong { color: #0F172A !important; }
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] li,
  [data-testid="stMarkdownContainer"] td {
    color: #334155 !important;
  }
  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3,
  [data-testid="stMarkdownContainer"] h4,
  [data-testid="stMarkdownContainer"] h5,
  [data-testid="stMarkdownContainer"] h6,
  [data-testid="stMarkdownContainer"] strong,
  [data-testid="stMarkdownContainer"] th {
    color: #0F172A !important;
  }
  .stMarkdown code {
    background: #EEF2FF !important; color: #4338CA !important;
    border-radius: 4px !important; padding: 0.1rem 0.4rem !important;
    font-family: 'Courier New', Courier, monospace !important;
  }

  hr { border: none !important; border-top: 1px solid #E2E8F0 !important; margin: 1.2rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

GENERATE_AGENTS = [
    ("clarify", "Gap Clarification Agent", "Identifying missing context and working assumptions"),
    ("nfr", "NFR Generation Agent", "Generating NFRs from the system description"),
    ("score", "Scoring & Priority Agent", "Scoring NFRs by business risk and complexity"),
    ("test", "Test Criteria Agent", "Generating test acceptance criteria"),
    ("conflict", "Conflict Detection Agent", "Identifying conflicts and tensions"),
    ("remediate", "Remediation Agent", "Improving weak, risky, or ambiguous NFRs"),
    ("compliance", "Compliance Mapping Agent", "Mapping NFRs to relevant control frameworks"),
]

VALIDATE_AGENTS = [
    ("clarify", "Gap Clarification Agent", "Identifying missing context affecting the review"),
    ("validate", "NFR Validation Agent", "Reviewing NFRs and identifying gaps"),
    ("remediate", "Remediation Agent", "Rewriting weak or vague NFRs"),
    ("compliance", "Compliance Mapping Agent", "Mapping NFRs to relevant control frameworks"),
]


def render_agent_cards(agent_defs: list[tuple[str, str, str]], states: dict):
    """Render progress cards for the provided agent set."""
    html = ""
    for key, label, description in agent_defs:
        state = states.get(key, "waiting")
        icon = {"waiting": "&#9675;", "running": "&#9673;", "done": "&#9679;"}[state]
        html += f"""
        <div class="agent-card {state}">
          <span class="dot"></span>
          <span><strong>{icon} {label}</strong> - {description}</span>
        </div>"""
    return html


def count_nfrs(nfr_text: str) -> int:
    import re
    return len(re.findall(r'NFR-\d+', nfr_text))


def count_critical(score_text: str) -> int:
    return score_text.upper().count("CRITICAL")


def render_redaction_preview(
    title: str,
    result: RedactionResult,
    key: str,
    height: int = 140,
) -> None:
    """Render a compact preview of sanitized input."""
    with st.expander(title, expanded=False):
        st.caption(summarize_redaction(result))
        st.text_area(
            f"{title} text",
            value=result.redacted_text,
            height=height,
            key=key,
            disabled=True,
            label_visibility="collapsed",
        )


def record_usage(agent_key: str, label: str, result) -> None:
    """Persist per-agent usage and estimated cost for the current run."""
    usage = dict(result.usage)
    st.session_state.usage_stats[agent_key] = {
        "label": label,
        "model": result.model,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "cached_tokens": usage.get("cached_tokens", 0),
        "reasoning_tokens": usage.get("reasoning_tokens", 0),
        "estimated_cost": estimate_usage_cost(usage),
    }


def usage_totals(usage_stats: dict) -> dict[str, float]:
    """Aggregate totals for the current run."""
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
        "estimated_cost": 0.0,
    }
    for item in usage_stats.values():
        totals["prompt_tokens"] += item.get("prompt_tokens", 0)
        totals["completion_tokens"] += item.get("completion_tokens", 0)
        totals["total_tokens"] += item.get("total_tokens", 0)
        totals["cached_tokens"] += item.get("cached_tokens", 0)
        totals["reasoning_tokens"] += item.get("reasoning_tokens", 0)
        totals["estimated_cost"] += item.get("estimated_cost", 0.0)
    return totals


def render_usage_summary(usage_stats: dict) -> None:
    """Render a compact token and cost summary."""
    if not usage_stats:
        return

    totals = usage_totals(usage_stats)
    st.caption(
        f"Usage: {totals['total_tokens']:,} total tokens "
        f"({totals['prompt_tokens']:,} in, {totals['completion_tokens']:,} out) "
        f"• Estimated cost: ${totals['estimated_cost']:.4f}"
    )

    rows = []
    for item in usage_stats.values():
        rows.append({
            "Agent": item["label"],
            "Model": item["model"],
            "Input": item["prompt_tokens"],
            "Output": item["completion_tokens"],
            "Total": item["total_tokens"],
            "Cached": item["cached_tokens"],
            "Cost (USD)": round(item["estimated_cost"], 4),
        })
    with st.expander("View usage details", expanded=False):
        st.caption(
            f"Estimated using {MODEL_NAME} text pricing, including cached input tokens where reported."
        )
        st.dataframe(rows, use_container_width=True, hide_index=True)


def default_run_filename(mode: str) -> str:
    """Return a timestamped default filename for a saved run."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"nfr_{mode}_{ts}.md"


def sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe markdown filename."""
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in filename.strip()
    )
    cleaned = cleaned.strip("._") or "nfr_run"
    if not cleaned.lower().endswith(".md"):
        cleaned = f"{cleaned}.md"
    return cleaned


def list_saved_runs() -> list[Path]:
    """List saved run files, newest first."""
    return sorted(SAVE_DIR.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)


def parse_saved_run(content: str) -> dict:
    """Parse a saved markdown run into app state."""
    sections = [section.strip() for section in content.strip().split("\n---\n")]
    if not sections:
        raise ValueError("The saved run is empty.")

    header = sections[0]
    if header.startswith("# NFR Pack"):
        mode = "generate"
        result_keys = [
            "clarify",
            "nfr",
            "score",
            "test",
            "conflict",
            "remediate",
            "compliance",
        ]
    elif header.startswith("# NFR Validation Pack"):
        mode = "validate"
        result_keys = ["clarify", "validate", "remediate", "compliance"]
    else:
        raise ValueError("Unsupported saved run format.")

    if "## System Description" not in header:
        raise ValueError("Saved run is missing a system description.")

    if len(sections) < len(result_keys) + 1:
        raise ValueError("Saved run is incomplete.")

    system_description = header.split("## System Description", 1)[1].strip()
    results = {
        key: sections[index + 1]
        for index, key in enumerate(result_keys)
    }
    return {
        "mode": mode,
        "system_description": system_description,
        "results": results,
    }


def save_run_file(filename: str, content: str) -> Path:
    """Persist a run pack to the saved runs directory."""
    safe_name = sanitize_filename(filename)
    path = SAVE_DIR / safe_name
    path.write_text(content, encoding="utf-8")
    return path


def load_saved_run(path: Path) -> None:
    """Load a saved run into session state."""
    parsed = parse_saved_run(path.read_text(encoding="utf-8"))
    mode = parsed["mode"]
    st.session_state.mode = mode
    st.session_state.system_description = parsed["system_description"]
    st.session_state.results = parsed["results"]
    st.session_state.pipeline_complete = True
    st.session_state.usage_stats = {}
    st.session_state.save_status = f"Loaded `{path.name}`"
    st.session_state.load_status = ""
    st.session_state.result_source = "loaded"

    if mode == "generate":
        st.session_state.agent_states = {key: "done" for key, _, _ in GENERATE_AGENTS}
        st.session_state.generate_save_name = default_run_filename("generate")
    else:
        st.session_state.agent_states = {key: "done" for key, _, _ in VALIDATE_AGENTS}
        st.session_state.validate_save_name = default_run_filename("validate")


def render_saved_runs_sidebar() -> None:
    """Render saved runs in the sidebar."""
    saved_runs = list_saved_runs()
    st.markdown("---")
    st.markdown("#### Saved Runs")
    if st.session_state.load_status:
        st.caption(st.session_state.load_status)
    if not saved_runs:
        st.caption("No saved runs yet.")
        return

    for path in saved_runs[:10]:
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d %b %Y %H:%M")
        st.markdown(
            f"""
            <div class="saved-run-card">
              <div class="title">{path.stem}</div>
              <div class="meta">{modified}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Run", use_container_width=True, key=f"load_saved_run_{path.name}"):
            try:
                load_saved_run(path)
                st.rerun()
            except ValueError as exc:
                st.session_state.load_status = f"Could not load `{path.name}`: {exc}"
                st.rerun()


def build_generate_pack() -> str:
    """Build the full generate-mode markdown pack."""
    return f"""# NFR Pack
Generated: {datetime.now().strftime("%d %B %Y at %H:%M")}

## System Description
{st.session_state.system_description}

---

{st.session_state.results.get("clarify", "")}

---

{st.session_state.results.get("nfr", "")}

---

{st.session_state.results.get("score", "")}

---

{st.session_state.results.get("test", "")}

---

{st.session_state.results.get("conflict", "")}

---

{st.session_state.results.get("remediate", "")}

---

{st.session_state.results.get("compliance", "")}
"""


def build_validate_pack() -> str:
    """Build the full validate-mode markdown pack."""
    return f"""# NFR Validation Pack
Generated: {datetime.now().strftime("%d %B %Y at %H:%M")}

## System Description
{st.session_state.system_description}

---

{st.session_state.results.get("clarify", "")}

---

{st.session_state.results.get("validate", "")}

---

{st.session_state.results.get("remediate", "")}

---

{st.session_state.results.get("compliance", "")}
"""


# â”€â”€ Session state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if "mode" not in st.session_state:
    st.session_state.mode = "generate"
if "agent_states" not in st.session_state:
    st.session_state.agent_states = {}
if "results" not in st.session_state:
    st.session_state.results = {}
if "system_description" not in st.session_state:
    st.session_state.system_description = ""
if "pipeline_complete" not in st.session_state:
    st.session_state.pipeline_complete = False
if "redaction_enabled" not in st.session_state:
    st.session_state.redaction_enabled = True
if "usage_stats" not in st.session_state:
    st.session_state.usage_stats = {}
if "save_status" not in st.session_state:
    st.session_state.save_status = ""
if "load_status" not in st.session_state:
    st.session_state.load_status = ""
if "result_source" not in st.session_state:
    st.session_state.result_source = "fresh"
if "generate_save_name" not in st.session_state:
    st.session_state.generate_save_name = default_run_filename("generate")
if "validate_save_name" not in st.session_state:
    st.session_state.validate_save_name = default_run_filename("validate")


# â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with st.sidebar:
    st.markdown("## NFR Studio")
    st.markdown("---")

    if st.button("Generate NFR Pack", use_container_width=True, type="primary"):
        st.session_state.mode = "generate"
        st.session_state.results = {}
        st.session_state.agent_states = {}
        st.session_state.usage_stats = {}
        st.session_state.save_status = ""
        st.session_state.load_status = ""
        st.session_state.result_source = "fresh"
        st.session_state.generate_save_name = default_run_filename("generate")
        st.session_state.pipeline_complete = False
        st.rerun()

    if st.button("Validate Existing NFRs", use_container_width=True):
        st.session_state.mode = "validate"
        st.session_state.results = {}
        st.session_state.agent_states = {}
        st.session_state.usage_stats = {}
        st.session_state.save_status = ""
        st.session_state.load_status = ""
        st.session_state.result_source = "fresh"
        st.session_state.validate_save_name = default_run_filename("validate")
        st.session_state.pipeline_complete = False
        st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.78rem; color:#94A3B8; line-height:1.8;">
    <strong style="color:#475569">Generate NFR Pack</strong><br>
    Runs 7 agents in sequence:<br>
    1. Gap Clarification<br>
    2. Generate NFRs<br>
    3. Score &amp; Prioritise<br>
    4. Test Acceptance Criteria<br>
    5. Conflict Detection<br>
    6. Remediation<br>
    7. Compliance Mapping<br><br>
    <strong style="color:#475569">Validate</strong><br>
    Gap analysis on your existing NFRs.
    </div>
    """, unsafe_allow_html=True)
    render_saved_runs_sidebar()


# â”€â”€ Main: Generate mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if st.session_state.mode == "generate":

    st.markdown("""
    <div class="header-block">
      <h1>NFR Studio</h1>
      <p>Describe your system and run the full 7-agent pipeline to produce a complete NFR pack.</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.pipeline_complete:
        st.markdown("#### Describe your system")
        st.caption("Include: system type, scale, users, integrations, platform, and known constraints. No client names or sensitive data needed.")
        redaction_enabled = st.checkbox(
            "Redact sensitive data before sending to OpenAI",
            key="redaction_enabled",
            help="Masks emails, URLs, domains, IPs, UUIDs, and secret-like values before model calls.",
        )

        system_description = st.text_area(
            "System description",
            height=200,
            placeholder="""Example: A high-volume e-commerce order management system processing around 50,000 orders per day. The system will be decomposed into four microservices (Orders, Payments, Inventory, Notifications) deployed on Azure Kubernetes Service in the UK South region. It will expose a REST API to approximately 20 third-party retail partners via Azure API Management. The system needs to handle Black Friday peak load of around 5x normal volume. It integrates with Azure Service Bus for async messaging and Azure SQL for transactional data.""",
            label_visibility="collapsed",
        )
        redacted_system_result = None
        if redaction_enabled and system_description.strip():
            redacted_system_result = redact_text(system_description.strip())
            render_redaction_preview(
                "Preview redacted system description",
                redacted_system_result,
                "generate_redaction_preview",
                height=180,
            )

        _, btn_col = st.columns([4, 1])
        with btn_col:
            run = st.button("Run Pipeline", type="primary", use_container_width=True)

        if run and system_description.strip():
            processed_system_description = system_description.strip()
            if redaction_enabled and redacted_system_result is not None:
                processed_system_description = redacted_system_result.redacted_text

            st.session_state.system_description = processed_system_description
            st.session_state.agent_states = {k: "waiting" for k, _, _ in GENERATE_AGENTS}
            st.session_state.results = {}
            st.session_state.usage_stats = {}
            st.session_state.save_status = ""
            st.session_state.load_status = ""
            st.session_state.result_source = "fresh"
            st.session_state.generate_save_name = default_run_filename("generate")

            st.markdown("---")
            st.markdown("#### Pipeline Progress")
            progress_placeholder = st.empty()

            def update_progress():
                progress_placeholder.markdown(
                    render_agent_cards(GENERATE_AGENTS, st.session_state.agent_states),
                    unsafe_allow_html=True
                )

            update_progress()

            try:
                from agents.nfr_agent import (
                    clarify_gaps,
                    detect_conflicts,
                    generate_nfrs,
                    generate_test_criteria,
                    map_compliance,
                    remediate_nfrs,
                    score_nfrs,
                )

                # Agent 0
                st.session_state.agent_states["clarify"] = "running"; update_progress()
                clarify_run = clarify_gaps(st.session_state.system_description)
                clarify_result = clarify_run.content
                st.session_state.results["clarify"] = clarify_result
                record_usage("clarify", "Gap Clarification Agent", clarify_run)
                st.session_state.agent_states["clarify"] = "done"; update_progress()

                # Agent 1
                st.session_state.agent_states["nfr"] = "running"; update_progress()
                nfr_input = f"""## Source System Description
{st.session_state.system_description}

## Gap Clarification Analysis
{clarify_result}

Use the source description as the primary input. Treat the clarification analysis as working assumptions and open questions."""
                nfr_run = generate_nfrs(nfr_input)
                nfr_result = nfr_run.content
                st.session_state.results["nfr"] = nfr_result
                record_usage("nfr", "NFR Generation Agent", nfr_run)
                st.session_state.agent_states["nfr"] = "done"; update_progress()

                # Agent 2
                st.session_state.agent_states["score"] = "running"; update_progress()
                score_run = score_nfrs(nfr_result)
                score_result = score_run.content
                st.session_state.results["score"] = score_result
                record_usage("score", "Scoring & Priority Agent", score_run)
                st.session_state.agent_states["score"] = "done"; update_progress()

                # Agent 3
                st.session_state.agent_states["test"] = "running"; update_progress()
                test_run = generate_test_criteria(nfr_result, score_result)
                test_result = test_run.content
                st.session_state.results["test"] = test_result
                record_usage("test", "Test Criteria Agent", test_run)
                st.session_state.agent_states["test"] = "done"; update_progress()

                # Agent 4
                st.session_state.agent_states["conflict"] = "running"; update_progress()
                conflict_run = detect_conflicts(nfr_result)
                conflict_result = conflict_run.content
                st.session_state.results["conflict"] = conflict_result
                record_usage("conflict", "Conflict Detection Agent", conflict_run)
                st.session_state.agent_states["conflict"] = "done"; update_progress()

                # Agent 5
                st.session_state.agent_states["remediate"] = "running"; update_progress()
                remediation_input = f"""## Gap Clarification
{clarify_result}

## Priority Analysis
{score_result}

## Conflict Analysis
{conflict_result}
"""
                remediation_run = remediate_nfrs(
                    st.session_state.system_description,
                    nfr_result,
                    remediation_input,
                )
                remediation_result = remediation_run.content
                st.session_state.results["remediate"] = remediation_result
                record_usage("remediate", "Remediation Agent", remediation_run)
                st.session_state.agent_states["remediate"] = "done"; update_progress()

                # Agent 6
                st.session_state.agent_states["compliance"] = "running"; update_progress()
                compliance_input = f"""## Priority Analysis
{score_result}

## Remediation Plan
{remediation_result}
"""
                compliance_run = map_compliance(
                    st.session_state.system_description,
                    nfr_result,
                    compliance_input,
                )
                compliance_result = compliance_run.content
                st.session_state.results["compliance"] = compliance_result
                record_usage("compliance", "Compliance Mapping Agent", compliance_run)
                st.session_state.agent_states["compliance"] = "done"; update_progress()

                st.session_state.pipeline_complete = True
                st.session_state.result_source = "fresh"
                st.rerun()

            except Exception as e:
                st.error(f"Pipeline error: {e}")
                raise

        elif run:
            st.warning("Please describe your system before running the pipeline.")

    # â”€â”€ Results â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if st.session_state.pipeline_complete and st.session_state.results:

        # Persistent agent cards
        st.markdown("#### Pipeline Progress")
        st.markdown(
            render_agent_cards(GENERATE_AGENTS, st.session_state.agent_states),
            unsafe_allow_html=True
        )

        st.markdown("---")

        # Metrics
        nfr_count = count_nfrs(st.session_state.results.get("nfr", ""))
        critical_count = count_critical(st.session_state.results.get("score", ""))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("NFRs Generated", nfr_count)
        m2.metric("Critical Priority", critical_count)
        m3.metric("Agents Run", len(GENERATE_AGENTS))
        m4.metric("Status", "Complete")

        # Tabs
        (
            tab_clarify,
            tab_nfr,
            tab_score,
            tab_test,
            tab_conflict,
            tab_remediate,
            tab_compliance,
            tab_download,
        ) = st.tabs([
            "Clarification",
            "NFRs",
            "Priority Matrix",
            "Test Criteria",
            "Conflicts",
            "Remediation",
            "Compliance",
            "Download",
        ])

        with tab_clarify:
            st.markdown(st.session_state.results.get("clarify", ""))

        with tab_nfr:
            st.markdown(st.session_state.results.get("nfr", ""))

        with tab_score:
            st.markdown(st.session_state.results.get("score", ""))

        with tab_test:
            st.markdown(st.session_state.results.get("test", ""))

        with tab_conflict:
            st.markdown(st.session_state.results.get("conflict", ""))

        with tab_remediate:
            st.markdown(st.session_state.results.get("remediate", ""))

        with tab_compliance:
            st.markdown(st.session_state.results.get("compliance", ""))

        with tab_download:
            st.markdown("#### Downloads")
            st.caption("Download individual outputs or the full combined pack.")

            # Combined pack
            combined = build_generate_pack()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            dl1, dl2, dl3 = st.columns(3)
            with dl1:
                st.download_button(
                    "Full NFR Pack (.md)",
                    data=combined,
                    file_name=f"nfr_pack_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.download_button(
                    "NFRs only (.md)",
                    data=st.session_state.results.get("nfr", ""),
                    file_name=f"nfrs_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.download_button(
                    "Clarification (.md)",
                    data=st.session_state.results.get("clarify", ""),
                    file_name=f"nfr_clarification_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with dl2:
                st.download_button(
                    "Priority Matrix (.md)",
                    data=st.session_state.results.get("score", ""),
                    file_name=f"nfr_priority_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.download_button(
                    "Test Criteria (.md)",
                    data=st.session_state.results.get("test", ""),
                    file_name=f"nfr_test_criteria_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with dl3:
                st.download_button(
                    "Conflicts (.md)",
                    data=st.session_state.results.get("conflict", ""),
                    file_name=f"nfr_conflicts_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.download_button(
                    "Remediation (.md)",
                    data=st.session_state.results.get("remediate", ""),
                    file_name=f"nfr_remediation_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.download_button(
                    "Compliance (.md)",
                    data=st.session_state.results.get("compliance", ""),
                    file_name=f"nfr_compliance_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

        if st.session_state.result_source != "loaded":
            st.markdown("---")
            st.markdown("#### Save this run")
            save_col, action_col = st.columns([3, 1])
            with save_col:
                st.text_input(
                    "Filename",
                    key="generate_save_name",
                    label_visibility="collapsed",
                )
            with action_col:
                if st.button("Save Run", use_container_width=True, key="save_generate_run"):
                    saved_path = save_run_file(
                        st.session_state.generate_save_name,
                        build_generate_pack(),
                    )
                    st.session_state.save_status = f"Saved run as `{saved_path.name}`"
                    st.rerun()
            if st.session_state.save_status:
                st.caption(st.session_state.save_status)

        # Run again button
        st.markdown("---")
        if st.button("Run again with different description"):
            st.session_state.pipeline_complete = False
            st.session_state.results = {}
            st.session_state.agent_states = {}
            st.session_state.usage_stats = {}
            st.session_state.save_status = ""
            st.session_state.generate_save_name = default_run_filename("generate")
            st.rerun()
        render_usage_summary(st.session_state.usage_stats)


# â”€â”€ Main: Validate mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
elif st.session_state.mode == "validate":

    st.markdown("""
    <div class="header-block">
      <h1>NFR Studio</h1>
      <p>Paste in your existing NFRs and get a gap analysis identifying what's missing, vague, or conflicting.</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.pipeline_complete:
        col_left, col_right = st.columns(2)
        redaction_enabled = st.checkbox(
            "Redact sensitive data before sending to OpenAI",
            key="redaction_enabled",
            help="Masks emails, URLs, domains, IPs, UUIDs, and secret-like values before model calls.",
        )
        with col_left:
            st.markdown("#### System description")
            system_description = st.text_area(
                "System description",
                height=280,
                placeholder="Describe the system the NFRs are for...",
                label_visibility="collapsed",
            )
        with col_right:
            st.markdown("#### Existing NFRs")
            existing_nfrs = st.text_area(
                "Existing NFRs",
                height=280,
                placeholder="Paste your existing NFRs here (any format - bullet points, table, prose)...",
                label_visibility="collapsed",
            )

        _, btn_col = st.columns([4, 1])
        with btn_col:
            run = st.button("Validate", type="primary", use_container_width=True)

        redacted_system_result = None
        redacted_nfrs_result = None
        if redaction_enabled and system_description.strip():
            redacted_system_result = redact_text(system_description.strip())
        if redaction_enabled and existing_nfrs.strip():
            redacted_nfrs_result = redact_text(existing_nfrs.strip())
        if redaction_enabled and (redacted_system_result or redacted_nfrs_result):
            with st.expander("Preview redacted inputs", expanded=False):
                if redacted_system_result is not None:
                    st.caption(f"System description: {summarize_redaction(redacted_system_result)}")
                    st.text_area(
                        "Redacted system description",
                        value=redacted_system_result.redacted_text,
                        height=150,
                        key="validate_redaction_system_preview",
                        disabled=True,
                        label_visibility="collapsed",
                    )
                if redacted_nfrs_result is not None:
                    st.caption(f"Existing NFRs: {summarize_redaction(redacted_nfrs_result)}")
                    st.text_area(
                        "Redacted existing NFRs",
                        value=redacted_nfrs_result.redacted_text,
                        height=180,
                        key="validate_redaction_nfr_preview",
                        disabled=True,
                        label_visibility="collapsed",
                    )

        if run and system_description.strip() and existing_nfrs.strip():
            processed_system_description = system_description.strip()
            processed_existing_nfrs = existing_nfrs.strip()
            if redaction_enabled and redacted_system_result is not None:
                processed_system_description = redacted_system_result.redacted_text
            if redaction_enabled and redacted_nfrs_result is not None:
                processed_existing_nfrs = redacted_nfrs_result.redacted_text

            st.session_state.system_description = processed_system_description
            st.session_state.agent_states = {k: "waiting" for k, _, _ in VALIDATE_AGENTS}
            st.session_state.results = {}
            st.session_state.usage_stats = {}
            st.session_state.save_status = ""
            st.session_state.load_status = ""
            st.session_state.result_source = "fresh"
            st.session_state.validate_save_name = default_run_filename("validate")

            st.markdown("---")
            st.markdown("#### Review Progress")
            progress_placeholder = st.empty()
            progress_placeholder.markdown(
                render_agent_cards(VALIDATE_AGENTS, st.session_state.agent_states),
                unsafe_allow_html=True,
            )


            try:
                from agents.nfr_agent import (
                    clarify_gaps,
                    map_compliance,
                    remediate_nfrs,
                    validate_nfrs,
                )

                st.session_state.agent_states["clarify"] = "running"
                progress_placeholder.markdown(
                    render_agent_cards(VALIDATE_AGENTS, st.session_state.agent_states),
                    unsafe_allow_html=True,
                )
                clarify_run = clarify_gaps(processed_system_description)
                clarify_result = clarify_run.content
                st.session_state.results["clarify"] = clarify_result
                record_usage("clarify", "Gap Clarification Agent", clarify_run)
                st.session_state.agent_states["clarify"] = "done"

                st.session_state.agent_states["validate"] = "running"
                progress_placeholder.markdown(
                    render_agent_cards(VALIDATE_AGENTS, st.session_state.agent_states),
                    unsafe_allow_html=True,
                )
                validation_system_context = f"""## Source System Description
{processed_system_description}

## Gap Clarification Analysis
{clarify_result}
"""
                validation_run = validate_nfrs(validation_system_context, processed_existing_nfrs)
                validation_result = validation_run.content
                st.session_state.results["validate"] = validation_result
                record_usage("validate", "NFR Validation Agent", validation_run)
                st.session_state.agent_states["validate"] = "done"

                st.session_state.agent_states["remediate"] = "running"
                progress_placeholder.markdown(
                    render_agent_cards(VALIDATE_AGENTS, st.session_state.agent_states),
                    unsafe_allow_html=True,
                )
                remediation_run = remediate_nfrs(
                    processed_system_description,
                    processed_existing_nfrs,
                    validation_result,
                )
                remediation_result = remediation_run.content
                st.session_state.results["remediate"] = remediation_result
                record_usage("remediate", "Remediation Agent", remediation_run)
                st.session_state.agent_states["remediate"] = "done"

                st.session_state.agent_states["compliance"] = "running"
                progress_placeholder.markdown(
                    render_agent_cards(VALIDATE_AGENTS, st.session_state.agent_states),
                    unsafe_allow_html=True,
                )
                compliance_run = map_compliance(
                    processed_system_description,
                    processed_existing_nfrs,
                    validation_result,
                )
                compliance_result = compliance_run.content
                st.session_state.results["compliance"] = compliance_result
                record_usage("compliance", "Compliance Mapping Agent", compliance_run)
                st.session_state.agent_states["compliance"] = "done"
                progress_placeholder.markdown(
                    render_agent_cards(VALIDATE_AGENTS, st.session_state.agent_states),
                    unsafe_allow_html=True,
                )

                st.session_state.pipeline_complete = True
                st.session_state.result_source = "fresh"
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                raise

        elif run:
            st.warning("Please fill in both fields before validating.")

    if st.session_state.pipeline_complete and st.session_state.results.get("validate"):
        st.markdown("#### Review Progress")
        st.markdown(
            render_agent_cards(VALIDATE_AGENTS, st.session_state.agent_states),
            unsafe_allow_html=True,
        )

        (
            tab_clarify,
            tab_validate,
            tab_remediate,
            tab_compliance,
            tab_download,
        ) = st.tabs([
            "Clarification",
            "Validation",
            "Remediation",
            "Compliance",
            "Download",
        ])

        with tab_clarify:
            st.markdown(st.session_state.results.get("clarify", ""))

        with tab_validate:
            st.markdown(st.session_state.results.get("validate", ""))

        with tab_remediate:
            st.markdown(st.session_state.results.get("remediate", ""))

        with tab_compliance:
            st.markdown(st.session_state.results.get("compliance", ""))

        with tab_download:
            st.markdown("#### Downloads")
            st.caption("Download the combined review output or any individual artefact.")

            combined = build_validate_pack()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dl1, dl2 = st.columns(2)

            with dl1:
                st.download_button(
                    "Full validation pack (.md)",
                    data=combined,
                    file_name=f"nfr_validation_pack_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.download_button(
                    "Validation report (.md)",
                    data=st.session_state.results.get("validate", ""),
                    file_name=f"nfr_validation_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            with dl2:
                st.download_button(
                    "Remediation plan (.md)",
                    data=st.session_state.results.get("remediate", ""),
                    file_name=f"nfr_validation_remediation_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.download_button(
                    "Compliance mapping (.md)",
                    data=st.session_state.results.get("compliance", ""),
                    file_name=f"nfr_validation_compliance_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

        if st.session_state.result_source != "loaded":
            st.markdown("---")
            st.markdown("#### Save this run")
            save_col, action_col = st.columns([3, 1])
            with save_col:
                st.text_input(
                    "Filename",
                    key="validate_save_name",
                    label_visibility="collapsed",
                )
            with action_col:
                if st.button("Save Run", use_container_width=True, key="save_validate_run"):
                    saved_path = save_run_file(
                        st.session_state.validate_save_name,
                        build_validate_pack(),
                    )
                    st.session_state.save_status = f"Saved run as `{saved_path.name}`"
                    st.rerun()
            if st.session_state.save_status:
                st.caption(st.session_state.save_status)

        st.markdown("---")
        if st.button("Validate different NFRs"):
            st.session_state.pipeline_complete = False
            st.session_state.results = {}
            st.session_state.agent_states = {}
            st.session_state.usage_stats = {}
            st.session_state.save_status = ""
            st.session_state.validate_save_name = default_run_filename("validate")
            st.rerun()
        render_usage_summary(st.session_state.usage_stats)
