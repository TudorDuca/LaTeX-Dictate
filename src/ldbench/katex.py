"""Optional render check with KaTeX (needs Node.js and `npm install` in tools/katex)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

KATEX_DIR = Path(__file__).resolve().parents[2] / "tools" / "katex"


def katex_available() -> bool:
    return shutil.which("node") is not None and (KATEX_DIR / "node_modules" / "katex").exists()


def renders(formulas: list[str]) -> list[bool] | None:
    """Whether each formula renders; None if the checker is not installed."""
    if not katex_available():
        return None
    if not formulas:
        return []
    proc = subprocess.run(
        ["node", str(KATEX_DIR / "check.mjs")],
        input=json.dumps(formulas),
        capture_output=True,
        text=True,
        cwd=KATEX_DIR,
        check=True,
    )
    return json.loads(proc.stdout)
