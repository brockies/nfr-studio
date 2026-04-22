"""Shared loader for configurable assessment pack/profile definitions."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).with_name("config") / "assessment_definitions.json"


@lru_cache(maxsize=1)
def load_assessment_catalog() -> dict[str, list[dict[str, Any]]]:
    """Load framework pack and industry profile definitions from JSON config."""

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    framework_packs = payload.get("framework_packs", [])
    industry_profiles = payload.get("industry_profiles", [])

    if not isinstance(framework_packs, list) or not isinstance(industry_profiles, list):
        raise ValueError("Assessment definition config is malformed.")

    return {
        "framework_packs": framework_packs,
        "industry_profiles": industry_profiles,
    }
