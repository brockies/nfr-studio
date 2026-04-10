"""Helpers for extracting useful text from uploaded supporting attachments."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path


MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 12000
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".log",
    ".sql",
    ".ini",
    ".cfg",
    ".conf",
    ".svg",
}
TEXT_MEDIA_TYPES = {
    "application/json",
    "application/xml",
    "application/yaml",
    "application/x-yaml",
    "image/svg+xml",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class ExtractedAttachment:
    """Attachment payload prepared for downstream summarisation."""

    name: str
    media_type: str
    kind: str
    content_text: str = ""
    binary_data: bytes = b""
    truncated: bool = False
    extraction_note: str = ""


def extract_uploaded_attachment(uploaded_file) -> ExtractedAttachment:
    """Extract text or binary image content from an uploaded file."""
    name = getattr(uploaded_file, "name", "") or "attachment"
    suffix = Path(name).suffix.lower()
    media_type = getattr(uploaded_file, "type", "") or _guess_media_type(suffix)
    payload = uploaded_file.getvalue()

    if len(payload) > MAX_ATTACHMENT_BYTES:
        raise ValueError(f"`{name}` is larger than 8 MB.")

    if suffix == ".pdf" or media_type == "application/pdf":
        text = _extract_pdf_text(payload)
        trimmed_text, truncated = _trim_text(text)
        return ExtractedAttachment(
            name=name,
            media_type="application/pdf",
            kind="document",
            content_text=trimmed_text,
            truncated=truncated,
            extraction_note="Extracted from PDF pages.",
        )

    if suffix in TEXT_EXTENSIONS or media_type.startswith("text/") or media_type in TEXT_MEDIA_TYPES:
        text = _decode_text(payload)
        trimmed_text, truncated = _trim_text(text)
        return ExtractedAttachment(
            name=name,
            media_type=media_type,
            kind="document",
            content_text=trimmed_text,
            truncated=truncated,
            extraction_note="Read as text content.",
        )

    if suffix in IMAGE_EXTENSIONS or media_type.startswith("image/"):
        return ExtractedAttachment(
            name=name,
            media_type=media_type,
            kind="image",
            binary_data=payload,
            extraction_note="Analysed as a visual attachment.",
        )

    raise ValueError(
        f"`{name}` is not a supported attachment type. Use PDF, text, markdown, CSV, JSON, YAML, SVG, PNG, JPG, or WEBP."
    )


def supported_upload_types() -> list[str]:
    """Return file extensions accepted by the upload widgets."""
    return ["pdf", "txt", "md", "markdown", "csv", "json", "yaml", "yml", "svg", "png", "jpg", "jpeg", "webp"]


def _extract_pdf_text(payload: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF attachments require `pypdf`. Run `pip install -r requirements.txt`.") from exc

    reader = PdfReader(BytesIO(payload))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    combined = "\n\n".join(page for page in pages if page)
    if not combined.strip():
        raise ValueError("The PDF does not contain extractable text.")
    return combined


def _decode_text(payload: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("The text attachment could not be decoded.")


def _trim_text(text: str) -> tuple[str, bool]:
    collapsed = text.strip()
    if not collapsed:
        raise ValueError("The attachment does not contain any usable text.")
    if len(collapsed) <= MAX_TEXT_CHARS:
        return collapsed, False
    return collapsed[:MAX_TEXT_CHARS].rstrip(), True


def _guess_media_type(suffix: str) -> str:
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".txt", ".md", ".markdown", ".csv", ".log", ".sql", ".ini", ".cfg", ".conf"}:
        return "text/plain"
    if suffix == ".json":
        return "application/json"
    if suffix in {".yaml", ".yml"}:
        return "application/yaml"
    if suffix == ".svg":
        return "image/svg+xml"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"
