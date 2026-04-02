"""Deterministic redaction helpers for masking sensitive input values."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RedactionItem:
    """A single detected value and its replacement placeholder."""

    label: str
    original: str
    replacement: str
    name: str = ""


@dataclass(frozen=True)
class RedactionResult:
    """Container for redacted text and replacement metadata."""

    original_text: str
    redacted_text: str
    counts: dict[str, int]
    items: tuple[RedactionItem, ...]

    @property
    def changed(self) -> bool:
        return self.original_text != self.redacted_text

    @property
    def total_replacements(self) -> int:
        return sum(self.counts.values())


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "secret",
        re.compile(
            r"(?im)\b(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|password|secret|token)\b"
            r"(\s*(?::|=|\uFF1A|is\b)\s*)([^\s,;]+)"
        ),
    ),
    (
        "email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        "url",
        re.compile(r"\b(?:https?://|ftp://|www\.)[^\s<>'\"]+", re.IGNORECASE),
    ),
    (
        "ipv4",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    ),
    (
        "uuid",
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "domain",
        re.compile(
            r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b",
            re.IGNORECASE,
        ),
    ),
]


def redact_text(text: str) -> RedactionResult:
    """Replace common sensitive values with typed placeholders."""
    counts: dict[str, int] = {}
    items: list[RedactionItem] = []
    redacted = text

    for label, pattern in PATTERNS:
        if label == "secret":
            redacted = pattern.sub(
                lambda match: _replace_secret(match, label, counts, items),
                redacted,
            )
            continue

        redacted = pattern.sub(
            lambda match, current_label=label: _replace_token(
                match,
                current_label,
                counts,
                items,
            ),
            redacted,
        )

    return RedactionResult(
        original_text=text,
        redacted_text=redacted,
        counts=counts,
        items=tuple(items),
    )


def summarize_redaction(result: RedactionResult) -> str:
    """Build a short human-readable summary."""
    if not result.changed:
        return "No obvious sensitive values were detected."

    details = ", ".join(
        f"{label.replace('_', ' ').title()} x{count}"
        for label, count in sorted(result.counts.items())
    )
    return f"Redacted {result.total_replacements} item(s): {details}."


def describe_redaction_items(result: RedactionResult) -> list[str]:
    """Return a human-readable list of specific detected replacements."""
    descriptions: list[str] = []
    for item in result.items:
        if item.label == "secret" and item.name:
            descriptions.append(f"{item.name} value -> {item.replacement}")
            continue
        descriptions.append(f"{_shorten(item.original)} -> {item.replacement}")
    return descriptions


def _replace_token(
    match: re.Match[str],
    label: str,
    counts: dict[str, int],
    items: list[RedactionItem],
) -> str:
    counts[label] = counts.get(label, 0) + 1
    replacement = f"[{label.upper()}_{counts[label]:02d}]"
    items.append(
        RedactionItem(
            label=label,
            original=match.group(0),
            replacement=replacement,
        )
    )
    return replacement


def _replace_secret(
    match: re.Match[str],
    label: str,
    counts: dict[str, int],
    items: list[RedactionItem],
) -> str:
    counts[label] = counts.get(label, 0) + 1
    replacement = f"[{label.upper()}_{counts[label]:02d}]"
    items.append(
        RedactionItem(
            label=label,
            original=match.group(3),
            replacement=replacement,
            name=match.group(1),
        )
    )
    return f"{match.group(1)}{match.group(2)}{replacement}"


def _shorten(value: str, limit: int = 48) -> str:
    """Trim long values so the preview list stays compact."""
    if len(value) <= limit:
        return value
    return f"{value[:limit - 3]}..."
