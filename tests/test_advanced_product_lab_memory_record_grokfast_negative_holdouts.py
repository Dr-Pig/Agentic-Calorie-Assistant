from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/run_advanced_product_lab_memory_record_grokfast_extraction.py"


def test_negative_holdout_cases_cover_block_downrank_and_ignored_dessert_without_oracle_payload() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_cases import (
        NEGATIVE_HOLDOUT_CASE_IDS,
        build_memory_record_grokfast_negative_holdout_cases,
        memory_record_grokfast_extraction_provider_payload,
    )

    cases = build_memory_record_grokfast_negative_holdout_cases()
    by_id = {case["case_id"]: case for case in cases}
    payload = memory_record_grokfast_extraction_provider_payload(cases, constraints={})

    assert [case["case_id"] for case in cases] == list(NEGATIVE_HOLDOUT_CASE_IDS)
    assert by_id["negative_bitter_melon_block"]["expected_candidate"]["strength"] == "block"
    assert by_id["negative_spicy_block"]["expected_candidate"]["strength"] == "block"
    assert by_id["negative_bland_food_downrank"]["expected_candidate"]["strength"] == "downrank"
    assert (
        by_id["negative_dessert_ignored_after_user_says_do_not_remember"][
            "expected_candidate"
        ]["memory_candidate_allowed"]
        is False
    )
    assert "expected_candidate" not in json.dumps(payload, ensure_ascii=False)
    assert payload["output_contract"]["negative_preference_priority"] == [
        "block",
        "downrank",
        "boost",
    ]
    assert payload["output_contract"]["do_not_remember_user_instruction_wins"] is True


def test_negative_holdout_fake_provider_passes_and_records_priority_summary() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction import (
        run_memory_record_grokfast_extraction_diagnostic,
    )
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_cases import (
        build_memory_record_grokfast_negative_holdout_cases,
    )

    cases = build_memory_record_grokfast_negative_holdout_cases()
    artifact = run_memory_record_grokfast_extraction_diagnostic(
        cases=cases,
        provider=_FakeExtractionProvider(cases),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        case_suite="negative_holdout",
    )

    assert artifact["status"] == "pass"
    assert artifact["case_suite"] == "negative_holdout"
    assert artifact["negative_holdout_summary"] == {
        "case_count": 6,
        "block_case_count": 2,
        "downrank_case_count": 3,
        "ignored_case_count": 1,
    }
    assert artifact["grader_summary"]["failed_case_count"] == 0
    assert artifact["live_grokfast_extraction_pass"] is False
    assert artifact["mainline_activation_enabled"] is False


def test_negative_holdout_grader_blocks_dessert_candidate_when_user_says_do_not_remember() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction import (
        run_memory_record_grokfast_extraction_diagnostic,
    )
    from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_cases import (
        build_memory_record_grokfast_negative_holdout_cases,
    )

    cases = build_memory_record_grokfast_negative_holdout_cases()
    artifact = run_memory_record_grokfast_extraction_diagnostic(
        cases=cases,
        provider=_FakeExtractionProvider(cases, corrupt_ignored=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        case_suite="negative_holdout",
    )

    assert artifact["status"] == "blocked"
    assert (
        "case:negative_dessert_ignored_after_user_says_do_not_remember."
        "memory_candidate_allowed_mismatch"
    ) in artifact["blockers"]
    assert (
        "case:negative_dessert_ignored_after_user_says_do_not_remember."
        "rejection_reason_missing"
    ) in artifact["blockers"]
    assert artifact["semantic_hardening_allowed"] is False


def test_negative_holdout_cli_fake_mode_writes_six_case_artifact(tmp_path: Path) -> None:
    output = tmp_path / "fake-negative-holdout-extraction.json"

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--output",
            str(output),
            "--provider-mode",
            "fake",
            "--case-suite",
            "negative-holdout",
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
    assert artifact["case_suite"] == "negative_holdout"
    assert artifact["case_count"] == 6
    assert artifact["negative_holdout_summary"]["ignored_case_count"] == 1
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


class _FakeExtractionProvider:
    def __init__(self, cases: list[dict[str, Any]], *, corrupt_ignored: bool = False) -> None:
        self.cases = cases
        self.corrupt_ignored = corrupt_ignored

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-memory-extraction", "configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        requested = {
            str(item.get("case_id") or "")
            for item in dict(kwargs["user_payload"])["cases"]  # type: ignore[index]
        }
        results = []
        for case in self.cases:
            if case["case_id"] not in requested:
                continue
            expected = dict(case["expected_candidate"])
            candidate_type = str(expected.get("candidate_type") or "none")
            rejection_reason = str(expected.get("rejection_reason") or "")
            if (
                self.corrupt_ignored
                and case["case_id"]
                == "negative_dessert_ignored_after_user_says_do_not_remember"
            ):
                candidate_type = "negative_preference"
                rejection_reason = ""
            results.append(
                {
                    "case_id": case["case_id"],
                    "candidate_type": candidate_type,
                    "polarity": expected.get("polarity", "neutral"),
                    "strength": expected.get("strength", "none"),
                    "promotion_allowed_now": expected.get("promotion_allowed_now", False),
                    "human_review_required": expected.get("human_review_required", False),
                    "rejection_reason": rejection_reason,
                    "source_refs": list(case["source_refs"]),
                    "reasoning_notes": "fake provider contract output",
                }
            )
        return {
            "case_results": results,
            "diagnostic_notes": "fake negative holdout extraction diagnostic",
            "risk_notes": "no semantic hardening",
            "claim_scope": "diagnostic_only",
        }, {"stage": "memory_record_grokfast_extraction", "provider": "fake"}
