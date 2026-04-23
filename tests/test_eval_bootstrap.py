from __future__ import annotations

from pathlib import Path

from scripts.eval_bootstrap import CANONICAL_PRE_EDD_STATUS_KEYS, build_bootstrap_checklist, build_bundle_verdict
from scripts.eval_parity_audit import run_parity_audit


ROOT = Path(__file__).resolve().parents[1]


def test_bundle1_parity_audit_reports_complete_coverage() -> None:
    report = run_parity_audit(1)

    assert report["bundle"] == 1
    assert report["parity_audit_completed"] is True
    assert report["coverage_status"] == "complete"
    assert report["coverage_blocking_gaps"] == 0
    assert any(clause["clause_id"] == "B-001.chat_remaining_matches_ui" for clause in report["spec_clauses"])


def test_bundle2_parity_audit_reports_macro_contract_clauses() -> None:
    report = run_parity_audit(2)

    clause_ids = {clause["clause_id"] for clause in report["spec_clauses"]}

    assert report["bundle"] == 2
    assert report["coverage_status"] == "complete"
    assert report["coverage_blocking_gaps"] == 0
    assert "macro.rule1_draft_hidden" in clause_ids
    assert "macro.rule5_chat_visibility" in clause_ids
    assert "same_turn.sync_family" in clause_ids
    assert "K-001.preserve_non_target_items" in clause_ids
    assert "K-002.removal_preserves_thread" in clause_ids


def test_bundle_verdict_requires_runner_coverage_and_founder_status() -> None:
    assert build_bundle_verdict(
        runner_case_status="pass",
        coverage_status="complete",
        founder_realism_status="pass",
    )["bundle_ready_for_human_e2e"] is True

    assert build_bundle_verdict(
        runner_case_status="pass",
        coverage_status="incomplete",
        founder_realism_status="pass",
    )["bundle_ready_for_human_e2e"] is False

    assert build_bundle_verdict(
        runner_case_status="pass",
        coverage_status="complete",
        founder_realism_status="not_run",
    )["bundle_ready_for_human_e2e"] is False


def test_bootstrap_checklist_reads_canonical_pre_edd_statuses(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.eval_bootstrap.run_parity_audit",
        lambda bundle: {"bundle": bundle, "coverage_status": "complete", "coverage_blocking_gaps": 0},
    )
    monkeypatch.setattr("scripts.eval_bootstrap.ensure_evomap_online", lambda: {"status": "offline"})
    monkeypatch.setattr("scripts.eval_bootstrap._trace_roundtrip_status", lambda: (True, "runtime/logs/requests"))

    pre_edd_report = {
        "summary": {"status": "ready_for_edd"},
        "statuses": {
            "encoding_status": {"status": "pass", "details": []},
            **{key: {"status": "pass", "details": []} for key in CANONICAL_PRE_EDD_STATUS_KEYS},
        },
    }
    checklist = build_bootstrap_checklist(
        bundle=2,
        founder_realism_status={"status": "not_run", "report_path": None, "blocking_failed": None},
        pre_edd_report=pre_edd_report,
    )

    assert checklist["pre_edd_readiness_status"] == "ready_for_edd"
    assert checklist["architecture_purity"] == "pass"
    assert checklist["trace_roundtrip_verified"] is True
    for key in CANONICAL_PRE_EDD_STATUS_KEYS:
        assert checklist[key]["status"] == "pass"


def test_bundle_verdict_requires_canonical_pre_edd_statuses() -> None:
    checklist = {
        "architecture_purity": "pass",
        "encoding_evidence_status": "pass",
        "text_integrity_status": "healthy",
        "trace_roundtrip_verified": True,
        **{key: {"status": "pass"} for key in CANONICAL_PRE_EDD_STATUS_KEYS},
    }
    checklist["latency_trace_status"] = {"status": "fail"}

    verdict = build_bundle_verdict(
        runner_case_status="pass",
        coverage_status="complete",
        founder_realism_status="pass",
        checklist=checklist,
    )

    assert verdict["bundle_ready_for_human_e2e"] is False


def test_eval_bootstrap_no_longer_uses_parallel_architecture_purity_source() -> None:
    source = (ROOT / "scripts" / "eval_bootstrap.py").read_text(encoding="utf-8")

    assert "test_architecture.py" not in source
    assert "run_architecture_enforcement" not in source
