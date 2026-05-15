from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def test_bootstrap_requires_best_practice_and_semantic_owner_fields() -> None:
    agents = _read("AGENTS.md")
    operating_entry = _read("docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md")
    golden_set = _read("docs/quality/CURRENT_SHELL_SELF_USE_GOLDEN_SET_SPEC.md")
    combined = f"{agents}\n{operating_entry}\n{golden_set}"

    required_markers = [
        "best_practice_evidence",
        "llm_deterministic_boundary",
        "semantic_owner",
        "Product truth is higher-order than eval shape",
        "Deterministic code may validate, reject, downgrade, derive, or request bounded repair",
        "Fake providers in deterministic diagnostics may simulate LLM/manager structured outputs",
    ]
    for marker in required_markers:
        assert marker in combined

    semantic_owner_markers = [
        "semantic intent",
        "tool choice",
        "correction/removal target",
        "attach target",
        "final action",
        "composition sufficiency",
        "estimability",
        "follow-up necessity",
    ]
    for marker in semantic_owner_markers:
        assert marker in combined


def test_best_practice_guidance_is_repo_local_not_kiro_steering() -> None:
    agents = _read("AGENTS.md")
    operating_entry = _read("docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md")
    combined = f"{agents}\n{operating_entry}"

    assert not (ROOT / ".kiro").exists()
    assert "current official or primary sources" in combined
    assert "best_practice_evidence" in combined
    assert ".kiro/steering/best-practice-search.md" not in combined


def test_bootstrap_records_founder_live_strictness_model_inversion_policy() -> None:
    runbook = _read("docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md")
    local_memory = _read("docs/agent/EVOMAP_LOCAL_MEMORY.md")

    assert "live full-suite failure unlocks attribution/audit only" in runbook
    assert "live failure alone cannot justify prompt/schema/contract hardening" in runbook
    assert "provider/model diversity evidence" in runbook
    assert "legal-flow matrix" in runbook
    assert "holdout tests" in runbook
    assert "local-2026-05-01-founder-live-strictness-model-inversion" in local_memory


def test_deterministic_semantic_ownership_audit_is_report_only() -> None:
    module = importlib.import_module("scripts.audit_deterministic_semantic_ownership")
    report = module.build_report()

    assert report["artifact_type"] == "deterministic_semantic_ownership_audit"
    assert report["report_only"] is True
    assert report["fails_build"] is False
    policy = report["semantic_owner_policy"]
    assert policy["deterministic_diagnostic_mode_is_not_semantic_ownership"] is True
    assert policy["llm_or_manager_structured_output_owns_ambiguous_intent_and_food_semantics"] is True
    assert policy["legacy_scan_matches_are_supporting_evidence_only"] is True

    findings = report["findings"]
    assert findings
    assert report["high_risk_finding_count"] >= report["unauthorized_high_risk_finding_count"]
    assert "allowed_findings" in report
    assert "unauthorized_findings" in report
    assert "active-runtime-zero" in report["gate_policy"]
