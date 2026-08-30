#!/usr/bin/env python3
"""Repository entry point for the packaged research gate CLI."""

from __future__ import annotations

import runpy
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "research-intake-gate"
    / "scripts"
    / "research_gate.py"
)

runpy.run_path(str(SCRIPT), run_name="__main__")
