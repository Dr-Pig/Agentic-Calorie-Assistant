from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
B2_ASK_FIRST_POLICY_VIOLATION = "b2_ask_first_policy_violation"
B2_EMPTY_ITEM_RESULTS = "b2_empty_item_results"
B2_LIVE_CONTRACT_CASE_IDS = ("B2-002", "B2-007", "B2-001", "B2-009", "B2-004", "B2-008")
ASK_FIRST_SELF_SELECTED_BASKET_DECISION_ID = "self_selected_basket_without_listed_items"

_B2_LIVE_FORBIDDEN_OUTPUT_FIELDS = (
    "logged",
    "draft",
    "canonical_write",
    "canonical_commit",
    "ledger_update",
    "ledger_mutation",
    "mutation_result",
    "mutation_intent",
    "commit",
    "correction_applied",
    "source_priority_decision",
    "product_semantic_decision",
)

_PRODUCT_DECISION_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "decision_id": "pearl_milk_tea_missing_sugar_size",
        "case": "Pearl milk tea with missing sugar level and size.",
        "current_spec_posture": "Approved: missing sugar/size pearl milk tea is estimable and may log with strong follow-up.",
        "decision_needed": "Resolved: logged estimate + follow-up refinement.",
        "options": ["draft_with_followup", "logged_estimate_with_followup"],
        "recommended_option": "logged_estimate_with_followup",
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

_APPROVED_PRODUCT_DECISIONS: dict[str, dict[str, Any]] = {
    "pearl_milk_tea_missing_sugar_size": {
        "status": "approved",
        "selected_policy": "logged_estimate_with_followup",
        "approval_source": "user_approved_product_semantics",
        "supersedes_stale_expectations": [
            "old_c001_draft_first_oracle",
            "pending_decision_pack_status",
        ],
    }
}


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


def build_b2_live_llm_diagnostic_contract_report(
    *,
    phase_b2_report: dict[str, Any],
    provider_outputs_by_case_id: dict[str, dict[str, Any]] | None = None,
    provider_mode: str = "fake",
    payload_artifact_id: str = "deterministic_b2_artifact",
    model_profile: str = "fake-contract-provider",
    schema_mode: str = "json_schema",
    selected_case_ids: tuple[str, ...] = B2_LIVE_CONTRACT_CASE_IDS,
    approved_ask_first_policy_ids: tuple[str, ...] = (),
    provider_traces_by_case_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate fake Pass 2 outputs against deterministic B2 packet contracts.

    This harness is an evaluator only: it consumes the deterministic B2 artifact
    and provider-shaped candidate output, then reports contract violations.
    """

    provider_outputs = provider_outputs_by_case_id or {}
    provider_traces = provider_traces_by_case_id or {}
    case_results = [
        _validate_b2_live_contract_case(
            _case_by_id(phase_b2_report, case_id),
            provider_outputs.get(case_id),
            provider_trace=provider_traces.get(case_id),
            approved_ask_first_policy_ids=approved_ask_first_policy_ids,
        )
        for case_id in selected_case_ids
    ]
    verdict_category = _contract_report_verdict(case_results)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "diagnostic_lane": B2_DIAGNOSTIC_LANE,
        "harness": "b2_live_llm_diagnostic_contract",
        "provider_mode": provider_mode,
        "live_invoked": False,
        "readiness_claimed": False,
        "live_provider_diagnostic_complete": False,
        "payload_artifact_id": payload_artifact_id,
        "schema_mode": schema_mode,
        "model_profile": model_profile,
        "provider_params": {
            "provider": provider_mode,
            "model_profile": model_profile,
            "schema_mode": schema_mode,
        },
        "selected_case_ids": list(selected_case_ids),
        "case_ids_are_diagnostic_labels_only": True,
        "report_builder_role": "evaluator_only",
        "case_results": case_results,
        "verdict_category": verdict_category,
        "verdict": _verdict(verdict_category, _contract_report_reason(verdict_category)),
        "diagnostic_scope": "b2_packet_synthesis_only",
        "readiness_scope": "none",
        "user_facing_enabled": False,
        "mutation_enabled": False,
        "mutation_authority": False,
        "ledger_truth_authority": False,
        "source_priority_authority": False,
        "product_semantic_authority": False,
        "canonical_truth_authority": False,
        "canonicalizes_product_semantics": False,
        "user_facing_behavior_changed": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "tavily_or_web_activated": False,
    }


def _case_by_id(report: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in _list(report.get("cases")):
        candidate = _dict(case)
        if candidate.get("case_id") == case_id:
            return candidate
    raise KeyError(f"B2 deterministic artifact missing case_id={case_id}")


def _validate_b2_live_contract_case(
    deterministic_case: dict[str, Any],
    provider_output: dict[str, Any] | None,
    *,
    provider_trace: dict[str, Any] | None = None,
    approved_ask_first_policy_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    case_id = str(deterministic_case.get("case_id") or "")
    payload = _dict(provider_output) if provider_output is not None else _default_fake_provider_output(deterministic_case)
    item_results = [_dict(item) for item in _list(payload.get("item_results")) if isinstance(item, dict)]
    packet_permissions = _packet_permissions(deterministic_case)
    rejected_packet_ids = _rejected_packet_ids(deterministic_case)
    evidence_refs = _evidence_refs(item_results)
    forbidden_fields = _forbidden_output_fields(payload, item_results)
    trace = _dict(provider_trace)
    output_diagnostics = _output_diagnostics(payload, item_results, trace)
    accepted_packets_count = _accepted_packets_count(deterministic_case)
    blockers: list[str] = []
    product_decisions_required: list[str] = []
    failure_family = B2_DIAGNOSTIC_FAILURE

    if _is_approved_ask_first_case(
        deterministic_case,
        approved_ask_first_policy_ids=approved_ask_first_policy_ids,
    ):
        if "item_results" in payload:
            blockers.append("ask_first_item_results_present")
        if _has_estimate(item_results) or _has_top_level_estimate(payload):
            blockers.append("ask_first_estimate_present")
        if evidence_refs or _has_top_level_evidence_refs(payload):
            blockers.append("ask_first_evidence_refs_present")
        if forbidden_fields or _has_mutation_intent(payload, item_results):
            blockers.append("forbidden_authority_fields")
        if payload.get("payload_shape_valid") is False:
            blockers.append("provider_schema_invalid")
        verdict_category = VERDICT_READINESS_BLOCKER if blockers else VERDICT_DIAGNOSTIC_OBSERVATION
        if blockers:
            failure_family = B2_ASK_FIRST_POLICY_VIOLATION
        return {
            "case_id": case_id,
            "case_label_only": True,
            "input_message": deterministic_case.get("input_message"),
            "provider_mode": "fake",
            "live_invoked": False,
            "source_path": _dict(deterministic_case.get("source_selection")).get("source_path"),
            "contract_type": "clarify_only",
            "ask_first_policy_id": ASK_FIRST_SELF_SELECTED_BASKET_DECISION_ID,
            "packet_permissions": packet_permissions,
            "rejected_packet_ids": sorted(rejected_packet_ids),
            "evidence_refs": sorted(evidence_refs),
            "rejected_packet_evidence_refs": [],
            "item_result_count": len(item_results),
            "forbidden_fields_present": forbidden_fields,
            "blockers": _dedupe(blockers),
            "product_decisions_required": [],
            "failure_family": failure_family if blockers else None,
            "verdict_category": verdict_category,
            "verdict": _verdict(verdict_category, failure_family if blockers else _case_verdict_reason(verdict_category)),
        }

    if not item_results:
        blockers.append("missing_item_results")
    if forbidden_fields:
        blockers.append("forbidden_authority_fields")
    if payload.get("payload_shape_valid") is False:
        blockers.append("provider_schema_invalid")

    rejected_evidence_refs = sorted(ref for ref in evidence_refs if ref in rejected_packet_ids)
    if rejected_evidence_refs:
        blockers.append("rejected_packet_used_as_evidence")

    exact_item_results = [item for item in item_results if str(item.get("exactness_posture") or "") == "exact"]
    if _is_generic_anchor_case(deterministic_case) and exact_item_results:
        blockers.append("generic_anchor_returned_exact")
    if exact_item_results and not _exactness_permitted(exact_item_results, packet_permissions["exact_packet_ids"]):
        blockers.append("exactness_exceeds_packet_permission")

    if _is_query_only_case(deterministic_case) and _has_mutation_intent(payload, item_results):
        blockers.append("query_only_mutation_intent")

    if _is_composition_unknown_case(deterministic_case) and _has_estimate(item_results):
        product_decisions_required.append("unknown_composition_estimated")

    verdict_category = (
        VERDICT_READINESS_BLOCKER
        if blockers
        else VERDICT_PRODUCT_DECISION_REQUIRED
        if product_decisions_required
        else VERDICT_DIAGNOSTIC_OBSERVATION
    )
    if "missing_item_results" in blockers:
        failure_family = B2_EMPTY_ITEM_RESULTS
    return {
        "case_id": case_id,
        "case_label_only": True,
        "input_message": deterministic_case.get("input_message"),
        "provider_mode": "fake",
        "live_invoked": False,
        "source_path": _dict(deterministic_case.get("source_selection")).get("source_path"),
        "contract_type": "item_results_synthesis",
        "item_results_required": True,
        "min_item_results": 1,
        "accepted_packets_count": accepted_packets_count,
        "accepted_usage": packet_permissions["accepted_usage"],
        "allowed_exactness": _allowed_exactness(packet_permissions),
        "packet_permissions": packet_permissions,
        "rejected_packet_ids": sorted(rejected_packet_ids),
        "evidence_refs": sorted(evidence_refs),
        "rejected_packet_evidence_refs": rejected_evidence_refs,
        "item_result_count": len(item_results),
        "forbidden_fields_present": forbidden_fields,
        "blockers": _dedupe(blockers),
        "product_decisions_required": _dedupe(product_decisions_required),
        "failure_family": failure_family if blockers else None,
        "empty_item_results_root_cause": _empty_item_results_root_cause(
            blockers=blockers,
            accepted_packets_count=accepted_packets_count,
            output_diagnostics=output_diagnostics,
        ),
        **output_diagnostics,
        "verdict_category": verdict_category,
        "verdict": _verdict(verdict_category, _case_verdict_reason(verdict_category)),
    }


def _default_fake_provider_output(deterministic_case: dict[str, Any]) -> dict[str, Any]:
    manager_pass_2 = _dict(deterministic_case.get("manager_pass_2"))
    return {
        "payload_shape_valid": True,
        "item_results": [_dict(item) for item in _list(manager_pass_2.get("item_results"))],
        "provider_params": {"provider": "fake", "model_profile": "fake-contract-provider"},
        "mutation_attempted": False,
    }


def _packet_permissions(deterministic_case: dict[str, Any]) -> dict[str, Any]:
    exact_packet_ids: set[str] = set()
    anchor_packet_ids: set[str] = set()
    packets_by_id: dict[str, dict[str, Any]] = {
        str(packet.get("packet_id")): _dict(packet)
        for packet in _list(deterministic_case.get("packets"))
        if isinstance(packet, dict) and packet.get("packet_id")
    }
    for item in _list(_dict(deterministic_case.get("manager_pass_2")).get("item_results")):
        if not isinstance(item, dict):
            continue
        for evidence in _list(item.get("evidence_used")):
            evidence_dict = _dict(evidence)
            packet_id = str(evidence_dict.get("packet_id") or "")
            if not packet_id:
                continue
            usage = str(evidence_dict.get("usage") or "")
            if usage == "exact" and packets_by_id.get(packet_id, {}).get("supports_exact_claim") is True:
                exact_packet_ids.add(packet_id)
            elif usage in {"anchor", "fallback"}:
                anchor_packet_ids.add(packet_id)
    return {
        "exact_packet_ids": sorted(exact_packet_ids),
        "anchor_packet_ids": sorted(anchor_packet_ids),
        "accepted_usage": "exact" if exact_packet_ids else "anchor" if anchor_packet_ids else "none",
    }


def _accepted_packets_count(deterministic_case: dict[str, Any]) -> int:
    permissions = _packet_permissions(deterministic_case)
    return len(permissions["exact_packet_ids"]) + len(permissions["anchor_packet_ids"])


def _allowed_exactness(packet_permissions: dict[str, Any]) -> str:
    if packet_permissions["accepted_usage"] == "exact":
        return "exact"
    if packet_permissions["accepted_usage"] == "anchor":
        return "estimated"
    return "none"


def _rejected_packet_ids(deterministic_case: dict[str, Any]) -> set[str]:
    rejected: set[str] = set()
    manager_pass_2 = _dict(deterministic_case.get("manager_pass_2"))
    for item in _list(manager_pass_2.get("item_results")):
        item_dict = _dict(item)
        for candidate in _list(item_dict.get("rejected_candidates")):
            packet_id = str(_dict(candidate).get("packet_id") or "")
            if packet_id:
                rejected.add(packet_id)
    return rejected


def _evidence_refs(item_results: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for item in item_results:
        for evidence in _list(item.get("evidence_used")):
            packet_id = str(_dict(evidence).get("packet_id") or "")
            if packet_id:
                refs.add(packet_id)
    return refs


def _forbidden_output_fields(payload: dict[str, Any], item_results: list[dict[str, Any]]) -> list[str]:
    fields: set[str] = {field for field in _B2_LIVE_FORBIDDEN_OUTPUT_FIELDS if field in payload}
    for item in item_results:
        fields.update(field for field in _B2_LIVE_FORBIDDEN_OUTPUT_FIELDS if field in item)
    return sorted(fields)


def _is_generic_anchor_case(deterministic_case: dict[str, Any]) -> bool:
    return _dict(deterministic_case.get("source_selection")).get("source_path") == "generic_anchor"


def _is_query_only_case(deterministic_case: dict[str, Any]) -> bool:
    source_selection = _dict(deterministic_case.get("source_selection"))
    mutation = _dict(deterministic_case.get("mutation"))
    return source_selection.get("read_only") is True or mutation.get("reason") == "no_mutation_intent"


def _is_composition_unknown_case(deterministic_case: dict[str, Any]) -> bool:
    source_selection = _dict(deterministic_case.get("source_selection"))
    if source_selection.get("source_path") == "ask_user":
        return True
    for packet in _list(deterministic_case.get("packets")):
        packet_dict = _dict(packet)
        if packet_dict.get("semantic_problem") == "composition_unknown":
            return True
    return False


def _is_approved_ask_first_case(
    deterministic_case: dict[str, Any],
    *,
    approved_ask_first_policy_ids: tuple[str, ...],
) -> bool:
    if ASK_FIRST_SELF_SELECTED_BASKET_DECISION_ID not in set(approved_ask_first_policy_ids):
        return False
    if not _is_composition_unknown_case(deterministic_case):
        return False
    source_selection = _dict(deterministic_case.get("source_selection"))
    if source_selection.get("source_path") == "ask_user":
        return True
    return any(
        _dict(packet).get("rule_id") == "self_selected_basket_without_ingredients"
        for packet in _list(deterministic_case.get("packets"))
    )


def _has_mutation_intent(payload: dict[str, Any], item_results: list[dict[str, Any]]) -> bool:
    if payload.get("mutation_attempted") is True:
        return True
    if any(field in payload for field in ("mutation_intent", "ledger_update", "mutation_result", "logged", "draft")):
        return True
    return any(
        any(field in item for field in ("mutation_intent", "ledger_update", "mutation_result", "logged", "draft"))
        for item in item_results
    )


def _has_estimate(item_results: list[dict[str, Any]]) -> bool:
    for item in item_results:
        if item.get("likely_kcal") is not None:
            return True
        kcal_range = item.get("kcal_range")
        if isinstance(kcal_range, list) and any(value is not None for value in kcal_range):
            return True
    return False


def _has_top_level_estimate(payload: dict[str, Any]) -> bool:
    if payload.get("likely_kcal") is not None:
        return True
    kcal_range = payload.get("kcal_range")
    return isinstance(kcal_range, list) and any(value is not None for value in kcal_range)


def _has_top_level_evidence_refs(payload: dict[str, Any]) -> bool:
    return bool(_list(payload.get("evidence_used")) or _list(payload.get("evidence_refs")))


def _output_diagnostics(
    payload: dict[str, Any],
    item_results: list[dict[str, Any]],
    trace: dict[str, Any],
) -> dict[str, Any]:
    raw_item_results_count = _int_or_default(trace.get("raw_item_results_count"), len(item_results))
    normalized_item_results_count = _int_or_default(trace.get("normalized_item_results_count"), len(item_results))
    raw_keys = [str(item) for item in _list(trace.get("raw_top_level_keys"))] or sorted(str(key) for key in payload)
    normalized_keys = sorted(str(key) for key in payload)
    return {
        "raw_provider_output_has_items": raw_item_results_count > 0,
        "normalized_output_has_items": normalized_item_results_count > 0,
        "raw_item_results_count": raw_item_results_count,
        "normalized_item_results_count": normalized_item_results_count,
        "raw_top_level_keys": raw_keys,
        "normalized_top_level_keys": normalized_keys,
        "raw_provider_output_excerpt": str(trace.get("raw_provider_output_excerpt") or ""),
        "normalized_provider_output_summary": {
            "top_level_keys": normalized_keys,
            "item_results_count": normalized_item_results_count,
            "payload_shape_valid": payload.get("payload_shape_valid") is not False,
        },
    }


def _empty_item_results_root_cause(
    *,
    blockers: list[str],
    accepted_packets_count: int,
    output_diagnostics: dict[str, Any],
) -> str | None:
    if "missing_item_results" not in blockers:
        return None
    if accepted_packets_count < 1:
        return "payload_missing_evidence"
    if output_diagnostics["raw_provider_output_has_items"] and not output_diagnostics["normalized_output_has_items"]:
        return "provider_bridge_dropped_items"
    if "item_results" in output_diagnostics["raw_top_level_keys"]:
        return "model_returned_empty_items"
    return "prompt_contract_under_specified"


def _int_or_default(value: Any, default: int) -> int:
    return value if isinstance(value, int) else default


def _exactness_permitted(item_results: list[dict[str, Any]], exact_packet_ids: list[str]) -> bool:
    allowed = set(exact_packet_ids)
    if not allowed:
        return False
    for item in item_results:
        refs = _evidence_refs([item])
        if not refs or not refs.issubset(allowed):
            return False
    return True


def _contract_report_verdict(case_results: list[dict[str, Any]]) -> str:
    if any(result.get("verdict_category") == VERDICT_READINESS_BLOCKER for result in case_results):
        return VERDICT_READINESS_BLOCKER
    if any(result.get("verdict_category") == VERDICT_PRODUCT_DECISION_REQUIRED for result in case_results):
        return VERDICT_PRODUCT_DECISION_REQUIRED
    return VERDICT_DIAGNOSTIC_OBSERVATION


def _contract_report_reason(verdict_category: str) -> str:
    if verdict_category == VERDICT_READINESS_BLOCKER:
        return B2_DIAGNOSTIC_FAILURE
    if verdict_category == VERDICT_PRODUCT_DECISION_REQUIRED:
        return "pending_product_semantic_decision"
    return "b2_fake_provider_contract_diagnostic_collected"


def _case_verdict_reason(verdict_category: str) -> str:
    if verdict_category == VERDICT_READINESS_BLOCKER:
        return B2_DIAGNOSTIC_FAILURE
    if verdict_category == VERDICT_PRODUCT_DECISION_REQUIRED:
        return "pending_product_semantic_decision"
    return "case_contract_passed_as_diagnostic_observation"


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


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
        approved = _dict(_APPROVED_PRODUCT_DECISIONS.get(str(decision["decision_id"])))
        if approved:
            decision.update(approved)
            decision["requires_user_approval"] = False
        else:
            decision["requires_user_approval"] = True
            decision["status"] = "pending"
        decision["canonicalizes_product_semantics"] = False
        decisions.append(decision)
    pending_count = sum(1 for decision in decisions if decision.get("status") == "pending")
    approved_count = sum(1 for decision in decisions if decision.get("status") == "approved")
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pack_type": "product_semantic_decision_pack",
        "pack_status": "pending_user_decision" if pending_count else "approved",
        "canonicalizes_product_semantics": False,
        "decision_count": len(decisions),
        "pending_decision_count": pending_count,
        "approved_decision_count": approved_count,
        "decisions": decisions,
    }


def build_live_diagnostic_macro_report(
    *,
    live_preflight: dict[str, Any],
    phase_c_gate_status: str,
    b2_live_llm_diagnostic: dict[str, Any],
    product_semantic_decision_pack: dict[str, Any],
) -> dict[str, Any]:
    product_decision_required = any(
        _dict(decision).get("status") == "pending" for decision in _list(product_semantic_decision_pack.get("decisions"))
    )
    phase_c_readiness = {
        "status": phase_c_gate_status,
        "readiness_pass": phase_c_gate_status not in {"hard_fail", "flagged"},
    }
    provider_schema_valid = b2_live_llm_diagnostic.get("verdict_category") != VERDICT_READINESS_BLOCKER
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
    "ASK_FIRST_SELF_SELECTED_BASKET_DECISION_ID",
    "B2_ASK_FIRST_POLICY_VIOLATION",
    "B2_DIAGNOSTIC_FAILURE",
    "B2_EMPTY_ITEM_RESULTS",
    "B2_DIAGNOSTIC_LANE",
    "VERDICT_DIAGNOSTIC_OBSERVATION",
    "VERDICT_PRODUCT_DECISION_REQUIRED",
    "VERDICT_READINESS_BLOCKER",
    "build_b2_live_llm_diagnostic_contract_report",
    "build_b2_live_llm_diagnostic_evidence",
    "build_live_diagnostic_macro_report",
    "build_product_semantic_decision_pack",
    "classify_live_diagnostic_verdict",
]


if __name__ == "__main__":
    raise SystemExit(main())
