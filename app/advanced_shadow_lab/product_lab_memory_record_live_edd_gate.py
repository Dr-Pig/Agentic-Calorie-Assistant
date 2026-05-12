from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_memory_record_live_artifact import (
    ARTIFACT_TYPE as LIVE_DIAGNOSTIC_ARTIFACT_TYPE,
)
from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (
    NON_CLAIMS,
    PREFLIGHT_ARTIFACT_TYPE,
)


GATE_ARTIFACT_TYPE = "advanced_product_lab_memory_record_live_edd_gate"


def review_memory_record_live_edd_gate(
    *,
    preflight_artifact: Mapping[str, Any],
    live_diagnostic_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_class = str(
        live_diagnostic_artifact.get("diagnostic_evidence_class") or "noncanonical"
    )
    blockers = [
        *_preflight_blockers(preflight_artifact),
        *_diagnostic_blockers(evidence_class, live_diagnostic_artifact),
        *_claim_drift_blockers("preflight", preflight_artifact),
        *_claim_drift_blockers("live_diagnostic", live_diagnostic_artifact),
    ]
    live_reviewed = evidence_class == "live_grokfast"
    live_complete = live_reviewed and not blockers
    return {
        "artifact_type": GATE_ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "pass" if live_complete else "blocked",
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_live_edd_gate.py",
        "consumer": "advanced_product_lab_memory_live_edd_decision_pack",
        "reviewed_live_status": _reviewed_live_status(
            evidence_class=evidence_class,
            live_complete=live_complete,
        ),
        "preflight_reviewed_status": str(
            preflight_artifact.get("reviewed_preflight_status") or ""
        ),
        "diagnostic_evidence_class": evidence_class,
        "fake_contract_reviewed": evidence_class == "fake_contract",
        "blocked_not_invoked_reviewed": evidence_class == "blocked_not_invoked",
        "live_grokfast_reviewed": live_reviewed,
        "live_milestone_complete": live_complete,
        "live_completion_claim_allowed": (
            live_diagnostic_artifact.get("live_completion_claim_allowed") is True
        ),
        "blockers": blockers,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _preflight_blockers(preflight_artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if preflight_artifact.get("artifact_type") != PREFLIGHT_ARTIFACT_TYPE:
        blockers.append("preflight.artifact_type_mismatch")
    status = str(preflight_artifact.get("status") or "missing")
    if status != "pass":
        blockers.append(f"preflight.status_{status}")
    if _preflight_live_ready_required(preflight_artifact):
        blockers.append("preflight.live_milestone_preflight_not_ready")
    return blockers


def _preflight_live_ready_required(preflight_artifact: Mapping[str, Any]) -> bool:
    if preflight_artifact.get("provider_mode") != "live":
        return False
    if preflight_artifact.get("status") != "pass":
        return False
    return preflight_artifact.get("live_milestone_preflight_ready") is not True


def _diagnostic_blockers(
    evidence_class: str,
    live_diagnostic_artifact: Mapping[str, Any],
) -> list[str]:
    if live_diagnostic_artifact.get("artifact_type") != LIVE_DIAGNOSTIC_ARTIFACT_TYPE:
        return ["live_diagnostic.artifact_type_mismatch"]
    if evidence_class == "live_grokfast":
        if live_diagnostic_artifact.get("live_completion_claim_allowed") is True:
            return []
        return ["live_diagnostic.live_completion_claim_not_allowed"]
    if evidence_class == "fake_contract":
        return ["live_diagnostic.fake_contract_not_live_milestone"]
    if evidence_class == "blocked_not_invoked":
        return ["live_diagnostic.blocked_not_invoked"]
    return [f"live_diagnostic.noncanonical_evidence:{evidence_class or 'missing'}"]


def _reviewed_live_status(*, evidence_class: str, live_complete: bool) -> str:
    if live_complete:
        return "live_grokfast_reviewed_pass"
    if evidence_class == "fake_contract":
        return "fake_contract_reviewed_non_live"
    if evidence_class == "blocked_not_invoked":
        return "blocked_not_invoked_reviewed"
    if evidence_class == "live_grokfast":
        return "live_grokfast_reviewed_blocked"
    return "noncanonical_reviewed"


def _claim_drift_blockers(stage: str, artifact: Mapping[str, Any]) -> list[str]:
    return [
        f"{stage}.{flag}.claim_drift"
        for flag in (
            "mainline_activation_enabled",
            "mainline_runtime_connected",
            "durable_product_memory_written",
            "canonical_product_mutation_allowed",
            "production_scheduler_delivery_allowed",
            "kimi_live_calls_allowed",
        )
        if artifact.get(flag) is True
    ]
