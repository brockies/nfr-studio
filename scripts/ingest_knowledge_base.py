"""CLI helper to ingest /knowledge_base into ChromaDB for NFR Studio."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Disable anonymized product telemetry (avoids noisy telemetry errors in local dev).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from utils.rag_manager import RagUnavailable, ingest_knowledge_base  # noqa: E402


def main() -> None:
    try:
        result = ingest_knowledge_base()
        print(json.dumps(result, indent=2))
    except RagUnavailable as exc:
        print(json.dumps({"indexed": False, "reason": str(exc)}, indent=2))
    except Exception as exc:
        print(json.dumps({"indexed": False, "reason": f"Ingest failed: {exc}"}, indent=2))


if __name__ == "__main__":
    main()
