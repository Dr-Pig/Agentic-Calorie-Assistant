from __future__ import annotations

from typing import Any

from app.shared.contracts.correction_operation import structured_payload_requests_remove_item


FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID = "founder_live_contract"
FOUNDER_LIVE_MANAGER_SCHEMA_NAME = "founder_live_manager_contract"
FOUNDER_LIVE_MANAGER_SCHEMA_VERSION = "v1"
FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY = "synthetic_tool_transport"
FOUNDER_LIVE_MANAGER_TOOL_NAME = "manager_structured_decision"
FOUNDER_LIVE_MANAGER_COMMIT_WITHOUT_EVIDENCE_REPAIR_FAMILY = "commit_without_evidence"
FOUNDER_LIVE_MANAGER_REPAIR_REQUIRED_TOOL_BY_FAMILY = {
    FOUNDER_LIVE_MANAGER_COMMIT_WITHOUT_EVIDENCE_REPAIR_FAMILY: "estimate_nutrition",
}
FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS = [
    "commit",
    "correction_applied",
    "overshoot_note",
]
FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES = [
    "resolve_correction_target",
    "estimate_nutrition",
    "compare_against_budget",
]

FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS = [
    "manager_action",
    "intent",
    "intent_type",
    "workflow_effect",
    "target_attachment",
    "exactness",
    "confidence",
    "evidence_posture",
    "semantic_decision",
    "answer_contract",
]

FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS = {
    "manager_action": "manager_loop_control",
    "intent": "runtime_router_and_trace_classifier",
    "intent_type": "active_runtime_router",
    "workflow_effect": "transition_guard_and_mutation_boundary",
    "target_attachment": "meal_thread_attachment_and_correction_path",
    "exactness": "nutrition_final_mapping_and_renderer_exactness_guard",
    "confidence": "uncertainty_and_evidence_honesty_trace",
    "evidence_posture": "b2_evidence_and_final_mapping_guard",
    "semantic_decision": "semantic_owner_trace_and_final_mapping_alignment",
    "answer_contract": "renderer_boundary",
}

FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES = [
    "complete_onboarding",
    "answer_remaining_budget",
    "onboarding_required",
    "manager_unavailable",
    "log_meal",
]


FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS = [
    "commit",
    "ask_followup",
    "correction_applied",
    "overshoot_note",
    "answer_only",
    "no_commit",
    "answer_remaining_budget",
    "onboarding_required",
    "manager_unavailable",
    "complete_onboarding",
]
FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES = {
    "refinement_not_commit_gate",
    "size_clarification",
}


FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT = {
    "complete_onboarding": "complete_onboarding",
    "answer_remaining_budget": "answer_remaining_budget",
    "answer_query": "log_meal",
    "log_meal": "log_meal",
    "correct_meal": "log_meal",
}
FOUNDER_LIVE_MANAGER_CONTRACT_POLICY = {
    "intent_type_by_semantic_intent": dict(FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT),
    "final_actions_requiring_evidence": list(FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS),
    "required_tool_when_evidence_missing": "estimate_nutrition",
    "query_only_rule": {
        "semantic_intent": "answer_query",
        "workflow_effect": "answer_only",
        "final_action": "answer_only",
        "mutation_intent_candidate": "no_mutation",
    },
    "correction_rule": {
        "semantic_intent": "correct_meal",
        "final_action": "correction_applied",
        "mutation_intent_candidate": "correction_write",
    },
    "explicit_item_removal_rule": {
        "semantic_intent": "correct_meal",
        "workflow_family": "correction",
        "operation": "remove_item",
        "evidence_type": "target_evidence",
        "nutrition_evidence_required": False,
        "manager_role": "propose_target_or_call_resolve_correction_target",
        "runtime_role": "validate_unique_writable_target",
        "forbidden": ["hard_delete", "whole_meal_undo", "raw_text_deterministic_routing"],
    },
    "composition_unknown_rule": {
        "workflow_effect": "ask_followup",
        "final_action": "ask_followup",
        "mutation_intent_candidate": "no_mutation",
        "estimate_tool_allowed": False,
    },
    "followup_question_rule": {
        "question_required_postures": sorted(FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES),
        "fallback_postures_when_no_question": ["none", "refinement_optional", "closed"],
    },
    "followup_question_required_postures": sorted(FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES),
    "forbidden_repair_shortcuts": [
        "case_id_matching",
        "raw_text_matching",
        "food_name_specific_patch",
        "deterministic_semantic_rewrite",
    ],
}
FOUNDER_LIVE_MANAGER_CONTRACT_POLICY_SUMMARY = (
    "Founder live manager contract policy: keep intent_type aligned with semantic_decision.current_turn_intent "
    "(answer_query/log_meal/correct_meal all route through intent_type=log_meal except onboarding/budget lanes); "
    "if no current estimate_nutrition tool result exists, call estimate_nutrition before final commit, "
    "nutrition-changing correction_applied, or overshoot_note; query-only nutrition questions must answer_only with no mutation; "
    "correct_meal must update the prior target with correction_applied/correction_write, not commit as a new meal; "
    "explicit item removal is a correction-family turn: propose a target item or call resolve_correction_target, "
    "then let runtime validate target uniqueness/writeability; target evidence is sufficient for remove_item and "
    "estimate_nutrition is not required; do not hard-delete or undo a whole meal; "
    "self-selected basket or composition-unknown meals must ask_followup/no_mutation until components are known "
    "and must not call estimate_nutrition while composition is unknown; "
    "refinement_not_commit_gate and size_clarification follow-up postures require a followup_question."
)
FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION = (
    "Current-loop nutrition evidence exists only when "
    "manager_contract_evidence_state.nutrition_evidence_present=true. If it is false and the intended final_action "
    "would be commit, nutrition-changing correction_applied, or overshoot_note, return manager_action='call_tools' with estimate_nutrition "
    "instead of manager_action='final'. Do not substitute final_action='ask_followup' or no_commit while "
    "semantic_decision.final_action_candidate is commit, correction_applied, or overshoot_note. "
    "Exception: explicit item removal is correction_applied/remove_item and requires target evidence from "
    "resolve_correction_target or a structured target_attachment validated by runtime; it does not require "
    "estimate_nutrition because existing canonical item calories are used for ledger recompute. "
    "If evidence_posture is requires_tool, evidence_missing, or evidence_pending, or if "
    "semantic_decision.estimation_posture is pending_tool_call or tool_pending, the current response must be "
    "manager_action='call_tools' with estimate_nutrition, not manager_action='final'. "
    "Exception: if your semantic decision is composition-unknown "
    "ask_followup/no_mutation, return manager_action='final' with final_action='ask_followup' and no tool_calls; "
    "do not estimate."
)
FOUNDER_LIVE_MANAGER_FOLLOWUP_INSTRUCTION = (
    "Use followup_posture='refinement_not_commit_gate' or 'size_clarification' only when you also provide "
    "a concrete user-facing followup_question in semantic_decision.followup_question or "
    "answer_contract.followup_question. If no concrete follow-up question is needed, use followup_posture='none', "
    "'closed', or 'refinement_optional' instead. Do not use refinement_not_commit_gate as a generic uncertainty "
    "or honesty label."
)
FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES = [
    {
        "name": "evidence_required_candidate_missing_evidence",
        "valid": {
            "manager_action": "call_tools",
            "tool_calls": [{"name": "estimate_nutrition"}],
            "evidence_posture": "evidence_pending",
            "semantic_decision": {
                "final_action_candidate": "commit_or_correction_applied_or_overshoot_note",
                "estimation_posture": "pending_tool_call",
            },
        },
        "invalid": {
            "manager_action": "final",
            "final_action": "ask_followup_or_no_commit_or_missing",
            "evidence_posture": "evidence_missing",
            "semantic_decision": {
                "final_action_candidate": "commit_or_correction_applied_or_overshoot_note",
                "estimation_posture": "pending_tool_call",
            },
        },
    },
    {
        "name": "followup_posture_without_question",
        "valid": {
            "semantic_decision": {
                "followup_posture": "none_or_closed_or_refinement_optional",
                "followup_question": None,
            },
        },
        "invalid": {
            "semantic_decision": {
                "followup_posture": "refinement_not_commit_gate_or_size_clarification",
                "followup_question": None,
            },
        },
    },
    {
        "name": "composition_unknown_exception",
        "valid": {
            "manager_action": "final",
            "final_action": "ask_followup",
            "workflow_effect": "ask_followup",
            "tool_calls": [],
            "semantic_decision": {
                "final_action_candidate": "ask_followup",
                "mutation_intent_candidate": "no_mutation",
                "estimation_posture": "composition_unknown_basket",
            },
        },
    },
    {
        "name": "explicit_item_removal_as_correction",
        "valid": {
            "manager_action": "call_tools",
            "tool_calls": [
                {
                    "name": "resolve_correction_target",
                    "arguments": {
                        "canonical_name": "target_item_name",
                        "target_proposal_source": "manager_structured_output",
                    },
                }
            ],
            "semantic_decision": {
                "current_turn_intent": "correct_meal",
                "final_action_candidate": "correction_applied",
                "mutation_intent_candidate": "correction_write",
                "target_attachment": {"operation": "remove_item"},
            },
        },
        "valid_after_target_evidence": {
            "manager_action": "final",
            "final_action": "correction_applied",
            "target_attachment": {"operation": "remove_item", "meal_item_id": "validated_target"},
            "semantic_decision": {
                "current_turn_intent": "correct_meal",
                "final_action_candidate": "correction_applied",
                "mutation_intent_candidate": "correction_write",
                "target_attachment": {"operation": "remove_item"},
            },
        },
        "invalid": {
            "manager_action": "final",
            "final_action": "commit",
            "semantic_decision": {
                "current_turn_intent": "correct_meal",
                "mutation_intent_candidate": "canonical_write",
            },
        },
    },
]


def is_founder_live_manager_contract(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return str(constraints.get("manager_contract_profile_id") or "") == FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID


def founder_live_manager_repair_failure_family(constraints: dict[str, Any] | None) -> str:
    if not isinstance(constraints, dict):
        return ""
    if not bool(constraints.get("guard_feedback_repair_request")):
        return ""
    return str(constraints.get("guard_feedback_failure_family") or "")


def founder_live_manager_contract_constraints(
    profile_id: str,
    *,
    tool_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    tool_result_names = _tool_result_names(tool_results)
    target_evidence = _target_evidence_state(tool_results)
    return {
        "manager_contract_profile_id": FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID,
        "manager_contract_provider_profile_id": profile_id,
        "manager_contract_schema_name": FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
        "manager_contract_schema_version": FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
        "manager_contract_transport_policy": FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
        "manager_contract_policy": dict(FOUNDER_LIVE_MANAGER_CONTRACT_POLICY),
        "manager_contract_policy_summary": FOUNDER_LIVE_MANAGER_CONTRACT_POLICY_SUMMARY,
        "manager_contract_evidence_instruction": FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION,
        "manager_contract_followup_instruction": FOUNDER_LIVE_MANAGER_FOLLOWUP_INSTRUCTION,
        "manager_contract_examples": [dict(item) for item in FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES],
        "manager_contract_evidence_state": {
            "tool_result_names": tool_result_names,
            "nutrition_evidence_present": _nutrition_evidence_present(tool_results),
            "target_evidence_present": target_evidence["target_evidence_present"],
            "target_evidence_source": target_evidence["target_evidence_source"],
        },
    }


def founder_live_manager_tool_description() -> str:
    return (
        "Return the manager structured decision payload. Follow the founder live manager contract policy: "
        "intent_type must match semantic_decision.current_turn_intent "
        "(complete_onboarding -> complete_onboarding; answer_remaining_budget -> answer_remaining_budget; "
        "answer_query -> log_meal; log_meal -> log_meal; correct_meal -> log_meal). "
        "For query-only calorie or nutrition questions without a consumption claim, use answer_query, "
        "final_action answer_only, and mutation_intent_candidate no_mutation. "
        "For correct_meal, use correction_applied with correction_write rather than a new commit, and call "
        "estimate_nutrition first when current-loop nutrition evidence is missing for a nutrition-changing correction. "
        "For explicit item removal, treat it as correct_meal/correction_write: propose the target item in "
        "target_attachment or call resolve_correction_target with structured target arguments, then allow runtime "
        "to validate uniqueness/writeability; target evidence is sufficient for remove_item and estimate_nutrition "
        "is not required; do not hard-delete, whole-meal undo, or rely on deterministic raw text routing. "
        "Do not use ask_followup or no_commit as a substitute when semantic_decision.final_action_candidate "
        "is commit, correction_applied, or overshoot_note; call estimate_nutrition first. "
        "If you set evidence_posture to requires_tool, evidence_missing, or evidence_pending, or set "
        "semantic_decision.estimation_posture to pending_tool_call or tool_pending, you must return "
        "manager_action call_tools with estimate_nutrition in this same response. "
        "Any call_tools response must include a non-empty tool_calls array with a supported tool name. "
        "The invalid evidence-required candidate pattern is manager_action final with evidence_missing and "
        "semantic_decision.final_action_candidate still pointing at commit, correction_applied, or overshoot_note. "
        "For a self-selected basket with unknown composition, ask_followup with no_mutation until components are known; "
        "return final ask_followup directly and do not call estimate_nutrition for composition-unknown baskets. "
        "If current tool_results do not include estimate_nutrition evidence, do not finalize commit, "
        "nutrition-changing correction_applied, or overshoot_note; call estimate_nutrition first. "
        "If followup_posture is refinement_not_commit_gate or size_clarification, include a followup_question."
        " If you do not have a concrete follow-up question, use followup_posture none, closed, or "
        "refinement_optional instead of refinement_not_commit_gate."
    )


def _tool_result_names(tool_results: list[dict[str, Any]] | None) -> list[str]:
    names: list[str] = []
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool_name") or item.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def _nutrition_evidence_present(tool_results: list[dict[str, Any]] | None) -> bool:
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool_name") or item.get("name") or "").strip()
        if name != "estimate_nutrition":
            continue
        if item.get("failure_family"):
            continue
        evidence = item.get("evidence")
        if isinstance(evidence, dict) and isinstance(evidence.get("nutrition_payload"), dict):
            return True
    return False


def _target_evidence_state(tool_results: list[dict[str, Any]] | None) -> dict[str, Any]:
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool_name") or item.get("name") or "").strip()
        if name != "resolve_correction_target" or item.get("failure_family"):
            continue
        provenance = item.get("provenance")
        evidence = item.get("evidence")
        target = {}
        if isinstance(provenance, dict) and isinstance(provenance.get("correction_target"), dict):
            target = dict(provenance["correction_target"])
        elif isinstance(evidence, dict) and isinstance(evidence.get("correction_target"), dict):
            target = dict(evidence["correction_target"])
        validation = target.get("manager_target_proposal_validation")
        if isinstance(validation, dict) and validation.get("status") == "rejected":
            continue
        if target.get("meal_thread_id") is not None and target.get("meal_item_id") is not None:
            return {
                "target_evidence_present": True,
                "target_evidence_source": "resolve_correction_target",
            }
    return {
        "target_evidence_present": False,
        "target_evidence_source": None,
    }


def _target_evidence_present(evidence_state: Any) -> bool:
    return isinstance(evidence_state, dict) and evidence_state.get("target_evidence_present") is True


def _final_action_requires_nutrition_evidence(
    *,
    payload: dict[str, Any],
    final_action: str,
    evidence_state: Any,
) -> bool:
    if final_action not in FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS:
        return False
    if final_action == "correction_applied" and structured_payload_requests_remove_item(payload):
        return not _target_evidence_present(evidence_state)
    return True


def validate_founder_live_manager_contract_consistency(
    payload: dict[str, Any],
    *,
    constraints: dict[str, Any] | None = None,
) -> None:
    repair_failure_family = founder_live_manager_repair_failure_family(constraints)
    required_repair_tool = FOUNDER_LIVE_MANAGER_REPAIR_REQUIRED_TOOL_BY_FAMILY.get(repair_failure_family)
    if required_repair_tool:
        manager_action = str(payload.get("manager_action") or "")
        if manager_action != "call_tools":
            raise RuntimeError(
                "founder live manager repair contract requires manager_action='call_tools' "
                f"for guard_feedback.failure_family={repair_failure_family!r}"
            )
        tool_calls = payload.get("tool_calls")
        if not isinstance(tool_calls, list) or not any(
            isinstance(item, dict) and str(item.get("name") or item.get("tool_name") or "") == required_repair_tool
            for item in tool_calls
        ):
            raise RuntimeError(
                "founder live manager repair contract requires tool_calls to include "
                f"{required_repair_tool!r} for guard_feedback.failure_family={repair_failure_family!r}"
            )
    if str(payload.get("manager_action") or "") == "call_tools":
        tool_calls = payload.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            raise RuntimeError(
                "founder live manager contract requires non-empty tool_calls when manager_action='call_tools'"
            )
        invalid_tool_names = [
            str(item.get("name") or item.get("tool_name") or "")
            for item in tool_calls
            if not isinstance(item, dict)
            or str(item.get("name") or item.get("tool_name") or "") not in FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES
        ]
        if invalid_tool_names:
            raise RuntimeError(
                "founder live manager contract tool_calls include unsupported tool names: "
                f"{invalid_tool_names!r}"
            )
    final_action = str(payload.get("final_action") or "")
    if final_action and final_action not in FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS:
        raise RuntimeError(f"founder live manager contract final_action invalid: {final_action!r}")
    evidence_state = constraints.get("manager_contract_evidence_state") if isinstance(constraints, dict) else None
    nutrition_evidence_present = (
        evidence_state.get("nutrition_evidence_present")
        if isinstance(evidence_state, dict)
        else None
    )
    if (
        nutrition_evidence_present is False
        and str(payload.get("manager_action") or "") == "final"
        and final_action == "correction_applied"
        and structured_payload_requests_remove_item(payload)
        and not _target_evidence_present(evidence_state)
    ):
        raise RuntimeError(
            "founder live manager contract remove_item finalization requires target evidence before "
            "final_action='correction_applied'; call resolve_correction_target first"
        )
    if (
        nutrition_evidence_present is False
        and str(payload.get("manager_action") or "") == "final"
        and _final_action_requires_nutrition_evidence(
            payload=payload,
            final_action=final_action,
            evidence_state=evidence_state,
        )
    ):
        raise RuntimeError(
            "founder live manager contract requires current-loop nutrition evidence before "
            f"final_action={final_action!r}; call estimate_nutrition first"
        )
    semantic_decision = payload.get("semantic_decision")
    if not isinstance(semantic_decision, dict):
        return
    final_action_candidate = str(semantic_decision.get("final_action_candidate") or "")
    if (
        nutrition_evidence_present is False
        and str(payload.get("manager_action") or "") == "final"
        and final_action_candidate == "correction_applied"
        and structured_payload_requests_remove_item(payload)
        and not _target_evidence_present(evidence_state)
    ):
        raise RuntimeError(
            "founder live manager contract remove_item finalization requires target evidence before "
            "semantic_decision.final_action_candidate='correction_applied'; call resolve_correction_target first"
        )
    if (
        nutrition_evidence_present is False
        and str(payload.get("manager_action") or "") == "final"
        and _final_action_requires_nutrition_evidence(
            payload=payload,
            final_action=final_action_candidate,
            evidence_state=evidence_state,
        )
    ):
        raise RuntimeError(
            "founder live manager contract requires current-loop nutrition evidence before "
            f"semantic_decision.final_action_candidate={final_action_candidate!r}; "
            "call estimate_nutrition first instead of substituting another final_action"
        )
    semantic_intent = str(semantic_decision.get("current_turn_intent") or "")
    expected_intent_type = FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT.get(semantic_intent)
    if expected_intent_type is None:
        return
    observed_intent_type = str(payload.get("intent_type") or "")
    if observed_intent_type != expected_intent_type:
        raise RuntimeError(
            "founder live manager contract intent_type mismatch: "
            f"semantic_decision.current_turn_intent={semantic_intent!r} "
            f"requires intent_type={expected_intent_type!r}, observed {observed_intent_type!r}"
        )
    if semantic_intent == "answer_query":
        mutation_intent = str(semantic_decision.get("mutation_intent_candidate") or "")
        workflow_effect = str(payload.get("workflow_effect") or semantic_decision.get("workflow_effect") or "")
        if final_action not in {"", "answer_only", "no_commit"} or mutation_intent != "no_mutation" or workflow_effect != "answer_only":
            raise RuntimeError(
                "founder live manager contract query-only mismatch: answer_query requires "
                "final_action='answer_only' or no commit, workflow_effect='answer_only', and "
                "mutation_intent_candidate='no_mutation'"
            )
    mutation_intent = str(semantic_decision.get("mutation_intent_candidate") or "")
    workflow_effect = str(payload.get("workflow_effect") or semantic_decision.get("workflow_effect") or "")
    estimation_posture = str(semantic_decision.get("estimation_posture") or "")
    if (
        str(payload.get("manager_action") or "") == "call_tools"
        and workflow_effect == "ask_followup"
        and mutation_intent == "no_mutation"
        and "composition_unknown" in estimation_posture
    ):
        tool_calls = payload.get("tool_calls")
        if isinstance(tool_calls, list) and any(
            isinstance(item, dict) and str(item.get("name") or item.get("tool_name") or "") == "estimate_nutrition"
            for item in tool_calls
        ):
            raise RuntimeError(
                "founder live manager contract composition-unknown ask_followup/no_mutation "
                "must not call estimate_nutrition before components are known"
            )
    if semantic_intent == "correct_meal" and str(payload.get("manager_action") or "") == "final":
        if final_action in {"commit", "complete_onboarding"} or mutation_intent == "canonical_write":
            raise RuntimeError(
                "founder live manager contract correct_meal requires correction_applied/correction_write, "
                "not a new canonical commit"
            )
    if final_action == "no_commit" and mutation_intent in {"canonical_write", "correction_write"}:
        raise RuntimeError(
            "founder live manager contract mutation intent mismatch: "
            f"semantic_decision.mutation_intent_candidate={mutation_intent!r} cannot pair with final_action='no_commit'"
        )
    followup_posture = str(semantic_decision.get("followup_posture") or "")
    if (
        str(payload.get("manager_action") or "") == "final"
        and semantic_intent == "log_meal"
        and mutation_intent == "canonical_write"
        and (final_action in {"", "commit"} or final_action_candidate == "commit")
        and followup_posture in FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES
    ):
        answer_contract = payload.get("answer_contract")
        answer_followup = (
            str(answer_contract.get("followup_question") or "").strip()
            if isinstance(answer_contract, dict)
            else ""
        )
        semantic_followup = str(semantic_decision.get("followup_question") or "").strip()
        if not (answer_followup or semantic_followup):
            raise RuntimeError(
                "founder live manager contract followup question missing: "
                f"semantic_decision.followup_posture={followup_posture!r} requires followup_question"
            )


__all__ = [
    "FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID",
    "FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS",
    "FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES",
    "FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES",
    "FOUNDER_LIVE_MANAGER_CONTRACT_POLICY",
    "FOUNDER_LIVE_MANAGER_CONTRACT_POLICY_SUMMARY",
    "FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES",
    "FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION",
    "FOUNDER_LIVE_MANAGER_FOLLOWUP_INSTRUCTION",
    "FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT",
    "FOUNDER_LIVE_MANAGER_COMMIT_WITHOUT_EVIDENCE_REPAIR_FAMILY",
    "FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS",
    "FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES",
    "FOUNDER_LIVE_MANAGER_REPAIR_REQUIRED_TOOL_BY_FAMILY",
    "FOUNDER_LIVE_MANAGER_SCHEMA_NAME",
    "FOUNDER_LIVE_MANAGER_SCHEMA_VERSION",
    "FOUNDER_LIVE_MANAGER_TOOL_NAME",
    "FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY",
    "founder_live_manager_contract_constraints",
    "founder_live_manager_repair_failure_family",
    "founder_live_manager_tool_description",
    "is_founder_live_manager_contract",
    "validate_founder_live_manager_contract_consistency",
]
