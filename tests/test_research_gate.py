"""Behavior and regression tests for the research intake gate."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "research_gate.py"
CORE = ROOT / "skills" / "research-intake-gate" / "scripts" / "research_gate.py"
SPEC = importlib.util.spec_from_file_location("research_gate", CORE)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)


def base_documents() -> tuple[dict, dict]:
    project, batch = gate.sample_project("admissions")
    return copy.deepcopy(project), copy.deepcopy(batch)


def issue_codes(project: dict, batch: dict) -> set[str]:
    return {issue.code for issue in gate.validate_project_and_batch(project, batch)}


class ValidationTests(unittest.TestCase):
    def test_valid_batch_passes(self) -> None:
        project, batch = base_documents()
        self.assertEqual(issue_codes(project, batch), set())

    def test_old_period_cannot_support_current_claim(self) -> None:
        project, batch = base_documents()
        batch["sources"][0]["applicablePeriod"] = "2026"
        self.assertIn("CURRENT_SUPPORT", issue_codes(project, batch))

    def test_search_snippet_cannot_support_current_claim(self) -> None:
        project, batch = base_documents()
        batch["sources"][0]["sourceType"] = "search_snippet"
        batch["sources"][0]["accessStatus"] = "snippet_only"
        self.assertIn("CURRENT_SUPPORT", issue_codes(project, batch))

    def test_blocked_page_cannot_prove_absence(self) -> None:
        project, batch = base_documents()
        batch["sources"][0]["accessStatus"] = "blocked"
        batch["claims"] = []
        batch["gaps"] = [{
            "id": "gap-1",
            "targetId": "northbridge-university",
            "field": "program_status",
            "type": "not_found",
            "sourceIds": ["source-official-2027"],
            "note": "No result inferred from an inaccessible page.",
        }]
        issues = gate.validate_project_and_batch(project, batch)
        self.assertIn("NOT_FOUND_FROM_BLOCKED", {issue.code for issue in issues})
        self.assertEqual(sum(issue.code == "NOT_FOUND_FROM_BLOCKED" for issue in issues), 1)

    def test_claim_without_evidence_fails(self) -> None:
        project, batch = base_documents()
        batch["claims"][0]["evidence"] = []
        self.assertIn("CLAIM_NO_EVIDENCE", issue_codes(project, batch))

    def test_unknown_source_id_fails(self) -> None:
        project, batch = base_documents()
        batch["claims"][0]["evidence"][0]["sourceId"] = "missing"
        self.assertIn("EVIDENCE_SOURCE", issue_codes(project, batch))

    def test_source_must_be_scoped_to_claim_field(self) -> None:
        project, batch = base_documents()
        batch["sources"][0]["supportsFields"] = ["contact"]
        batch["claims"][0]["field"] = "program_status"
        batch["claims"][0]["value"] = "open"
        codes = issue_codes(project, batch)
        self.assertIn("SOURCE_FIELD_MISMATCH", codes)
        self.assertIn("CURRENT_SUPPORT", codes)

    def test_duplicate_source_and_claim_ids_fail(self) -> None:
        project, batch = base_documents()
        batch["sources"].append(copy.deepcopy(batch["sources"][0]))
        batch["claims"].append(copy.deepcopy(batch["claims"][0]))
        codes = issue_codes(project, batch)
        self.assertIn("SOURCE_DUPLICATE", codes)
        self.assertIn("CLAIM_DUPLICATE", codes)

    def test_conflicting_evidence_is_visible(self) -> None:
        project, batch = base_documents()
        contradiction = copy.deepcopy(batch["claims"][0]["evidence"][0])
        contradiction["relation"] = "contradicts"
        contradiction["excerpt"] = "The application window is suspended."
        batch["claims"][0]["evidence"].append(contradiction)
        self.assertIn("CLAIM_CONFLICT", issue_codes(project, batch))

    def test_sensitive_fields_block_and_contact_values_warn(self) -> None:
        project, batch = base_documents()
        batch["api_token"] = "do-not-store-this"
        batch["notes"] = "Contact research@example.org or +1 202 555 0188."
        issues = gate.validate_project_and_batch(project, batch)
        self.assertIn("SENSITIVE_FIELD", {issue.code for issue in issues if issue.level == "error"})
        warnings = {issue.code for issue in issues if issue.level == "warning"}
        self.assertIn("EMAIL_PRESENT", warnings)
        self.assertIn("PHONE_PRESENT", warnings)

    def test_iso_dates_are_not_phone_warnings(self) -> None:
        project, batch = base_documents()
        warnings = [issue for issue in gate.validate_project_and_batch(project, batch) if issue.code == "PHONE_PRESENT"]
        self.assertEqual(warnings, [])


class CommandTests(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=cwd or ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_example(self, parent: Path, name: str = "project") -> Path:
        project_dir = parent / name
        result = self.run_cli("init", str(project_dir), "--example", "admissions")
        self.assertEqual(result.returncode, 0, result.stderr)
        return project_dir

    def write_decisions(self, project_dir: Path, decisions: list[dict]) -> None:
        path = project_dir / "reviews" / "admissions-2027-01-decisions.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["reviewer"] = "Synthetic human review"
        document["reviewedAt"] = "2026-08-30T12:00:00Z"
        document["decisions"] = decisions
        path.write_text(gate.json_text(document), encoding="utf-8")

    def test_review_outputs_share_the_same_model_and_are_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            result = self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01")
            self.assertEqual(result.returncode, 0, result.stderr)
            review_json = json.loads((project_dir / "reviews" / "admissions-2027-01-review.json").read_text(encoding="utf-8"))
            review_html = (project_dir / "reviews" / "admissions-2027-01-review.html").read_text(encoding="utf-8")
            marker = '<script type="application/json" id="review-data">'
            embedded = review_html.split(marker, 1)[1].split("</script>", 1)[0]
            self.assertEqual(json.loads(embedded), review_json)
            self.assertNotIn("<script src=", review_html)
            self.assertNotIn("<link rel=", review_html)

    def test_markdown_and_html_show_global_warnings_and_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            staging_path = project_dir / "staging" / "admissions-2027-01.json"
            batch = json.loads(staging_path.read_text(encoding="utf-8"))
            batch["notes"] = "Review contact@example.org before reuse."
            batch["gaps"] = [{
                "id": "gap-low-yield",
                "targetId": "northbridge-university",
                "field": "program_status",
                "type": "low_yield",
                "sourceIds": ["source-official-2027"],
                "note": "The source did not resolve programme status."
            }]
            staging_path.write_text(gate.json_text(batch), encoding="utf-8")
            result = self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            markdown = (project_dir / "reviews" / "admissions-2027-01-review.md").read_text(encoding="utf-8")
            review_html = (project_dir / "reviews" / "admissions-2027-01-review.html").read_text(encoding="utf-8")
            for expected in ("EMAIL_PRESENT", "gap-low-yield", "source-official-2027", "accessed_body", "2027"):
                self.assertIn(expected, markdown)
                self.assertIn(expected, review_html)

    def test_pending_review_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            self.assertEqual(self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01").returncode, 0)
            result = self.run_cli("promote", str(project_dir), "--batch", "admissions-2027-01")
            self.assertEqual(result.returncode, 1)
            self.assertIn("REVIEW_PENDING", result.stdout)

    def test_rejected_invalid_claim_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            staging_path = project_dir / "staging" / "admissions-2027-01.json"
            batch = json.loads(staging_path.read_text(encoding="utf-8"))
            invalid = copy.deepcopy(batch["claims"][0])
            invalid["id"] = "claim-search-only"
            invalid["field"] = "program_status"
            invalid["value"] = "open"
            invalid["evidence"] = []
            batch["claims"].append(invalid)
            staging_path.write_text(gate.json_text(batch), encoding="utf-8")
            self.assertEqual(self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01").returncode, 1)
            self.write_decisions(project_dir, [
                {"claimId": "claim-application-window", "decision": "accept", "reason": "Official current notice checked."},
                {"claimId": "claim-search-only", "decision": "reject", "reason": "No accessed evidence."},
            ])
            result = self.run_cli("promote", str(project_dir), "--batch", "admissions-2027-01")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            approved = json.loads((project_dir / "approved" / "admissions-2027-01.json").read_text(encoding="utf-8"))
            self.assertEqual([claim["id"] for claim in approved["acceptedClaims"]], ["claim-application-window"])

    def test_repeat_promotion_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            self.assertEqual(self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01").returncode, 0)
            self.write_decisions(project_dir, [
                {"claimId": "claim-application-window", "decision": "accept", "reason": "Official current notice checked."}
            ])
            self.assertEqual(self.run_cli("promote", str(project_dir), "--batch", "admissions-2027-01").returncode, 0)
            second = self.run_cli("promote", str(project_dir), "--batch", "admissions-2027-01")
            self.assertEqual(second.returncode, 2)
            self.assertIn("Refusing to overwrite", second.stderr)

    def test_final_review_requires_reviewer_and_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            self.assertEqual(self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01").returncode, 0)
            path = project_dir / "reviews" / "admissions-2027-01-decisions.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["decisions"] = [{
                "claimId": "claim-application-window", "decision": "accept", "reason": "Evidence checked."
            }]
            path.write_text(gate.json_text(document), encoding="utf-8")
            result = self.run_cli("promote", str(project_dir), "--batch", "admissions-2027-01")
            self.assertEqual(result.returncode, 1)
            self.assertIn("REVIEWER_REQUIRED", result.stdout)

    def test_final_decision_requires_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            self.assertEqual(self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01").returncode, 0)
            self.write_decisions(project_dir, [{
                "claimId": "claim-application-window", "decision": "accept", "reason": ""
            }])
            result = self.run_cli("promote", str(project_dir), "--batch", "admissions-2027-01")
            self.assertEqual(result.returncode, 2)
            self.assertIn("needs a reason", result.stderr)

    def test_diff_reports_added_removed_modified_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.make_example(Path(tmp))
            first_path = project_dir / "staging" / "admissions-2027-01.json"
            first = json.loads(first_path.read_text(encoding="utf-8"))
            second = copy.deepcopy(first)
            second["batchId"] = "admissions-2027-02"
            second["claims"][0]["value"]["closes"] = "2026-12-20"
            second["claims"][0]["status"] = "reference"
            second["claims"].append({
                "id": "claim-program-status",
                "targetId": "northbridge-university",
                "field": "program_status",
                "value": "open",
                "status": "current",
                "evidence": copy.deepcopy(second["claims"][0]["evidence"]),
            })
            (project_dir / "staging" / "admissions-2027-02.json").write_text(gate.json_text(second), encoding="utf-8")
            result = self.run_cli("diff", str(project_dir), "--from", "admissions-2027-01", "--to", "admissions-2027-02")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((project_dir / "reports" / "diff-admissions-2027-01-to-admissions-2027-02.json").read_text(encoding="utf-8"))
            self.assertEqual(len(report["added"]), 1)
            self.assertEqual(len(report["modified"]), 1)
            self.assertEqual(len(report["statusChanges"]), 1)

    def test_same_input_produces_identical_review_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            first = self.make_example(parent, "first")
            second = self.make_example(parent, "second")
            for project_dir in (first, second):
                self.assertEqual(self.run_cli("review", str(project_dir), "--batch", "admissions-2027-01").returncode, 0)
            for suffix in ("json", "md", "html"):
                first_bytes = (first / "reviews" / f"admissions-2027-01-review.{suffix}").read_bytes()
                second_bytes = (second / "reviews" / f"admissions-2027-01-review.{suffix}").read_bytes()
                self.assertEqual(first_bytes, second_bytes)

    def test_invalid_json_returns_exit_code_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "broken"
            (project_dir / "staging").mkdir(parents=True)
            (project_dir / "project.json").write_text("{", encoding="utf-8")
            (project_dir / "staging" / "batch.json").write_text("{}", encoding="utf-8")
            result = self.run_cli("validate", str(project_dir), "--batch", "batch")
            self.assertEqual(result.returncode, 2)

    def test_init_refuses_nonempty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nonempty"
            target.mkdir()
            (target / "keep.txt").write_text("keep", encoding="utf-8")
            result = self.run_cli("init", str(target), "--example", "admissions")
            self.assertEqual(result.returncode, 2)
            self.assertTrue((target / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
