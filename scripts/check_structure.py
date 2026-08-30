#!/usr/bin/env python3
"""Run repository-local structural checks without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "research-intake-gate" / "SKILL.md"


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    required = [
        SKILL,
        ROOT / "skills" / "research-intake-gate" / "agents" / "openai.yaml",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / "README.md",
        ROOT / "README.en.md",
        ROOT / "LICENSE",
        ROOT / "docs" / "demo.gif",
    ]
    for path in required:
        if not path.is_file():
            fail(f"Missing required file: {path.relative_to(ROOT)}", errors)

    if SKILL.exists():
        text = SKILL.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        if not match:
            fail("SKILL.md frontmatter is missing", errors)
        else:
            frontmatter = match.group(1)
            if not re.search(r"^name:\s*research-intake-gate\s*$", frontmatter, re.MULTILINE):
                fail("SKILL.md name is invalid", errors)
            description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
            if not description or len(description.group(1).strip()) < 80:
                fail("SKILL.md description is not discriminating enough", errors)
        if "[TODO" in text:
            fail("SKILL.md contains a TODO placeholder", errors)

    codex_path = ROOT / ".codex-plugin" / "plugin.json"
    claude_path = ROOT / ".claude-plugin" / "plugin.json"
    market_path = ROOT / ".claude-plugin" / "marketplace.json"
    for path in (codex_path, claude_path, market_path):
        if not path.exists():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}", errors)
            continue
        if path != market_path and document.get("name") != "research-intake-gate":
            fail(f"Plugin name mismatch in {path.relative_to(ROOT)}", errors)
        if path != market_path and document.get("version") != "0.1.0":
            fail(f"Plugin version mismatch in {path.relative_to(ROOT)}", errors)
        if path == market_path:
            plugins = document.get("plugins")
            if not isinstance(plugins, list) or len(plugins) != 1:
                fail("Claude marketplace must contain exactly one plugin", errors)
            elif plugins[0].get("name") != "research-intake-gate" or plugins[0].get("source") != "./":
                fail("Claude marketplace plugin entry is inconsistent", errors)

    for review_html in ROOT.glob("examples/*/reviews/*-review.html"):
        text = review_html.read_text(encoding="utf-8")
        if "<script src=" in text or "<link rel=" in text:
            fail(f"Review HTML loads an external asset: {review_html.relative_to(ROOT)}", errors)
        if 'id="review-data"' not in text or 'id="filter"' not in text:
            fail(f"Review HTML is missing review data or filter controls: {review_html.relative_to(ROOT)}", errors)

    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors))
        return 1
    print("PASS: repository structure and manifests are internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
