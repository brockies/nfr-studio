"""Framework pack definitions used to bias compliance analysis."""

from __future__ import annotations

from dataclasses import dataclass

from .assessment_catalog import load_assessment_catalog

@dataclass(frozen=True)
class FrameworkPackDefinition:
    key: str
    label: str
    description: str
    frameworks: tuple[str, ...]
    guidance: str


DEFAULT_FRAMEWORK_PACK = "core_saas"

def _load_framework_packs() -> dict[str, FrameworkPackDefinition]:
    items: dict[str, FrameworkPackDefinition] = {}
    for entry in load_assessment_catalog()["framework_packs"]:
        pack = FrameworkPackDefinition(
            key=str(entry["key"]),
            label=str(entry["label"]),
            description=str(entry["description"]),
            frameworks=tuple(str(item) for item in entry.get("frameworks", [])),
            guidance=str(entry["guidance"]),
        )
        items[pack.key] = pack
    return items


FRAMEWORK_PACKS: dict[str, FrameworkPackDefinition] = _load_framework_packs()


def get_framework_pack(pack_key: str | None) -> FrameworkPackDefinition:
    """Return the selected pack, defaulting safely when the key is unknown."""

    normalized = (pack_key or DEFAULT_FRAMEWORK_PACK).strip().lower()
    return FRAMEWORK_PACKS.get(normalized, FRAMEWORK_PACKS[DEFAULT_FRAMEWORK_PACK])


def framework_pack_options() -> list[dict[str, str]]:
    """Return lightweight pack metadata for clients."""

    return [
        {
            "key": pack.key,
            "label": pack.label,
            "description": pack.description,
        }
        for pack in FRAMEWORK_PACKS.values()
    ]
