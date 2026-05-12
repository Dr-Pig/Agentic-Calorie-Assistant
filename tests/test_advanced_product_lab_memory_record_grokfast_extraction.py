from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]
ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
SCRIPT = "scripts/run_advanced_product_lab_memory_record_grokfast_extraction.py"


def test_grokfast_extraction_cases_use_approved_golden_set_without_oracle_payload() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_cases import (
        GOLDEN_EXTRACTION_CASE_IDS,
        build_memory_record_grokfast_extraction_cases,
        memory_record_grokfast_extraction_provider_payload,
    )

    cases = build_memory_record_grokfast_extraction_cases()
    payload = memory_record_grokfast_extraction_provider_payload(cases, constraints={})

    assert [case["case_id"] for case in cases] == list(GOLDEN_EXTRACTION_CASE_IDS)
    assert len(cases) >= 8
    assert all(case["source_refs"] for case in cases)
    assert "expected_candidate" in cases[0]
    assert "expected_candidate" not in json.dumps(payload, ensure_ascii=False)
    assert "raw_keyword_route_allowed" not in json.dumps(payload, ensure_ascii=False)


def test_grokfast_extraction_fake_provider_passes_contract_as_non_live() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction import (
        run_memory_record_grokfast_extraction_diagnostic,
    )
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_cases import (
        build_memory_record_grokfast_extraction_cases,
    )

    cases = build_memory_record_grokfast_extraction_cases()
    artifact = run_memory_record_grokfast_extraction_diagnostic(
        cases=cases,
        provider=_FakeExtractionProvider(cases),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_memory_record_grokfast_extraction_diagnostic"
    )
    assert artifact["status"] == "pass"
    assert artifact["case_count"] == len(cases)
    assert artifact["diagnostic_evidence_class"] == "fake_contract"
    assert artifact["live_grokfast_extraction_pass"] is False
    assert artifact["live_completion_claim_allowed"] is False
    assert artifact["semantic_hardening_allowed"] is False
    assert artifact["grader_summary"]["failed_case_count"] == 0
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["durable_product_memory_written"] is False


def test_grokfast_extraction_grader_blocks_mismatch_without_semantic_hardening() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction import (
        run_memory_record_grokfast_extraction_diagnostic,
    )
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_cases import (
        build_memory_record_grokfast_extraction_cases,
    )

    cases = build_memory_record_grokfast_extraction_cases()
    artifact = run_memory_record_grokfast_extraction_diagnostic(
        cases=cases,
        provider=_FakeExtractionProvider(cases, corrupt_first=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "blocked"
    assert artifact["semantic_hardening_allowed"] is False
    assert artifact["grader_summary"]["failed_case_count"] == 1
    assert "case:explicit_preference_confirm_candidate.candidate_type_mismatch" in (
        artifact["blockers"]
    )


def test_grokfast_extraction_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "blocked-live-extraction.json"

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={key: value for key, value in os.environ.items() if key != ALLOW_ENV},
    )

    assert result.returncode == 0, result.stderr
    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["diagnostic_evidence_class"] == "blocked_not_invoked"
    assert artifact["live_grokfast_extraction_pass"] is False


def test_grokfast_extraction_cli_fake_mode_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "fake-extraction.json"

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--output",
            str(output),
            "--provider-mode",
            "fake",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout = json.loads(result.stdout)
    artifact = read_json_artifact(output)
    assert stdout["status"] == "pass"
    assert artifact["status"] == "pass"
    assert artifact["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


class _FakeExtractionProvider:
    def __init__(self, cases: list[dict[str, Any]], *, corrupt_first: bool = False) -> None:
        self.cases = cases
        self.corrupt_first = corrupt_first

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-memory-extraction", "configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        requested = {
            str(item.get("case_id") or "")
            for item in dict(kwargs["user_payload"])["cases"]  # type: ignore[index]
        }
        results = []
        for index, case in enumerate(self.cases):
            if case["case_id"] not in requested:
                continue
            expected = dict(case["expected_candidate"])
            candidate_type = str(expected.get("candidate_type") or "none")
            if index == 0 and self.corrupt_first:
                candidate_type = "none"
            results.append(
                {
                    "case_id": case["case_id"],
                    "candidate_type": candidate_type,
                    "polarity": expected.get("polarity", "neutral"),
                    "strength": expected.get("strength", "none"),
                    "promotion_allowed_now": expected.get("promotion_allowed_now", False),
                    "human_review_required": expected.get("human_review_required", False),
                    "rejection_reason": expected.get("rejection_reason", ""),
                    "source_refs": list(case["source_refs"]),
                    "reasoning_notes": "fake provider contract output",
                }
            )
        return {
            "case_results": results,
            "diagnostic_notes": "fake extraction diagnostic",
            "risk_notes": "no semantic hardening",
            "claim_scope": "diagnostic_only",
        }, {"stage": "memory_record_grokfast_extraction", "provider": "fake"}
