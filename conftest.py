from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CALCULATOR = ROOT / "calculator"


def _ensure_path(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


_ensure_path(ROOT)
_ensure_path(CALCULATOR)
