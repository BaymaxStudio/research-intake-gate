#!/usr/bin/env python3
"""Validate staged research and promote only human-reviewed claims."""

from __future__ import annotations

import argparse
import copy
import html
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "0.1.0"
SOURCE_TYPES = {"official_page", "official_pdf", "search_snippet", "third_party", "other"}
ACCESS_STATES = {"accessed_body", "blocked", "not_found", "snippet_only"}
RELATIONS = {"supports", "contradicts", "context"}
GAP_TYPES = {"not_found", "blocked", "low_yield", "conflict", "pending"}
DECISIONS = {"accept", "reject", "needs_followup"}
CLAIM_STATUSES = {"current", "reference"}
BLOCKED_FIELD_RE = re.compile(
    r"(^|_)(password|passwd|api_?key|secret|token|national_?id|passport|bank_?account)($|_)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)")
SECRET_VALUE_RE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[opusr]_[A-Za-z0-9]{20,})\b")


class DataError(Exception):
    """Raised when input cannot be interpreted safely."""


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    message: str
    claim_id: str | None = None
    source_id: str | None = None


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DataError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"Invalid JSON in {path}: {exc}") from exc


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DataError(f"{label} must be a JSON object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise DataError(f"{label} must be a JSON array")
    return value


def write_new(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "xb" if isinstance(content, bytes) else "x"
    kwargs = {} if isinstance(content, bytes) else {"encoding": "utf-8", "newline": "\n"}
    try:
        with path.open(mode, **kwargs) as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise DataError(f"Refusing to overwrite existing file: {path}") from exc


def check_outputs_absent(paths: Iterable[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise DataError("Refusing to overwrite existing files: " + ", ".join(existing))


def is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value[:10])
    except ValueError:
        return False
    return True


def duplicate_ids(items: Sequence[Any]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            item_id = item["id"]
            if item_id in seen:
                duplicates.add(item_id)
            seen.add(item_id)
    return duplicates


def scan_sensitive(value: Any, path: str = "$") -> list[Issue]:
    issues: list[Issue] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if BLOCKED_FIELD_RE.search(str(key)):
                issues.append(Issue("error", "SENSITIVE_FIELD", f"Blocked sensitive field at {child_path}"))
            issues.extend(scan_sensitive(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(scan_sensitive(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        if SECRET_VALUE_RE.search(value):
            issues.append(Issue("error", "CREDENTIAL_PATTERN", f"Credential-like value at {path}"))
        if EMAIL_RE.search(value):
            issues.append(Issue("warning", "EMAIL_PRESENT", f"Email-like value at {path}"))
        if PHONE_RE.search(value) and not is_iso_date(value):
            issues.append(Issue("warning", "PHONE_PRESENT", f"Phone-like value at {path}"))
    return issues


def validate_project_and_batch(project: dict[str, Any], batch: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if project.get("schemaVersion") != SCHEMA_VERSION:
        issues.append(Issue("error", "PROJECT_SCHEMA_VERSION", f"Expected project schema {SCHEMA_VERSION}"))
    current_period = project.get("currentPeriod")
    if not isinstance(current_period, str) or not current_period.strip():
        issues.append(Issue("error", "CURRENT_PERIOD", "project.currentPeriod must be a non-empty string"))

    targets = require_list(project.get("targets"), "project.targets")
    allowed_fields = require_list(project.get("allowedFields"), "project.allowedFields")
    target_ids = {item.get("id") for item in targets if isinstance(item, dict)}
    issues.extend(
        Issue("error", "TARGET_DUPLICATE", f"Duplicate target id: {item_id}")
        for item_id in sorted(duplicate_ids(targets))
    )

    if batch.get("schemaVersion") != SCHEMA_VERSION:
        issues.append(Issue("error", "BATCH_SCHEMA_VERSION", f"Expected batch schema {SCHEMA_VERSION}"))
    if not isinstance(batch.get("batchId"), str) or not batch["batchId"].strip():
        issues.append(Issue("error", "BATCH_ID", "batch.batchId must be a non-empty string"))
    if not is_iso_date(batch.get("createdAt")):
        issues.append(Issue("error", "BATCH_DATE", "batch.createdAt must start with an ISO date"))

    sources = require_list(batch.get("sources"), "batch.sources")
    claims = require_list(batch.get("claims"), "batch.claims")
    gaps = require_list(batch.get("gaps"), "batch.gaps")
    for source_id in sorted(duplicate_ids(sources)):
        issues.append(Issue("error", "SOURCE_DUPLICATE", f"Duplicate source id: {source_id}", source_id=source_id))
    for claim_id in sorted(duplicate_ids(claims)):
        issues.append(Issue("error", "CLAIM_DUPLICATE", f"Duplicate claim id: {claim_id}", claim_id=claim_id))
    for gap_id in sorted(duplicate_ids(gaps)):
        issues.append(Issue("error", "GAP_DUPLICATE", f"Duplicate gap id: {gap_id}"))

    source_map = {
        source["id"]: source
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }
    for source in sources:
        if not isinstance(source, dict):
            issues.append(Issue("error", "SOURCE_SHAPE", "Every source must be an object"))
            continue
        source_id = source.get("id") if isinstance(source.get("id"), str) else None
        if not source_id:
            issues.append(Issue("error", "SOURCE_ID", "Source id must be a non-empty string"))
        if not isinstance(source.get("url"), str) or not source.get("url", "").startswith(("https://", "http://")):
            issues.append(Issue("error", "SOURCE_URL", "Source URL must start with http:// or https://", source_id=source_id))
        if source.get("sourceType") not in SOURCE_TYPES:
            issues.append(Issue("error", "SOURCE_TYPE", "Unknown sourceType", source_id=source_id))
        if source.get("accessStatus") not in ACCESS_STATES:
            issues.append(Issue("error", "SOURCE_ACCESS", "Unknown accessStatus", source_id=source_id))
        if not is_iso_date(source.get("accessedAt")):
            issues.append(Issue("error", "SOURCE_ACCESSED_DATE", "accessedAt must be an ISO date", source_id=source_id))
        if source.get("publishedAt") is not None and not is_iso_date(source.get("publishedAt")):
            issues.append(Issue("error", "SOURCE_PUBLISHED_DATE", "publishedAt must be null or an ISO date", source_id=source_id))

    for claim in claims:
        if not isinstance(claim, dict):
            issues.append(Issue("error", "CLAIM_SHAPE", "Every claim must be an object"))
            continue
        claim_id = claim.get("id") if isinstance(claim.get("id"), str) else None
        if not claim_id:
            issues.append(Issue("error", "CLAIM_ID", "Claim id must be a non-empty string"))
        if claim.get("targetId") not in target_ids:
            issues.append(Issue("error", "CLAIM_TARGET", "Claim references an unknown target", claim_id=claim_id))
        if claim.get("field") not in allowed_fields:
            issues.append(Issue("error", "CLAIM_FIELD", "Claim uses a field outside project.allowedFields", claim_id=claim_id))
        if claim.get("status") not in CLAIM_STATUSES:
            issues.append(Issue("error", "CLAIM_STATUS", "Claim status must be current or reference", claim_id=claim_id))
        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            issues.append(Issue("error", "CLAIM_NO_EVIDENCE", "Claim has no evidence", claim_id=claim_id))
            evidence = []
        valid_current_support = False
        relations: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict):
                issues.append(Issue("error", "EVIDENCE_SHAPE", "Evidence must be an object", claim_id=claim_id))
                continue
            source_id = item.get("sourceId")
            relation = item.get("relation")
            if relation not in RELATIONS:
                issues.append(Issue("error", "EVIDENCE_RELATION", "Unknown evidence relation", claim_id=claim_id))
            else:
                relations.add(relation)
            if not isinstance(item.get("excerpt"), str) or not item.get("excerpt", "").strip():
                issues.append(Issue("error", "EVIDENCE_EXCERPT", "Evidence needs a short excerpt", claim_id=claim_id))
            elif len(item["excerpt"]) > 280:
                issues.append(Issue("warning", "LONG_EXCERPT", "Evidence excerpt exceeds 280 characters", claim_id=claim_id))
            if not isinstance(item.get("locator"), str) or not item.get("locator", "").strip():
                issues.append(Issue("error", "EVIDENCE_LOCATOR", "Evidence needs a locator", claim_id=claim_id))
            if source_id not in source_map:
                issues.append(Issue("error", "EVIDENCE_SOURCE", f"Unknown source id: {source_id}", claim_id=claim_id))
                continue
            source = source_map[source_id]
            if (
                relation == "supports"
                and source.get("accessStatus") == "accessed_body"
                and source.get("sourceType") != "search_snippet"
                and source.get("applicablePeriod") in {current_period, "evergreen"}
            ):
                valid_current_support = True
            if relation == "supports" and source.get("accessStatus") == "blocked":
                issues.append(Issue("error", "BLOCKED_SOURCE_SUPPORT", "A blocked source cannot support a claim", claim_id=claim_id, source_id=source_id))
        if claim.get("status") == "current" and not valid_current_support:
            issues.append(Issue("error", "CURRENT_SUPPORT", "Current claim lacks accessed body evidence for the current period", claim_id=claim_id))
        if "supports" in relations and "contradicts" in relations:
            issues.append(Issue("error", "CLAIM_CONFLICT", "Claim contains supporting and contradicting evidence", claim_id=claim_id))

    for gap in gaps:
        if not isinstance(gap, dict):
            issues.append(Issue("error", "GAP_SHAPE", "Every gap must be an object"))
            continue
        if gap.get("type") not in GAP_TYPES:
            issues.append(Issue("error", "GAP_TYPE", "Unknown gap type"))
        if gap.get("targetId") not in target_ids:
            issues.append(Issue("error", "GAP_TARGET", "Gap references an unknown target"))
        if gap.get("field") not in allowed_fields:
            issues.append(Issue("error", "GAP_FIELD", "Gap uses a field outside project.allowedFields"))
        source_ids = gap.get("sourceIds", [])
        if not isinstance(source_ids, list):
            issues.append(Issue("error", "GAP_SOURCES", "gap.sourceIds must be an array"))
            continue
        referenced = [source_map.get(source_id) for source_id in source_ids]
        if gap.get("type") == "not_found" and any(
            source and source.get("accessStatus") == "blocked" for source in referenced
        ):
            issues.append(Issue("error", "NOT_FOUND_FROM_BLOCKED", "A blocked page cannot prove that information is absent"))
        for source_id, source in zip(source_ids, referenced):
            if source is None:
                issues.append(Issue("error", "GAP_SOURCE", f"Unknown source id: {source_id}"))

    issues.extend(scan_sensitive({"project": project, "batch": batch}))
    return issues


def resolve_batch(project_dir: Path, batch_id: str | None) -> tuple[Path, dict[str, Any]]:
    staging = project_dir / "staging"
    if batch_id:
        path = staging / f"{batch_id}.json"
    else:
        candidates = sorted(staging.glob("*.json"))
        if len(candidates) != 1:
            raise DataError("Omit --batch only when staging contains exactly one JSON batch")
        path = candidates[0]
    batch = require_object(read_json(path), str(path))
    if batch.get("batchId") != path.stem:
        raise DataError(f"batchId must match filename: {path.name}")
    return path, batch


def issue_dict(issue: Issue) -> dict[str, Any]:
    return {key: value for key, value in asdict(issue).items() if value is not None}


def print_issues(issues: Sequence[Issue]) -> None:
    if not issues:
        print("PASS: no validation issues")
        return
    for issue in issues:
        refs = "".join(
            value for value in (
                f" claim={issue.claim_id}" if issue.claim_id else "",
                f" source={issue.source_id}" if issue.source_id else "",
            )
        )
        print(f"{issue.level.upper()} {issue.code}{refs}: {issue.message}")
    errors = sum(issue.level == "error" for issue in issues)
    warnings = sum(issue.level == "warning" for issue in issues)
    print(f"RESULT: {errors} error(s), {warnings} warning(s)")


def review_model(project: dict[str, Any], batch: dict[str, Any], issues: Sequence[Issue]) -> dict[str, Any]:
    target_map = {
        item.get("id"): item.get("name", item.get("id"))
        for item in project.get("targets", [])
        if isinstance(item, dict)
    }
    source_map = {
        item.get("id"): item for item in batch.get("sources", []) if isinstance(item, dict)
    }
    claims = []
    for claim in batch.get("claims", []):
        if not isinstance(claim, dict):
            continue
        claim_issues = [issue_dict(issue) for issue in issues if issue.claim_id == claim.get("id")]
        evidence = []
        for item in claim.get("evidence", []):
            if not isinstance(item, dict):
                continue
            evidence.append({**item, "source": source_map.get(item.get("sourceId"))})
        claims.append({**claim, "targetName": target_map.get(claim.get("targetId")), "evidence": evidence, "issues": claim_issues})
    return {
        "schemaVersion": SCHEMA_VERSION,
        "batchId": batch.get("batchId"),
        "projectName": project.get("name"),
        "currentPeriod": project.get("currentPeriod"),
        "summary": {
            "claimCount": len(batch.get("claims", [])),
            "sourceCount": len(batch.get("sources", [])),
            "gapCount": len(batch.get("gaps", [])),
            "errorCount": sum(issue.level == "error" for issue in issues),
            "warningCount": sum(issue.level == "warning" for issue in issues),
        },
        "claims": claims,
        "gaps": batch.get("gaps", []),
        "globalIssues": [issue_dict(issue) for issue in issues if issue.claim_id is None],
    }


def markdown_review(model: dict[str, Any]) -> str:
    lines = [
        f"# Review: {model['batchId']}",
        "",
        f"Project: {model.get('projectName')}  ",
        f"Current period: {model.get('currentPeriod')}  ",
        f"Claims: {model['summary']['claimCount']} | Sources: {model['summary']['sourceCount']} | "
        f"Errors: {model['summary']['errorCount']} | Warnings: {model['summary']['warningCount']}",
        "",
    ]
    for claim in model["claims"]:
        lines.extend([
            f"## {claim.get('id')}: {claim.get('targetName')} / {claim.get('field')}",
            "",
            f"- Status: `{claim.get('status')}`",
            f"- Value: `{json.dumps(claim.get('value'), ensure_ascii=False)}`",
        ])
        for evidence in claim.get("evidence", []):
            source = evidence.get("source") or {}
            lines.extend([
                f"- Evidence `{evidence.get('relation')}` from `{evidence.get('sourceId')}` "
                f"({source.get('accessStatus', 'unknown')}, {source.get('applicablePeriod', 'unknown')}): "
                f"{evidence.get('excerpt', '')}",
            ])
        for issue in claim.get("issues", []):
            lines.append(f"- {issue['level'].upper()} `{issue['code']}`: {issue['message']}")
        lines.append("")
    if model.get("gaps"):
        lines.extend(["## Gaps", ""])
        for gap in model["gaps"]:
            lines.append(f"- `{gap.get('type')}` {gap.get('targetId', '')}: {gap.get('note', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def html_review(model: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value), quote=True)

    cards = []
    for claim in model["claims"]:
        evidence_html = "".join(
            "<li><span class='relation'>"
            + esc(item.get("relation"))
            + "</span> <code>"
            + esc(item.get("sourceId"))
            + "</code> · "
            + esc((item.get("source") or {}).get("accessStatus", "unknown"))
            + " · “"
            + esc(item.get("excerpt", ""))
            + "”</li>"
            for item in claim.get("evidence", [])
        )
        issue_html = "".join(
            f"<li class='{esc(item['level'])}'>{esc(item['level'].upper())} <code>{esc(item['code'])}</code>: {esc(item['message'])}</li>"
            for item in claim.get("issues", [])
        ) or "<li class='pass'>No claim-specific issues</li>"
        search_text = " ".join(
            str(value) for value in (claim.get("id"), claim.get("targetName"), claim.get("field"), claim.get("value"))
        )
        cards.append(
            f"<article class='claim' data-search='{esc(search_text.lower())}' tabindex='0'>"
            f"<header><span>{esc(claim.get('targetName'))}</span><code>{esc(claim.get('field'))}</code></header>"
            f"<h2>{esc(claim.get('id'))}</h2><pre>{esc(json.dumps(claim.get('value'), ensure_ascii=False, indent=2))}</pre>"
            f"<h3>Evidence</h3><ul>{evidence_html}</ul><h3>Checks</h3><ul>{issue_html}</ul></article>"
        )
    summary = model["summary"]
    model_json = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Research review · {esc(model['batchId'])}</title>
<style>
:root{{--paper:#f5f1e8;--ink:#17201b;--muted:#657169;--line:#cbd1c8;--accent:#0b6b50;--warn:#9a5b00;--error:#a12a2a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,sans-serif}}
main{{max-width:1080px;margin:auto;padding:32px 20px 64px}}.mast{{border-bottom:2px solid var(--ink);padding-bottom:20px}}
h1{{font:700 clamp(2rem,6vw,4.5rem)/.95 ui-serif,Georgia,serif;margin:.2em 0}}.meta{{display:flex;gap:16px;flex-wrap:wrap;color:var(--muted)}}
label{{display:block;margin:24px 0 12px;font-weight:700}}input{{width:100%;padding:12px;border:1px solid var(--line);background:#fff;font:inherit}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.claim{{background:#fff;border:1px solid var(--line);padding:18px;box-shadow:4px 4px 0 #dce1d9}}
.claim:focus{{outline:3px solid var(--accent);outline-offset:2px}}header{{display:flex;justify-content:space-between;gap:12px;color:var(--muted)}}
h2{{font:700 1.45rem ui-serif,Georgia,serif}}h3{{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;margin-top:20px}}pre{{white-space:pre-wrap;background:#edf0eb;padding:12px}}
li{{margin:.55em 0}}.relation{{color:var(--accent);font-weight:700}}.warning{{color:var(--warn)}}.error{{color:var(--error)}}.pass{{color:var(--accent)}}
.empty{{display:none;padding:24px;border:1px dashed var(--line)}}@media(max-width:680px){{main{{padding:20px 14px 48px}}.grid{{grid-template-columns:1fr}}header{{display:block}}}}
</style></head><body><main><section class="mast"><p>LOCAL REVIEW DOSSIER</p><h1>{esc(model['batchId'])}</h1>
<div class="meta"><span>{esc(model.get('projectName'))}</span><span>Period {esc(model.get('currentPeriod'))}</span>
<span>{summary['claimCount']} claims</span><span>{summary['errorCount']} errors</span><span>{summary['warningCount']} warnings</span></div></section>
<label for="filter">Filter claims</label><input id="filter" type="search" placeholder="Target, field, value, or claim ID" autocomplete="off">
<p class="empty" id="empty">No matching claims.</p><section class="grid" id="claims">{''.join(cards)}</section>
<script type="application/json" id="review-data">{model_json}</script><script>
const input=document.getElementById('filter');const cards=[...document.querySelectorAll('.claim')];const empty=document.getElementById('empty');
input.addEventListener('input',()=>{{const q=input.value.trim().toLowerCase();let shown=0;for(const card of cards){{const yes=!q||card.dataset.search.includes(q);card.hidden=!yes;if(yes)shown++}}empty.style.display=shown?'none':'block'}});
</script></main></body></html>"""


def decisions_template(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "batchId": batch.get("batchId"),
        "reviewer": "human-review-required",
        "reviewedAt": None,
        "decisions": [
            {"claimId": claim.get("id"), "decision": "needs_followup", "reason": ""}
            for claim in batch.get("claims", [])
            if isinstance(claim, dict)
        ],
    }


def sample_project(example: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if example == "admissions":
        target = {"id": "northbridge-university", "name": "Northbridge University"}
        field = "application_window"
        value = {"opens": "2026-10-01", "closes": "2026-12-15"}
        title = "2027 doctoral admissions notice"
        excerpt = "Applications for the 2027 doctoral intake run from 1 October to 15 December 2026."
    else:
        target = {"id": "harbor-city-school", "name": "Harbor City School"}
        field = "application_window"
        value = {"opens": "2026-09-01", "closes": "2026-11-30"}
        title = "2027 teaching recruitment notice"
        excerpt = "Applications for the 2027 teaching intake run from 1 September to 30 November 2026."
    batch_id = f"{example}-2027-01"
    project = {
        "schemaVersion": SCHEMA_VERSION,
        "name": f"Synthetic {example} intake",
        "currentPeriod": "2027",
        "allowedFields": ["application_window", "program_status", "contact"],
        "targets": [target],
    }
    batch = {
        "schemaVersion": SCHEMA_VERSION,
        "batchId": batch_id,
        "createdAt": "2026-08-30T00:00:00Z",
        "sources": [{
            "id": "source-official-2027",
            "url": f"https://example.invalid/{example}/2027-notice",
            "title": title,
            "sourceType": "official_page",
            "publishedAt": "2026-08-20",
            "accessedAt": "2026-08-30",
            "applicablePeriod": "2027",
            "accessStatus": "accessed_body",
        }],
        "claims": [{
            "id": "claim-application-window",
            "targetId": target["id"],
            "field": field,
            "value": value,
            "status": "current",
            "evidence": [{
                "sourceId": "source-official-2027",
                "relation": "supports",
                "excerpt": excerpt,
                "locator": "section: application timeline",
            }],
        }],
        "gaps": [],
    }
    return project, batch


def command_init(args: argparse.Namespace) -> int:
    target = Path(args.project_dir).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise DataError(f"Target directory is not empty: {target}")
    project, batch = sample_project(args.example or "admissions")
    if args.example is None:
        project = {
            "schemaVersion": SCHEMA_VERSION,
            "name": target.name,
            "currentPeriod": "2027",
            "allowedFields": ["replace_with_allowed_field"],
            "targets": [{"id": "replace-with-target-id", "name": "Replace with target name"}],
        }
        batch = None
    target.mkdir(parents=True, exist_ok=True)
    for folder in ("staging", "reviews", "approved", "reports"):
        (target / folder).mkdir(exist_ok=False)
    write_new(target / "project.json", json_text(project))
    if batch is not None:
        write_new(target / "staging" / f"{batch['batchId']}.json", json_text(batch))
    print(f"Created research project: {target}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    project = require_object(read_json(project_dir / "project.json"), "project.json")
    _, batch = resolve_batch(project_dir, args.batch)
    issues = validate_project_and_batch(project, batch)
    print_issues(issues)
    return 1 if any(issue.level == "error" for issue in issues) else 0


def command_review(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    project = require_object(read_json(project_dir / "project.json"), "project.json")
    _, batch = resolve_batch(project_dir, args.batch)
    issues = validate_project_and_batch(project, batch)
    model = review_model(project, batch, issues)
    stem = project_dir / "reviews" / f"{args.batch}-review"
    outputs = [stem.with_suffix(".json"), stem.with_suffix(".md"), stem.with_suffix(".html"), project_dir / "reviews" / f"{args.batch}-decisions.json"]
    check_outputs_absent(outputs)
    write_new(outputs[0], json_text(model))
    write_new(outputs[1], markdown_review(model))
    write_new(outputs[2], html_review(model))
    write_new(outputs[3], json_text(decisions_template(batch)))
    print(f"Wrote review dossier: {outputs[2]}")
    print_issues(issues)
    return 1 if any(issue.level == "error" for issue in issues) else 0


def load_decisions(path: Path, batch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    document = require_object(read_json(path), str(path))
    if document.get("batchId") != batch.get("batchId"):
        raise DataError("Decision batchId does not match staged batch")
    decisions = require_list(document.get("decisions"), "decisions")
    if duplicate_ids([{"id": item.get("claimId")} for item in decisions if isinstance(item, dict)]):
        raise DataError("Duplicate claimId in decisions")
    result: dict[str, dict[str, Any]] = {}
    for item in decisions:
        if not isinstance(item, dict) or item.get("decision") not in DECISIONS:
            raise DataError("Each decision must be accept, reject, or needs_followup")
        if not isinstance(item.get("reason"), str):
            raise DataError("Each review decision needs a string reason")
        if item.get("decision") in {"accept", "reject"} and not item["reason"].strip():
            raise DataError("Every accept or reject decision needs a reason")
        result[item.get("claimId")] = item
    return result


def command_promote(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    project = require_object(read_json(project_dir / "project.json"), "project.json")
    _, batch = resolve_batch(project_dir, args.batch)
    issues = validate_project_and_batch(project, batch)
    decisions_path = project_dir / "reviews" / f"{args.batch}-decisions.json"
    decisions_document = require_object(read_json(decisions_path), str(decisions_path))
    decisions = load_decisions(decisions_path, batch)
    claims = [claim for claim in batch.get("claims", []) if isinstance(claim, dict)]
    claim_ids = {claim.get("id") for claim in claims}
    if set(decisions) != claim_ids:
        print("ERROR REVIEW_COVERAGE: every staged claim needs exactly one decision")
        return 1
    pending = [claim_id for claim_id, item in decisions.items() if item["decision"] == "needs_followup"]
    if pending:
        print("ERROR REVIEW_PENDING: " + ", ".join(sorted(pending)))
        return 1
    reviewer = decisions_document.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip() or reviewer == "human-review-required":
        print("ERROR REVIEWER_REQUIRED: final review needs a named reviewer")
        return 1
    if not is_iso_date(decisions_document.get("reviewedAt")):
        print("ERROR REVIEW_DATE_REQUIRED: final review needs an ISO reviewedAt date")
        return 1
    accepted_ids = {claim_id for claim_id, item in decisions.items() if item["decision"] == "accept"}
    blocking = [issue for issue in issues if issue.level == "error" and (issue.claim_id is None or issue.claim_id in accepted_ids)]
    if blocking:
        print_issues(blocking)
        return 1
    accepted = [copy.deepcopy(claim) for claim in claims if claim.get("id") in accepted_ids]
    accepted_source_ids = {
        item.get("sourceId")
        for claim in accepted
        for item in claim.get("evidence", [])
        if isinstance(item, dict)
    }
    approved = {
        "schemaVersion": SCHEMA_VERSION,
        "batchId": batch.get("batchId"),
        "projectName": project.get("name"),
        "currentPeriod": project.get("currentPeriod"),
        "acceptedClaims": accepted,
        "sources": [source for source in batch.get("sources", []) if isinstance(source, dict) and source.get("id") in accepted_source_ids],
        "review": {
            "reviewer": decisions_document.get("reviewer"),
            "reviewedAt": decisions_document.get("reviewedAt"),
            "decisions": [decisions[claim_id] | {"claimId": claim_id} for claim_id in sorted(decisions)],
        },
    }
    output = project_dir / "approved" / f"{args.batch}.json"
    write_new(output, json_text(approved))
    print(f"Promoted {len(accepted)} accepted claim(s): {output}")
    return 0


def resolve_version(project_dir: Path, version_id: str) -> tuple[str, list[dict[str, Any]]]:
    approved_path = project_dir / "approved" / f"{version_id}.json"
    staging_path = project_dir / "staging" / f"{version_id}.json"
    if approved_path.exists():
        document = require_object(read_json(approved_path), str(approved_path))
        claims = require_list(document.get("acceptedClaims"), "acceptedClaims")
        return "approved", [item for item in claims if isinstance(item, dict)]
    if staging_path.exists():
        document = require_object(read_json(staging_path), str(staging_path))
        claims = require_list(document.get("claims"), "claims")
        return "staging", [item for item in claims if isinstance(item, dict)]
    raise DataError(f"Unknown batch or approved version: {version_id}")


def claim_key(claim: dict[str, Any]) -> str:
    return f"{claim.get('targetId')}::{claim.get('field')}"


def command_diff(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    from_kind, from_claims = resolve_version(project_dir, args.from_id)
    to_kind, to_claims = resolve_version(project_dir, args.to_id)
    before = {claim_key(claim): claim for claim in from_claims}
    after = {claim_key(claim): claim for claim in to_claims}
    added = [after[key] for key in sorted(after.keys() - before.keys())]
    removed = [before[key] for key in sorted(before.keys() - after.keys())]
    modified = []
    status_changes = []
    for key in sorted(before.keys() & after.keys()):
        if before[key].get("status") != after[key].get("status"):
            status_changes.append({"key": key, "from": before[key].get("status"), "to": after[key].get("status")})
        comparable_before = {k: v for k, v in before[key].items() if k != "status"}
        comparable_after = {k: v for k, v in after[key].items() if k != "status"}
        if comparable_before != comparable_after:
            modified.append({"key": key, "from": before[key], "to": after[key]})
    report = {
        "schemaVersion": SCHEMA_VERSION,
        "from": {"id": args.from_id, "kind": from_kind},
        "to": {"id": args.to_id, "kind": to_kind},
        "added": added,
        "removed": removed,
        "modified": modified,
        "statusChanges": status_changes,
    }
    stem = project_dir / "reports" / f"diff-{args.from_id}-to-{args.to_id}"
    outputs = [stem.with_suffix(".json"), stem.with_suffix(".md")]
    check_outputs_absent(outputs)
    write_new(outputs[0], json_text(report))
    markdown = (
        f"# Diff: {args.from_id} to {args.to_id}\n\n"
        f"- Added: {len(added)}\n- Removed: {len(removed)}\n- Modified: {len(modified)}\n"
        f"- Status changes: {len(status_changes)}\n"
    )
    write_new(outputs[1], markdown)
    print(markdown.rstrip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-gate", description="Audit staged AI research before human-approved promotion.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="create an empty project or a synthetic example")
    init_parser.add_argument("project_dir")
    init_parser.add_argument("--example", choices=("admissions", "recruitment"))
    init_parser.set_defaults(func=command_init)
    validate_parser = subparsers.add_parser("validate", help="validate staged research")
    validate_parser.add_argument("project_dir")
    validate_parser.add_argument("--batch")
    validate_parser.set_defaults(func=command_validate)
    review_parser = subparsers.add_parser("review", help="write JSON, Markdown, and offline HTML review files")
    review_parser.add_argument("project_dir")
    review_parser.add_argument("--batch", required=True)
    review_parser.set_defaults(func=command_review)
    promote_parser = subparsers.add_parser("promote", help="promote accepted claims after complete human review")
    promote_parser.add_argument("project_dir")
    promote_parser.add_argument("--batch", required=True)
    promote_parser.set_defaults(func=command_promote)
    diff_parser = subparsers.add_parser("diff", help="compare staged or approved versions")
    diff_parser.add_argument("project_dir")
    diff_parser.add_argument("--from", dest="from_id", required=True)
    diff_parser.add_argument("--to", dest="to_id", required=True)
    diff_parser.set_defaults(func=command_diff)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except DataError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    except (KeyError, TypeError) as exc:
        print(f"INPUT ERROR: malformed data ({exc})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
