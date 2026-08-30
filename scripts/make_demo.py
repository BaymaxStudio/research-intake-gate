#!/usr/bin/env python3
"""Reproduce the public demo from real CLI output and synthetic data."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "research_gate.py"
DOCS = ROOT / "docs"
WIDTH, HEIGHT = 1200, 680


def run(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def sanitize(text: str, project_dir: Path) -> str:
    return text.replace(str(project_dir), "<demo-project>").replace(str(project_dir.resolve()), "<demo-project>")


def wrap(text: str, width: int = 88) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if not raw:
            lines.append("")
            continue
        while len(raw) > width:
            split_at = raw.rfind(" ", 0, width)
            if split_at < 1:
                split_at = width
            lines.append(raw[:split_at])
            raw = raw[split_at:].lstrip()
        lines.append(raw)
    return lines


def frame(title: str, transcript: str, step: int, total: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#111814")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    small = ImageFont.load_default(size=18)
    draw.rounded_rectangle((32, 28, WIDTH - 32, HEIGHT - 28), radius=18, fill="#17221c", outline="#3d5548", width=2)
    draw.ellipse((58, 52, 74, 68), fill="#e85d4a")
    draw.ellipse((84, 52, 100, 68), fill="#e3ad39")
    draw.ellipse((110, 52, 126, 68), fill="#4fb06d")
    draw.text((154, 48), title, font=font, fill="#f4efe4")
    draw.text((WIDTH - 164, 50), f"{step}/{total}", font=small, fill="#85b99b")
    y = 104
    for line in wrap(transcript):
        color = "#f4efe4"
        if line.startswith("ERROR") or line.startswith("INPUT ERROR"):
            color = "#ff8b82"
        elif line.startswith("WARNING"):
            color = "#ffd27a"
        elif line.startswith("PASS") or line.startswith("Promoted"):
            color = "#79d99b"
        draw.text((62, y), line, font=small, fill=color)
        y += 27
        if y > HEIGHT - 64:
            break
    return image


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    transcript_sections: list[str] = []
    frames: list[Image.Image] = []
    with tempfile.TemporaryDirectory(prefix="research-gate-demo-") as temporary:
        project_dir = Path(temporary) / "project"
        steps: list[tuple[str, list[str]]] = [
            ("Create a synthetic intake project", ["init", str(project_dir), "--example", "admissions"]),
            ("Run deterministic evidence checks", ["validate", str(project_dir), "--batch", "admissions-2027-01"]),
            ("Generate the review dossier", ["review", str(project_dir), "--batch", "admissions-2027-01"]),
        ]
        for index, (title, args) in enumerate(steps, start=1):
            code, output = run(*args)
            clean = sanitize(output, project_dir)
            block = f"$ research-gate {' '.join(sanitize(arg, project_dir) for arg in args)}\n{clean}\nexit={code}"
            transcript_sections.append(block)
            frames.append(frame(title, block, index, 6))
            if code != 0:
                raise RuntimeError(block)

        decision_path = project_dir / "reviews" / "admissions-2027-01-decisions.json"
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        decision["reviewer"] = "Synthetic human review"
        decision["reviewedAt"] = "2026-08-30T12:00:00Z"
        decision["decisions"] = [{
            "claimId": "claim-application-window",
            "decision": "accept",
            "reason": "The current official notice and excerpt match the staged value."
        }]
        decision_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        human_block = "$ human review\naccept claim-application-window\nreason: current official notice matches the staged value"
        transcript_sections.append(human_block)
        frames.append(frame("Record a human decision", human_block, 4, 6))

        code, output = run("promote", str(project_dir), "--batch", "admissions-2027-01")
        clean = sanitize(output, project_dir)
        promote_block = f"$ research-gate promote <demo-project> --batch admissions-2027-01\n{clean}\nexit={code}"
        transcript_sections.append(promote_block)
        frames.append(frame("Promote accepted claims", promote_block, 5, 6))
        if code != 0:
            raise RuntimeError(promote_block)

        first = json.loads((project_dir / "staging" / "admissions-2027-01.json").read_text(encoding="utf-8"))
        second = json.loads(json.dumps(first))
        second["batchId"] = "admissions-2027-02"
        second["claims"][0]["value"]["closes"] = "2026-12-20"
        (project_dir / "staging" / "admissions-2027-02.json").write_text(
            json.dumps(second, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        code, output = run("diff", str(project_dir), "--from", "admissions-2027-01", "--to", "admissions-2027-02")
        clean = sanitize(output, project_dir)
        diff_block = f"$ research-gate diff <demo-project> --from admissions-2027-01 --to admissions-2027-02\n{clean}\nexit={code}"
        transcript_sections.append(diff_block)
        frames.append(frame("Compare approved and staged versions", diff_block, 6, 6))
        if code != 0:
            raise RuntimeError(diff_block)

        shutil.copyfile(project_dir / "reviews" / "admissions-2027-01-review.html", DOCS / "sample-review.html")
        shutil.copyfile(project_dir / "approved" / "admissions-2027-01.json", DOCS / "sample-approved.json")
        shutil.copyfile(
            project_dir / "reports" / "diff-admissions-2027-01-to-admissions-2027-02.json",
            DOCS / "sample-diff.json",
        )

    (DOCS / "demo-transcript.txt").write_text("\n\n".join(transcript_sections) + "\n", encoding="utf-8")
    frames[0].save(
        DOCS / "demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[1400, 1800, 1800, 1900, 1800, 2200],
        loop=0,
        optimize=False,
    )
    frames[-1].save(DOCS / "demo-final.png")
    print("Wrote docs/demo.gif and reproducible sample artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
