from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def test_bootstrap_requires_best_practice_and_semantic_owner_fields() -> None:
    agents = _read("AGENTS.md")
    bootstrap = _read("docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md")
    combined = f"{agents}\n{bootstrap}"

    required_markers = [
        "best_practice_evidence",
        "llm_deterministic_boundary",
        "semantic_owner",
        "deterministic diagnostic mode means offline, reproducible, and no live provider call",
        "does not grant deterministic semantic ownership",
        "fake providers in deterministic diagnostics may simulate LLM / manager structured outputs",
    ]
    for marker in required_markers:
        assert marker in combined

    semantic_fields = [
        "intent",
        "workflow_effect",
        "action_taken",
        "response_mode_hint",
        "follow_up_needed",
        "followup_question",
        "route_target",
        "exactness",
        "resolution_mode",
    ]
    for field in semantic_fields:
        assert f"`{field}`" in combined


def test_best_practice_steering_uses_available_search_and_requires_evidence() -> None:
    steering = _read(".kiro/steering/best-practice-search.md")

    assert "Use the available web/search tool in the current environment" in steering
    assert "Prefer official or primary sources first" in steering
    assert "Record the search in the implementation plan under `best_practice_evidence`" in steering
    assert "missing `best_practice_evidence` is a planning failure" in steering


def test_bootstrap_records_founder_live_strictness_model_inversion_policy() -> None:
    bootstrap = _read("docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md")
    local_memory = _read("docs/agent/EVOMAP_LOCAL_MEMORY.md")

    assert "first-pass strictness must target invariant compliance" in bootstrap
    assert "not provider-specific trace imitation" in bootstrap
    assert "single-profile diagnostic stability" in bootstrap
    assert "model diversity evidence" in bootstrap
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
