from __future__ import annotations

from pathlib import Path

from scripts import audit_deterministic_semantic_ownership as audit


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_audit_report_mode_remains_non_blocking_for_known_legacy_inventory() -> None:
    report = audit.build_report(stage="report")

    assert report["report_only"] is True
    assert report["fails_build"] is False
    assert report["gate_stage"] == "report"
    assert report["semantic_owner_policy"]["legacy_scan_matches_are_supporting_evidence_only"] is True


def test_audit_zero_high_risk_stage_passes_when_active_runtime_is_clean() -> None:
    report = audit.build_report(stage="zero-high-risk")

    assert report["report_only"] is False
    assert report["fails_build"] is False
    assert report["gate_stage"] == "zero-high-risk"
    assert report["high_risk_finding_count"] == 0


def test_audit_detects_synthetic_forbidden_keyword_semantic_router(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    _write(
        tmp_path / "app/intake/application/router.py",
        """
def route(text):
    keywords = ("ate", "logged")
    if any(token in text for token in keywords):
        return "intake"
    return "chat"
""",
    )

    report = audit.build_report(stage="active-runtime-zero")

    assert report["fails_build"] is True
    assert report["active_runtime_unauthorized_high_risk_finding_count"] >= 1
    assert report["unauthorized_high_risk_finding_count"] >= 1
    assert any(
        finding["risk_id"] == "deterministic_keyword_intent_or_workflow_router"
        and finding["marker"] == "keywords"
        for finding in report["unauthorized_findings"]
    )


def test_audit_detects_synthetic_post_manager_semantic_field_rewrite(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    _write(
        tmp_path / "app/runtime/application/post_manager.py",
        """
def rewrite(payload):
    payload.follow_up_needed = False
    payload.action_taken = "logged"
    return payload
""",
    )

    report = audit.build_report(stage="active-runtime-zero")

    assert report["fails_build"] is True
    markers = {finding["marker"] for finding in report["unauthorized_findings"]}
    assert {"payload.follow_up_needed =", "payload.action_taken ="} <= markers


def test_audit_detects_synthetic_legacy_resolution_pipeline(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    legacy_token = "nutrition" + "_resolution"
    _write(
        tmp_path / "app/nutrition/agent" / f"{legacy_token}_normalizer.py",
        """
def normalize(raw):
    return raw
""",
    )

    report = audit.build_report(stage="active-runtime-zero")

    assert report["fails_build"] is True
    assert any(
        finding["risk_id"] == "legacy_resolution_semantic_pipeline"
        for finding in report["unauthorized_findings"]
    )


def test_audit_detects_synthetic_legacy_resolution_action(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    legacy_action = "run_" + "nutrition" + "_resolution"
    _write(
        tmp_path / "app/shared/contracts/common.py",
        f"""
DecisionNextAction = Literal["run_tool_lookup", "{legacy_action}"]
""",
    )

    report = audit.build_report(stage="active-runtime-zero")

    assert report["fails_build"] is True
    assert any(
        finding["marker"] == legacy_action
        for finding in report["unauthorized_findings"]
    )


def test_audit_zero_high_risk_stage_blocks_synthetic_post_manager_rewrite(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    _write(
        tmp_path / "app/nutrition/application/followup_policy.py",
        """
def rewrite(updated):
    updated["follow_up_needed"] = True
    updated["action_taken"] = "clarify_before_estimate"
    return updated
""",
    )

    report = audit.build_report(stage="zero-high-risk")

    assert report["fails_build"] is True
    assert report["unauthorized_high_risk_finding_count"] >= 2


def test_audit_allowlisted_validator_and_trace_surfaces_are_not_unauthorized(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    _write(
        tmp_path / "app/intake/application/transition_guard.py",
        """
def validate_guard():
    blocked_mutation = True
    payload.follow_up_needed = payload.follow_up_needed
    return blocked_mutation
""",
    )
    _write(
        tmp_path / "app/runtime/application/request_trace_artifacts.py",
        """
def emit_trace(trace_contract, unresolved):
    trace_contract["followup_question"] = None
    trace_contract["unresolved_info"] = unresolved
""",
    )

    report = audit.build_report(stage="active-runtime-zero")

    assert report["fails_build"] is False
    assert report["high_risk_finding_count"] >= 3
    assert report["allowed_high_risk_finding_count"] == report["high_risk_finding_count"]
    assert report["unauthorized_high_risk_finding_count"] == 0
    allowed_reasons = {finding["allowlist_reason"] for finding in report["allowed_findings"]}
    assert allowed_reasons == {
        "Transition guard legality validation may expose semantic fields without owning their meaning.",
        "Trace artifact projection records manager output for auditability without rewriting product truth.",
    }


def test_audit_stage_names_remain_backwards_compatible() -> None:
    assert {"report", "new-high-risk", "active-runtime", "zero-high-risk", "active-runtime-zero"} <= set(
        audit.GATE_STAGES
    )
