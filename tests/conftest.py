from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is importable so `import backend...` works in tests.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

