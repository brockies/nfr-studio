"""Industry profile definitions used to bias analysis across the workflow."""

from __future__ import annotations

from dataclasses import dataclass

from .assessment_catalog import load_assessment_catalog

@dataclass(frozen=True)
class IndustryProfileDefinition:
    key: str
    label: str
    description: str
    likely_frameworks: tuple[str, ...]
    likely_nfr_themes: tuple[str, ...]
    likely_evidence: tuple[str, ...]
    guidance: str


DEFAULT_INDUSTRY_PROFILE = "saas"

def _load_industry_profiles() -> dict[str, IndustryProfileDefinition]:
    items: dict[str, IndustryProfileDefinition] = {}
    for entry in load_assessment_catalog()["industry_profiles"]:
        profile = IndustryProfileDefinition(
            key=str(entry["key"]),
            label=str(entry["label"]),
            description=str(entry["description"]),
            likely_frameworks=tuple(str(item) for item in entry.get("likely_frameworks", [])),
            likely_nfr_themes=tuple(str(item) for item in entry.get("likely_nfr_themes", [])),
            likely_evidence=tuple(str(item) for item in entry.get("likely_evidence", [])),
            guidance=str(entry["guidance"]),
        )
        items[profile.key] = profile
    return items


INDUSTRY_PROFILES: dict[str, IndustryProfileDefinition] = _load_industry_profiles()


def get_industry_profile(profile_key: str | None) -> IndustryProfileDefinition:
    """Return the selected profile, defaulting safely when the key is unknown."""

    normalized = (profile_key or DEFAULT_INDUSTRY_PROFILE).strip().lower()
    return INDUSTRY_PROFILES.get(normalized, INDUSTRY_PROFILES[DEFAULT_INDUSTRY_PROFILE])


def industry_profile_options() -> list[dict[str, str]]:
    """Return lightweight profile metadata for clients."""

    return [
        {
            "key": profile.key,
            "label": profile.label,
            "description": profile.description,
        }
        for profile in INDUSTRY_PROFILES.values()
    ]


def render_industry_profile_context(profile_key: str | None) -> str:
    """Render a short markdown block describing the selected profile's bias."""

    profile = get_industry_profile(profile_key)
    lines = [
        "## Selected Industry Profile",
        f"Name: {profile.label}",
        f"Description: {profile.description}",
        "Likely frameworks:",
        *[f"- {item}" for item in profile.likely_frameworks],
        "Likely NFR themes:",
        *[f"- {item}" for item in profile.likely_nfr_themes],
        "Likely evidence artefacts:",
        *[f"- {item}" for item in profile.likely_evidence],
        f"Guidance: {profile.guidance}",
    ]
    return "\n".join(lines)
