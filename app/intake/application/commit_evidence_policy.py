from __future__ import annotations

from typing import Any


COMMIT_EVIDENCE_FAILURE_FAMILY = "nutrition_evidence_not_commit_eligible"


def commit_evidence_blockers(trace_contract: dict[str, Any] | None) -> list[str]:
    trace = trace_contract or {}
    blockers: list[str] = []
    if trace.get("shadow_stub") is True:
        blockers.append("shadow_stub_estimate")
    approved_fooddb = trace.get("approved_fooddb_evidence_trace")
    if isinstance(approved_fooddb, dict) and approved_fooddb.get("runtime_truth_allowed") is False:
        blockers.append("approved_fooddb_runtime_truth_denied")
    approved_macro = trace.get("approved_exact_macro_trace")
    if isinstance(approved_macro, dict) and approved_macro.get("runtime_truth_allowed") is False:
        blockers.append("approved_exact_runtime_truth_denied")
    return blockers


def apply_commit_evidence_policy_to_trace(trace_contract: dict[str, Any] | None) -> dict[str, Any]:
    trace = trace_contract if isinstance(trace_contract, dict) else {}
    blockers = commit_evidence_blockers(trace)
    if not blockers:
        return trace
    existing_decision = trace.get("canonical_write_decision")
    decision = existing_decision if isinstance(existing_decision, dict) else {}
    decision.update(
        {
            "can_write_canonical": False,
            "source": "commit_evidence_policy",
            "failure_family": COMMIT_EVIDENCE_FAILURE_FAMILY,
            "blockers": blockers,
        }
    )
    trace["canonical_write_decision"] = decision
    trace["macro_display_authorized"] = False
    trace.setdefault("macro_visibility_status", "hidden_missing_source")
    trace.setdefault("macro_guard_reason", "no_macro_data")
    return trace


def apply_commit_evidence_policy_to_payload(payload: Any | None) -> dict[str, Any]:
    if payload is None:
        return {}
    trace = apply_commit_evidence_policy_to_trace(dict(getattr(payload, "trace_contract", None) or {}))
    payload.trace_contract = trace
    return trace


def commit_evidence_failure_family(trace_contract: dict[str, Any] | None) -> str | None:
    decision = dict((trace_contract or {}).get("canonical_write_decision") or {})
    failure = str(decision.get("failure_family") or "").strip()
    return failure or None


__all__ = [
    "COMMIT_EVIDENCE_FAILURE_FAMILY",
    "apply_commit_evidence_policy_to_payload",
    "apply_commit_evidence_policy_to_trace",
    "commit_evidence_blockers",
    "commit_evidence_failure_family",
]
