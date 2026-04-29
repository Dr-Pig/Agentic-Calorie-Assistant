from __future__ import annotations

from pathlib import Path

from scripts.live_eval_readiness import (
    PHASE_C_LIVE_BLOCKING_CHECKS,
    PHASE_C_SAME_TRUTH_FAILURE,
    build_live_preflight_report,
    build_phase_c_live_readiness,
    summarize_phase_c_gate_status,
)


ROOT = Path(__file__).resolve().parents[1]


def _phase_c_trace(*, status: str = "pass") -> dict[str, object]:
    return {
        "phase_c_trace": {
            "mutation_outcome": {"canonical_commit_status": "committed"},
            "same_truth_read_result": {"owner_alignment": "aligned"},
            "same_truth_closure_gate": {
                "checked": True,
                "status": status,
                "failure_family": PHASE_C_SAME_TRUTH_FAILURE if status == "hard_fail" else None,
            },
        }
    }


def test_phase_c_live_readiness_accepts_structured_trace_evidence() -> None:
    readiness = build_phase_c_live_readiness(response={"hard_fail_conditions": []}, trace=_phase_c_trace())

    assert all(readiness["checks"][name] for name in PHASE_C_LIVE_BLOCKING_CHECKS)
    assert readiness["summary"]["status"] == "pass"
    assert readiness["summary"]["readiness_pass"] is True


def test_phase_c_live_readiness_hard_fail_blocks_readiness_but_remains_diagnostic_evidence() -> None:
    readiness = build_phase_c_live_readiness(
        response={"hard_fail_conditions": [PHASE_C_SAME_TRUTH_FAILURE]},
        trace=_phase_c_trace(status="hard_fail"),
    )

    assert readiness["checks"]["phase_c_trace_present"] is True
    assert readiness["checks"]["phase_c_same_truth_gate_checked"] is True
    assert readiness["checks"]["phase_c_same_truth_gate_not_hard_fail"] is False
    assert readiness["checks"]["phase_c_no_same_truth_hard_fail_condition"] is False
    assert readiness["summary"]["status"] == "hard_fail"
    assert readiness["summary"]["readiness_pass"] is False


def test_live_preflight_distinguishes_diagnostic_default_from_explicit_readiness_base_url() -> None:
    ping = {
        "provider": {"ready": True},
        "manager_provider": {"ready": True},
        "search": {"ready": False},
        "extract": {"ready": False},
    }

    diagnostic = build_live_preflight_report(
        base_url="http://127.0.0.1:8010",
        base_url_explicit=False,
        ping_payload=ping,
    )
    readiness = build_live_preflight_report(
        base_url="http://127.0.0.1:8011",
        base_url_explicit=True,
        ping_payload=ping,
    )

    assert diagnostic["live_test_mode"] == "diagnostic"
    assert diagnostic["readiness_claim_scope"] == "diagnostic_live_smoke"
    assert readiness["live_test_mode"] == "readiness"
    assert readiness["readiness_claim_scope"] == "live_readiness_candidate"
    assert readiness["server_ping_status"] == "pass"
    assert readiness["provider_readiness"]["manager_provider"] == {"ready": True}


def test_phase_c_gate_status_summary_marks_flagged_and_hard_fail() -> None:
    assert summarize_phase_c_gate_status(
        [
            {"extra": {"phase_c_live_readiness": {"status": "pass", "readiness_pass": True}}},
            {"extra": {"phase_c_live_readiness": {"status": "flagged", "readiness_pass": True}}},
        ]
    ) == "flagged"

    assert summarize_phase_c_gate_status(
        [{"extra": {"phase_c_live_readiness": {"status": "hard_fail", "readiness_pass": False}}}]
    ) == "hard_fail"

    assert summarize_phase_c_gate_status([{"extra": {}}]) == "not_applicable"


def test_bundle2_live_runner_can_attach_phase_c_readiness_to_case_checks() -> None:
    from scripts import run_v2_bundle2_live_eval as runner

    checks, extra = runner._phase_c_checked_case(
        checks={"existing_case_check": True},
        response={"hard_fail_conditions": []},
        trace=_phase_c_trace(),
    )

    assert checks["existing_case_check"] is True
    assert all(checks[name] for name in runner.PHASE_C_LIVE_BLOCKING_CHECKS)
    assert extra["phase_c_live_readiness"]["readiness_pass"] is True


def test_live_runner_case_selection_supports_single_case_and_shard_modes() -> None:
    from scripts import run_v2_bundle2_live_eval as runner

    single = runner._selection_metadata(["C-001"])
    shard = runner._selection_metadata(["C-001", "D-001"])

    assert single["run_mode"] == "single_case"
    assert single["selected_case_ids"] == ["C-001"]
    assert single["expected_total_cases"] == 1
    assert single["full_acceptance_package_run"] is False
    assert [case_id for case_id, _ in runner._select_case_runners(["C-001"])] == ["C-001"]
    assert shard["run_mode"] == "shard"
    assert shard["selected_case_ids"] == ["C-001", "D-001"]
    assert shard["expected_total_cases"] == 2
    assert shard["full_acceptance_package_run"] is False


def test_live_runner_no_case_selector_keeps_full_mode() -> None:
    from scripts import run_v2_bundle1_live_eval as runner

    metadata = runner._selection_metadata(None)

    assert metadata["run_mode"] == "full"
    assert metadata["expected_total_cases"] == len(runner.CASE_RUNNER_MAP)
    assert metadata["completed_cases"] == 0
    assert metadata["full_acceptance_package_run"] is True


def test_selected_live_run_cannot_report_readiness_status() -> None:
    from scripts import run_v2_bundle2_live_eval as runner

    assert runner._runner_case_status(all_cases_pass=True, run_mode="single_case") == "diagnostic"
    assert runner._runner_case_status(all_cases_pass=True, run_mode="shard") == "diagnostic"
    assert runner._runner_case_status(all_cases_pass=True, run_mode="full") == "pass"
    assert (
        runner._readiness_claim_scope_for_run(
            live_preflight_scope="live_readiness_candidate",
            run_mode="single_case",
        )
        == "diagnostic_case_run"
    )
    assert (
        runner._readiness_claim_scope_for_run(
            live_preflight_scope="live_readiness_candidate",
            run_mode="full",
        )
        == "live_readiness_candidate"
    )


def test_live_runner_error_result_preserves_canonical_case_id() -> None:
    from scripts import run_v2_bundle1_live_eval as runner

    result = runner._case_error_result("B-004", RuntimeError("boom"))

    assert result["case_id"] == "B-004"
    assert result["passed"] is False
    assert result["checks"] == {"runner_ok": False}


def test_live_eval_readiness_docs_lock_ladder_and_phase_c_gate() -> None:
    spec = (ROOT / "docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md").read_text(encoding="utf-8-sig")
    bootstrap = (ROOT / "docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md").read_text(encoding="utf-8-sig")

    assert "Live Eval Readiness Harness Lock" in spec
    assert "Bundle 2 mutating live cases must check structured Phase C evidence" in spec
    assert "`same_truth_closure_gate.status` is not `hard_fail`" in spec
    assert "default localhost script settings are diagnostic unless `--base-url` is explicitly provided" in spec
    assert "Live eval readiness ladder" in bootstrap
    assert "hard-fail Phase C evidence may be recorded for diagnosis, but it blocks bundle readiness" in bootstrap
