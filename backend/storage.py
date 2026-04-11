"""Saved-run and markdown-pack helpers for the API backend."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

from .models import RunCounts, RunPayload, SavedRunSummary


SAVE_DIR = Path("saved_runs")
SAVE_DIR.mkdir(exist_ok=True)

GENERATE_AGENT_COUNT = 7
VALIDATE_AGENT_COUNT = 4


def sanitize_project_slug(project_name: str) -> str:
    """Return a filesystem-safe project slug for default filenames."""

    cleaned = "".join(
        char.lower() if char.isalnum() or char in {"-", "_"} else "_"
        for char in project_name.strip()
    )
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("._")


def default_run_filename(mode: str, project_name: str = "", refined: bool = False) -> str:
    """Create a timestamped default run filename."""

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_slug = sanitize_project_slug(project_name)
    prefix = f"{project_slug}__" if project_slug else ""
    middle = f"nfr_{mode}_refined" if refined else f"nfr_{mode}"
    return f"{prefix}{middle}_{ts}.md"


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


def count_nfrs(content: str) -> int:
    """Count unique NFR ids in markdown output."""

    return len(set(re.findall(r"\bNFR-\d+\b", content or "")))


def count_critical(content: str) -> int:
    """Count CRITICAL priority entries in the scoring output."""

    return len(re.findall(r"\|\s*CRITICAL\s*\|", content or "", flags=re.IGNORECASE))


def build_counts(mode: str, results: dict[str, str]) -> RunCounts:
    """Derive quick dashboard metrics for a run."""

    if mode == "generate":
        return RunCounts(
            nfr_count=count_nfrs(results.get("nfr", "")),
            critical_count=count_critical(results.get("score", "")),
            agents_run=GENERATE_AGENT_COUNT,
        )

    return RunCounts(
        nfr_count=count_nfrs(results.get("validate", "")),
        critical_count=count_critical(results.get("validate", "")),
        agents_run=VALIDATE_AGENT_COUNT,
    )


def build_generate_pack(run: RunPayload) -> str:
    """Build the full generate-mode markdown pack."""

    project_section = ""
    if run.project_name.strip():
        project_section = f"""
## Project
{run.project_name.strip()}
"""
    attachment_section = ""
    if run.attachment_context.strip():
        attachment_section = f"""
{run.attachment_context.strip()}
"""

    kb_section = ""
    if getattr(run, "rag_sources", None):
        project_ids = sorted({item.project_id for item in run.rag_sources if item.project_id})
        if project_ids:
            kb_section = f"""
## Knowledge Base Insights
Based on insights from: {", ".join(project_ids)}
"""

    return f"""# NFR Pack
Generated: {datetime.now().strftime("%d %B %Y at %H:%M")}
{project_section}
{attachment_section}

## System Description
{run.system_description}
{kb_section}

---

{run.results.get("clarify", "")}

---

{run.results.get("nfr", "")}

---

{run.results.get("score", "")}

---

{run.results.get("test", "")}

---

{run.results.get("conflict", "")}

---

{run.results.get("remediate", "")}

---

{run.results.get("compliance", "")}
"""


def build_validate_pack(run: RunPayload) -> str:
    """Build the full validate-mode markdown pack."""

    project_section = ""
    if run.project_name.strip():
        project_section = f"""
## Project
{run.project_name.strip()}
"""
    attachment_section = ""
    if run.attachment_context.strip():
        attachment_section = f"""
{run.attachment_context.strip()}
"""
    existing_nfrs_section = ""
    if run.existing_nfrs.strip():
        existing_nfrs_section = f"""
## Existing NFRs
{run.existing_nfrs}
"""

    return f"""# NFR Validation Pack
Generated: {datetime.now().strftime("%d %B %Y at %H:%M")}
{project_section}
{attachment_section}

## System Description
{run.system_description}
{existing_nfrs_section}

---

{run.results.get("clarify", "")}

---

{run.results.get("validate", "")}

---

{run.results.get("remediate", "")}

---

{run.results.get("compliance", "")}
"""


def build_pack(run: RunPayload) -> str:
    """Dispatch to the correct pack builder for the supplied run."""

    return build_generate_pack(run) if run.mode == "generate" else build_validate_pack(run)


def hydrate_pack(run: RunPayload) -> RunPayload:
    """Fill in derived counts and the full markdown pack on a run payload."""

    run.counts = build_counts(run.mode, run.results)
    run.pack_markdown = build_pack(run)
    return run


def extract_header_section(header: str, title: str) -> str:
    """Extract a named markdown section from the saved-run header."""

    pattern = rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, header.strip())
    if not match:
        return ""
    return match.group(1).strip()


def parse_saved_run(content: str) -> dict[str, Any]:
    """Parse a saved markdown run into a transport-friendly structure."""

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

    system_description = extract_header_section(header, "System Description")
    if not system_description:
        raise ValueError("Saved run is missing a system description.")

    parsed: dict[str, Any] = {
        "mode": mode,
        "system_description": system_description,
        "results": {
            key: sections[index + 1]
            for index, key in enumerate(result_keys)
        },
        "project_name": extract_header_section(header, "Project"),
        "attachment_context": "",
        "existing_nfrs": "",
    }
    attachment_context = extract_header_section(header, "Supporting Attachments")
    if attachment_context:
        parsed["attachment_context"] = f"## Supporting Attachments\n{attachment_context}"
    if mode == "validate":
        parsed["existing_nfrs"] = extract_header_section(header, "Existing NFRs")
    return parsed


def read_saved_run_summary(path: Path) -> dict[str, str]:
    """Return lightweight metadata for rendering the saved-run list."""

    try:
        content = path.read_text(encoding="utf-8")
        header = content.split("\n---\n", 1)[0]
        project_name = extract_header_section(header, "Project")
        mode_label = "Validate" if header.startswith("# NFR Validation Pack") else "Generate"
    except OSError:
        project_name = ""
        mode_label = "Saved"
    return {
        "project_name": project_name,
        "mode_label": mode_label,
    }


def build_saved_run_card_title(summary: dict[str, str], path: Path) -> str:
    """Return a short title for the saved-run list."""

    mode_label = summary.get("mode_label", "Saved")
    is_refined = "_refined_" in path.stem.lower()
    return f"{mode_label} refined run" if is_refined else f"{mode_label} run"


def list_saved_runs() -> list[SavedRunSummary]:
    """List saved run files, newest first."""

    paths = sorted(SAVE_DIR.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
    items: list[SavedRunSummary] = []
    for path in paths[:25]:
        summary = read_saved_run_summary(path)
        raw_mode = "validate" if summary["mode_label"] == "Validate" else "generate"
        items.append(
            SavedRunSummary(
                file_name=path.name,
                project_name=summary["project_name"],
                mode=raw_mode,
                mode_label=summary["mode_label"],
                kind_label=build_saved_run_card_title(summary, path),
                modified=datetime.fromtimestamp(path.stat().st_mtime).strftime("%d %b %Y %H:%M"),
            )
        )
    return items


def save_run_file(filename: str, run: RunPayload) -> Path:
    """Persist a run pack to disk."""

    safe_name = sanitize_filename(filename)
    path = SAVE_DIR / safe_name
    path.write_text(build_pack(run), encoding="utf-8")
    return path


def load_saved_run(filename: str) -> tuple[Path, RunPayload]:
    """Load a saved run from disk and convert it to the transport model."""

    safe_name = sanitize_filename(filename)
    path = SAVE_DIR / safe_name
    if not path.exists():
        raise FileNotFoundError(f"`{safe_name}` was not found.")

    content = path.read_text(encoding="utf-8")
    parsed = parse_saved_run(content)
    run = RunPayload(
        mode=parsed["mode"],
        system_description=parsed["system_description"],
        existing_nfrs=parsed.get("existing_nfrs", ""),
        project_name=parsed.get("project_name", ""),
        attachment_context=parsed.get("attachment_context", ""),
        results=parsed["results"],
        agent_states={key: "done" for key in parsed["results"].keys()},
        result_source="loaded",
        pack_markdown=content,
    )
    run.counts = build_counts(run.mode, run.results)
    return path, run
