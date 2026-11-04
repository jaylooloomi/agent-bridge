"""Worker adapters for Antigravity, Codex, and Claude."""

from __future__ import annotations

import os
from pathlib import Path


def ensure_output_dir(output_dir: str | None = None) -> Path:
    """Resolve and create the target output directory for generated media/files."""
    if output_dir:
        p = Path(output_dir).expanduser().resolve()
    else:
        default_dir = os.environ.get("AGENT_BRIDGE_OUTPUT_DIR")
        if default_dir:
            p = Path(default_dir).expanduser().resolve()
        else:
            p = (Path.cwd() / "outputs").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p
