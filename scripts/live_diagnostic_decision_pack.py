from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "live_diagnostic_product_semantic_decision_pack.json"

VERDICT_DIAGNOSTIC_OBSERVATION = "diagnostic_observation"
VERDICT_READINESS_BLOCKER = "readiness_blocker"
VERDICT_PRODUCT_DECISION_REQUIRED = "product_decision_required"

B2_DIAGNOSTIC_LANE = "b2_packet_synthesis"
B2_DIAGNOSTIC_FAILURE = "b2_live_llm_diagnostic_contract_violation"

_PRODUCT_DECISION_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "decision_id": "pearl_milk_tea_missing_sugar_size",
        "case": "Pearl milk tea with missing sugar level and size.",
        "current_spec_posture": "estimate_with_followup may stay draft unless commit boundary says estimable.",
        "decision_needed": "Should this be draft + follow-up or logged estimate + follow-up?",
        "options": ["draft_with_followup", "logged_estimate_with_followup"],
        "recommended_option": "draft_with_followup_until_founder_approved",
        "affected_runtime_surfaces": ["ClarificationDecision", "CommitBoundaryDecision", "Phase C same-truth"],
        "affected_tests": ["MS2", "MS7", "founder_human_gate"],
        "affected_copy": ["intake follow-up wording", "logged/draft honesty wording"],
    },
    {
        "decision_id": "homemade_dish_minimum_estimability",
        "case": "Homemade dish with unknown composition.",
        "current_spec_posture": "composition-unknown food remains draft or clarify-first.",
        "decision_needed": "What minimum ingredient/portion detail makes homemade food estimable?",
        "options": ["clarify_until_composition_known", "allow_rough_range_with_low_confidence"],
        "recommended_option": "clarify_until_composition_known",
        "affected_runtime_surfaces": ["B2 estimability", "ClarificationDecision", "CommitBoundaryDecision"],
        "affected_tests": ["MS2 homemade", "B2 synthesis"],
        "affected_copy": ["clarify question wording"],
    },
    {
        "decision_id": "followup_precision_or_commit_gate",
        "case": "Estimable item that still benefits from follow-up.",
        "current_spec_posture": "Follow-up is a precision-upgrade tool, not a hidden commit gate.",
        "decision_needed": "Confirm whether follow-up can coexist with logged estimates.",
        "options": ["precision_upgrade_only", "commit_gate_when_high_severity"],
        "recommended_option": "precision_upgrade_only",
        "affected_runtime_surfaces": ["followup_policy", "CommitBoundaryDecision"],
        "affected_tests": ["B2 follow-up severity", "Phase A boundary projection"],
        "affected_copy": ["follow-up explanation"],
    },
    {
        "decision_id": "ambiguous_correction_attach_threshold",
        "case": "User says a back-reference such as 'change that drink to half sugar'.",
        "current_spec_posture": "Strong single candidate may attach; ambiguity remains conservative.",
        "decision_needed": "When is a strong candidate enough without a yes/no confirmation?",
        "options": ["single_strong_candidate_attaches", "always_confirm_before_correction"],
        "recommended_option": "single_strong_candidate_attaches_with_guarded_no_mutation_fallback",
        "affected_runtime_surfaces": ["AttachmentDecision", "TransitionGuardResult", "history expansion"],
        "affected_tests": ["Phase A history expansion", "correction path"],
        "affected_copy": ["tentative-understanding cue"],
    },
    {
        "decision_id": "shadow_hypothesis_visibility",
        "case": "Tentative interpretation is useful but not authoritative.",
        "current_spec_posture": "ShadowHypothesis may guide dialogue but cannot authorize canonical write.",
        "decision_needed": "When should tentative understanding be chat-visible?",
        "options": ["internal_only", "medium_uncertainty_visible", "always_visible_before_action"],
        "recommended_option": "medium_uncertainty_visible",
        "affected_runtime_surfaces": ["ShadowHypothesis", "manager payload", "output honesty"],
        "affected_tests": ["Phase A shadow lifecycle", "dialogue cue tests"],
        "affected_copy": ["tentative phrasing"],
    },
    {
        "decision_id": "no_plan_budget_query_response",
        "case": "User asks remaining budget without an active body plan.",
        "current_spec_posture": "Degraded/onboarding guidance allowed; concrete remaining kcal not allowed.",
        "decision_needed": "What exact degraded response should be shown?",
        "options": ["onboarding_guidance_only", "explain_missing_plan_plus_logged_intake_summary"],
        "recommended_option": "explain_missing_plan_plus_logged_intake_summary",
        "affected_runtime_surfaces": ["FallbackHonestyDecision", "RemainingBudgetAnswerContract"],
        "affected_tests": ["MS14", "general-chat budget"],
        "affected_copy": ["budget degraded wording"],
    },
    {
        "decision_id": "phase_c_contradiction_strategy",
        "case": "Phase C structured surfaces contradict each other.",
        "current_spec_posture": "Contradictions are trace-visible hard-fail evidence only.",
        "decision_needed": "Should runtime later block output, safe no_commit, or show degraded state?",
        "options": ["diagnostic_only", "safe_no_commit", "output_block", "degraded_state"],
        "recommended_option": "safe_no_commit_after_owner_resolution",
        "affected_runtime_surfaces": ["phase_c_trace", "same_truth_closure_gate", "sidecar", "state_delta"],
        "affected_tests": ["Phase C same-truth", "live readiness"],
        "affected_copy": ["safe failure wording"],
    },
    {
        "decision_id": "llm_synthesis_trust_boundary",
        "case": "Live LLM produces B2 packet-based synthesis candidates.",
        "current_spec_posture": "LLM candidate output is diagnostic and non-mutating.",
        "decision_needed": "What error range and influence scope are acceptable before user-facing canary?",
        "options": ["diagnostic_only", "non_mutating_user_facing_estimate", "mutation_bearing_after_phase_c_enforcement"],
        "recommended_option": "diagnostic_only_until_shadow_comparison_green",
        "affected_runtime_surfaces": ["B2 Pass 2", "renderer input", "CommitBoundaryDecision"],
        "affected_tests": ["B2 provider bridge", "B2 readiness"],
        "affected_copy": ["estimate uncertainty wording"],
    },
    {
        "decision_id": "b2_live_web_tavily_scope",
        "case": "Live web/Tavily canary for nutrition evidence.",
        "current_spec_posture": "Provider/Tavily/B2 canaries are trace-first diagnostics.",
        "decision_needed": "Should first live web scope stay exact-brand only or widen?",
        "options": ["exact_brand_trace_only", "wider_web_retrieval_after_anchor_policy"],
        "recommended_option": "exact_brand_trace_only",
        "affected_runtime_surfaces": ["WebSearchPort", "selected extract policy", "evidence packets"],
        "affected_tests": ["B2 live exact-brand web canary", "selected extract"],
        "affected_copy": ["source honesty wording"],
    },
    {
        "decision_id": "founder_human_e2e_required_journeys",
        "case": "Human validation before E2E readiness claim.",
        "current_spec_posture": "Founder/human E2E requires bootstrap verdict inputs and trace roundtrip.",
        "decision_needed": "Which journeys are mandatory founder gates?",
        "options": ["core_intake_budget_correction_only", "core_plus_b2_live_diagnostic", "full_wave1_human_gate"],
        "recommended_option": "core_intake_budget_correction_only",
        "affected_runtime_surfaces": ["live eval reports", "bootstrap verdict"],
        "affected_tests": ["founder realism", "UX journey map"],
        "affected_copy": ["human review checklist"],
    },
)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def classify_live_diagnostic_verdict(
    *,
    phase_c_live_readiness: dict[str, Any] | None = None,
    provider_schema_valid: bool = True,
    product_decision_required: bool = False,
) -> dict[str, Any]:
    phase_c = _dict(phase_c_live_readiness)
    if phase_c.get("status") == "hard_fail" or phase_c.get("readiness_pass") is False:
        return _verdict(VERDICT_READINESS_BLOCKER, "phase_c_same_truth_gate_not_ready")
    if not provider_schema_valid:
        return _verdict(VERDICT_READINESS_BLOCKER, "provider_schema_invalid")
    if product_decision_required:
        return _verdict(VERDICT_PRODUCT_DECISION_REQUIRED, "pending_product_semantic_decision")
    return _verdict(VERDICT_DIAGNOSTIC_OBSERVATION, "diagnostic_evidence_collected")


def build_b2_live_llm_diagnostic_evidence(manager_pass_2: dict[str, Any] | None) -> dict[str, Any]:
    payload = _dict(manager_pass_2)
    forbidden_fields = [str(item) for item in _list(payload.get("forbidden_mutation_fields_present"))]
    payload_shape_valid = payload.get("payload_shape_valid") is not False
    mutation_attempted = bool(payload.get("mutation_attempted"))
    contract_valid = payload_shape_valid and not forbidden_fields and not mutation_attempted
    item_results = [dict(item) for item in _list(payload.get("item_results")) if isinstance(item, dict)]
    verdict = (
        _verdict(VERDICT_DIAGNOSTIC_OBSERVATION, "b2_live_llm_candidate_synthesis_collected")
        if contract_valid
        else _verdict(VERDICT_READINESS_BLOCKER, B2_DIAGNOSTIC_FAILURE)
    )
    return {
        "diagnostic_lane": B2_DIAGNOSTIC_LANE,
        "activation": "live_diagnostic",
        "manager_role": payload.get("manager_role"),
        "candidate_estimate_present": bool(item_results),
        "item_result_count": len(item_results),
        "payload_shape_valid": payload_shape_valid,
        "forbidden_mutation_fields_present": forbidden_fields,
        "mutation_attempted": mutation_attempted,
        "mutation_authority": False,
        "canonical_truth_authority": False,
        "ledger_truth_authority": False,
        "source_priority_authority": False,
        "product_semantic_authority": False,
        "provider_params": _dict(payload.get("provider_params")),
        "verdict_category": verdict["category"],
        "failure_family": None if contract_valid else B2_DIAGNOSTIC_FAILURE,
        "verdict": verdict,
    }


def build_product_semantic_decision_pack(
    *,
    observations: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    observed = observations or {}
    decisions: list[dict[str, Any]] = []
    for template in _PRODUCT_DECISION_TEMPLATES:
        decision = dict(template)
        observation = _dict(observed.get(str(decision["decision_id"])))
        decision["observed_system_behavior"] = observation.get("observed_system_behavior", "not_observed")
        decision["observed_live_llm_behavior"] = observation.get("observed_live_llm_behavior", "not_observed")
        decision["requires_user_approval"] = True
        decision["status"] = "pending"
        decision["canonicalizes_product_semantics"] = False
        decisions.append(decision)
    return {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pack_type": "product_semantic_decision_pack",
        "pack_status": "pending_user_decision",
        "canonicalizes_product_semantics": False,
        "decision_count": len(decisions),
        "decisions": decisions,
    }


def build_live_diagnostic_macro_report(
    *,
    live_preflight: dict[str, Any],
    phase_c_gate_status: str,
    b2_live_llm_diagnostic: dict[str, Any],
    product_semantic_decision_pack: dict[str, Any],
) -> dict[str, Any]:
    product_decision_required = bool(_list(product_semantic_decision_pack.get("decisions")))
    phase_c_readiness = {
        "status": phase_c_gate_status,
        "readiness_pass": phase_c_gate_status not in {"hard_fail", "flagged"},
    }
    provider_schema_valid = b2_live_llm_diagnostic.get("verdict_category") != VERDICT_READINESS_BLOCKER
    return {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "macro_batch": "live_diagnostic_evidence_product_semantics_decision_pack",
        "outputs": [
            "live_diagnostic_report",
            "b2_live_llm_diagnostic_lane",
            "product_semantic_decision_pack",
        ],
        "live_preflight": _dict(live_preflight),
        "phase_c_gate_status": phase_c_gate_status,
        "b2_live_llm_diagnostic": _dict(b2_live_llm_diagnostic),
        "product_semantic_decision_pack": _dict(product_semantic_decision_pack),
        "verdict": classify_live_diagnostic_verdict(
            phase_c_live_readiness=phase_c_readiness,
            provider_schema_valid=provider_schema_valid,
            product_decision_required=product_decision_required,
        ),
        "canonicalizes_product_semantics": False,
        "user_facing_behavior_changed": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
    }


def _verdict(category: str, reason: str) -> dict[str, Any]:
    return {
        "category": category,
        "reason": reason,
        "canonicalizes_product_semantics": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the live diagnostic product semantic decision pack.")
    parser.add_argument("--live-report", default=None)
    parser.add_argument("--b2-pass2-report", default=None)
    parser.add_argument("--observations", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    live_report = _read_json_optional(args.live_report)
    b2_pass2 = _read_json_optional(args.b2_pass2_report)
    observations = _read_json_optional(args.observations)
    decision_pack = build_product_semantic_decision_pack(observations=observations or None)
    live_preflight = _dict(live_report.get("live_preflight") if live_report else None) or {
        "live_test_mode": "diagnostic",
        "readiness_claim_scope": "diagnostic_live_smoke",
    }
    phase_c_gate_status = str(
        (live_report.get("phase_c_gate_status") if live_report else None)
        or _dict(live_report.get("summary") if live_report else None).get("phase_c_gate_status")
        or "not_run"
    )
    report = build_live_diagnostic_macro_report(
        live_preflight=live_preflight,
        phase_c_gate_status=phase_c_gate_status,
        b2_live_llm_diagnostic=build_b2_live_llm_diagnostic_evidence(b2_pass2),
        product_semantic_decision_pack=decision_pack,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_path": str(output_path),
                "decision_count": decision_pack["decision_count"],
                "verdict_category": report["verdict"]["category"],
                "canonicalizes_product_semantics": report["canonicalizes_product_semantics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _read_json_optional(path_text: str | None) -> dict[str, Any] | None:
    if not path_text:
        return None
    path = Path(path_text)
    return json.loads(path.read_text(encoding="utf-8-sig"))


__all__ = [
    "B2_DIAGNOSTIC_FAILURE",
    "B2_DIAGNOSTIC_LANE",
    "VERDICT_DIAGNOSTIC_OBSERVATION",
    "VERDICT_PRODUCT_DECISION_REQUIRED",
    "VERDICT_READINESS_BLOCKER",
    "build_b2_live_llm_diagnostic_evidence",
    "build_live_diagnostic_macro_report",
    "build_product_semantic_decision_pack",
    "classify_live_diagnostic_verdict",
]


if __name__ == "__main__":
    raise SystemExit(main())
