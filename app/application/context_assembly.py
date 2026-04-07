from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from ..domain import CanonicalMealState, ConversationState, PlannerContextPayload
from ..schemas import PlanningBrief
from ..schemas import ContextPackTrace, DecisionPassResult, NutritionResolutionResult, TaskMealLinkResult, TurnState


def _compact_chunk(chunk: Any) -> dict[str, Any]:
    return {
        "chunk_id": str(getattr(chunk, "chunk_id", "")),
        "source_type": str(getattr(chunk, "source_type", "")),
        "content": str(getattr(chunk, "content", "")),
        "linked_meal_id": getattr(chunk, "linked_meal_id", None),
        "score": getattr(chunk, "score", 0.0),
    }


def _compact_open_meal(chunk: Any) -> dict[str, Any]:
    metadata = getattr(chunk, "metadata", {}) or {}
    return {
        "meal_id": getattr(chunk, "source_id", None),
        "title": str(metadata.get("title") or metadata.get("meal_title") or ""),
        "status": str(metadata.get("status") or ""),
        "linked_meal_id": getattr(chunk, "linked_meal_id", None),
    }


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def canonicalize_lookup_text(text: str) -> str:
    normalized = normalize_text(text).lower()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def lookup_key(text: str) -> str:
    return "".join(re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", canonicalize_lookup_text(text)))


def lookup_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", canonicalize_lookup_text(text)) if len(token) > 1]


_PORTION_CLUE_PATTERNS = (
    "小杯",
    "中杯",
    "大杯",
    "特大杯",
    "超大杯",
    "tall",
    "grande",
    "venti",
)

_DRINK_LIKE_TOKENS = (
    "那堤",
    "拿鐵",
    "latte",
    "咖啡",
    "奶茶",
    "紅茶",
    "綠茶",
    "茶",
    "奶",
)


def extract_portion_clues(text: str) -> list[str]:
    normalized = normalize_text(text).lower()
    matched: list[str] = []
    for pattern in _PORTION_CLUE_PATTERNS:
        if pattern.lower() in normalized:
            matched.append(pattern)
    return matched


def extract_drink_customization_clues(text: str) -> list[str]:
    normalized = normalize_text(text).lower()
    patterns = (
        "全糖",
        "半糖",
        "微糖",
        "少糖",
        "無糖",
        "去冰",
        "少冰",
        "微冰",
        "正常冰",
        "熱",
        "溫",
        "鮮奶",
        "奶精",
        "加珍珠",
        "珍珠",
    )
    matched: list[str] = []
    for pattern in patterns:
        if pattern.lower() in normalized:
            matched.append(pattern)
    return matched


def looks_like_standardized_drink(text: str, evidence_items: list[dict[str, Any]] | None = None) -> bool:
    haystacks = [normalize_text(text).lower()]
    for item in evidence_items or []:
        haystacks.append(normalize_text(str(item.get("title") or "")).lower())
        haystacks.extend(normalize_text(str(alias)).lower() for alias in item.get("aliases", []) if str(alias).strip())
    combined = " ".join(haystacks)
    return any(token.lower() in combined for token in _DRINK_LIKE_TOKENS)


def _brand_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", normalize_text(text).lower()) if len(token) > 1]


def _candidate_brand_matches_input(user_input: str, brand: str) -> bool:
    input_lower = normalize_text(user_input).lower()
    return any(token in input_lower for token in _brand_tokens(brand))


def should_treat_exact_candidates_as_generic_drink_refs(
    *,
    user_input: str,
    standardized_drink_like: bool,
    portion_clues: list[str],
    exact_candidates: list[dict[str, Any]],
) -> bool:
    if not standardized_drink_like or portion_clues or not exact_candidates:
        return False
    candidate_brands = [str(item.get("brand") or "").strip() for item in exact_candidates if str(item.get("brand") or "").strip()]
    if not candidate_brands:
        return False
    if any(_candidate_brand_matches_input(user_input, brand) for brand in candidate_brands):
        return False
    return True


def filter_generic_drink_packaged_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in items:
        evidence_role = str(item.get("evidence_role") or item.get("record_role") or "")
        source_class = str(item.get("source_class") or item.get("source_type") or "")
        if evidence_role == "exact_truth" and source_class == "exact_item_db":
            continue
        filtered.append(item)
    return filtered


def normalize_user_input_for_estimation(text: str) -> dict[str, Any]:
    raw = normalize_text(text)
    return {
        "raw_text": raw,
        "normalized_text": raw,
        "normalizer_applied": False,
        "notes": ["normalization_patches_removed", "raw_signal_preserved"],
    }


def normalized_input_from_debug_steps(debug_steps: list[dict[str, Any]]) -> str | None:
    for step in debug_steps:
        if step.get("step") != "planner_pass":
            continue
        value = normalize_text(str(step.get("normalized_user_input", "")))
        if value:
            return value
    return None


def estimate_token_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return max(1, len(value) // 4)
    return max(1, len(json.dumps(value, ensure_ascii=False)) // 4)


def knowledge_context(snippets: list[dict[str, Any]]) -> str:
    if not snippets:
        return "- No supporting evidence was retrieved."
    lines: list[str] = []
    for item in snippets[:5]:
        title = str(item.get("title") or item.get("name") or "")
        source = str(item.get("source_type") or item.get("source_class") or "unknown")
        note = str(item.get("snippet") or item.get("summary") or item.get("note") or "").strip()
        line = f"- [{source}] {title}"
        if note:
            line += f": {note}"
        lines.append(line)
    return "\n".join(lines)


def risk_context(packet: dict[str, Any]) -> str:
    lines: list[str] = []
    if packet.get("risk_flags"):
        lines.append(f"- risk_flags: {', '.join(str(item) for item in packet['risk_flags'])}")
    for item in packet.get("review_focus", []):
        lines.append(f"- review_focus: {item}")
    for item in packet.get("must_ask_if_uncertain", []):
        lines.append(f"- must_ask_if_uncertain: {item}")
    for item in packet.get("portion_clues", {}).get("review_focus", []):
        lines.append(f"- portion_review_focus: {item}")
    return "\n".join(lines) if lines else "- no additional risk context"


def calibration_context(packet: dict[str, Any]) -> str:
    """Format calibration packet for LLM context in system prompt."""
    if not packet:
        return "- No specific calibration context for this dish type."
    lines = []
    title = packet.get("title", "")
    if title:
        lines.append(f"[{title}]")
    bias_notes = packet.get("bias_notes", [])
    if bias_notes:
        for note in bias_notes:
            lines.append(f"- 注意: {note}")
    high_calorie = packet.get("high_calorie_sources", [])
    if high_calorie:
        lines.append(f"- 高熱量來源: {', '.join(str(item) for item in high_calorie)}")
    adjustment = packet.get("typical_adjustment_range", {})
    if adjustment:
        low = adjustment.get("kcal_delta_low", "")
        high = adjustment.get("kcal_delta_high", "")
        if low and high:
            lines.append(f"- 典型調整範圍: +{low} ~ +{high} kcal")
    return "\n".join(lines) if lines else "- No specific calibration context for this dish type."


def build_dynamic_system_addition(*, selected_evidence_summary: list[dict[str, Any]], risk_packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_evidence_summary": selected_evidence_summary,
        "risk_flags": risk_packet.get("risk_flags", []),
        "required_checks": risk_packet.get("required_checks", {}),
    }


def build_turn_state(state: ConversationState) -> TurnState:
    candidate_components = [comp.get("name", "") for comp in state.latest_components if comp.get("name")]
    return TurnState(
        active_meal_log_id=state.latest_log_id,
        pending_question=state.pending_question,
        last_estimate_mode=None,
        candidate_components=candidate_components,
        allowed_next_intents=["clarification", "modification", "new_intake", "general_chat"],
    )


def render_conversation_state_prompt(state: ConversationState) -> str:
    turn_state = build_turn_state(state)
    state_json = turn_state.model_dump(mode="json")
    parts: list[str] = [f"[Current TurnState]\n{json.dumps(state_json, ensure_ascii=False, indent=2)}"]
    if state.planner_state_digest:
        parts.append("[Planner State Digest]\n" + json.dumps(state.planner_state_digest.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.active_meal_summary:
        parts.append("[Active Meal Summary]\n" + json.dumps(state.active_meal_summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.session_summary:
        parts.append("[Session Summary]\n" + json.dumps(state.session_summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.durable_memory_hits:
        parts.append("[Durable Memory Hits]\n" + json.dumps([hit.model_dump(mode="json") for hit in state.durable_memory_hits], ensure_ascii=False, indent=2))
    if state.recent_messages:
        lines = []
        for msg in list(state.recent_messages)[-5:]:
            prefix = "USER" if msg.role == "user" else "ASSISTANT"
            lines.append(f"[{prefix}] {msg.content}")
        parts.append("[Recent Conversation Context]\n" + "\n".join(lines))
    if state.conversation_archive_hits:
        hit_lines = []
        for hit in state.conversation_archive_hits[:4]:
            prefix = "USER" if hit.role == "user" else "ASSISTANT"
            hit_lines.append(f"[{prefix}#{hit.message_id}] {hit.content}")
        parts.append("[Retrieved Conversation Hits]\n" + "\n".join(hit_lines))
    if state.retrieved_meal_records:
        meal_lines = []
        for chunk in state.retrieved_meal_records[:3]:
            meal_lines.append(f"[MEAL#{chunk.source_id}] {chunk.metadata.get('title', '')} :: {chunk.content[:240]}")
        parts.append("[Retrieved Meal Records]\n" + "\n".join(meal_lines))
    return "\n\n".join(parts)


def build_planner_context_payload(
    *,
    raw_user_input: str,
    thin_sanitized_input: str,
    allow_search: bool,
    state: ConversationState,
) -> PlannerContextPayload:
    return PlannerContextPayload(
        raw_user_input=raw_user_input,
        thin_sanitized_input=thin_sanitized_input,
        allow_search=allow_search,
        pending_question=state.pending_question,
        latest_meal_summary=state.latest_meal_title,
        conversation_state_summary={
            "latest_log_id": state.latest_log_id,
            "latest_log_status": state.latest_log_status,
            "latest_meal_title": state.latest_meal_title,
            "latest_components": state.latest_components,
            "pending_question": state.pending_question,
            "active_parent_log_id": state.active_parent_log_id,
            "recent_message_count": len(state.recent_messages),
            "conversation_window_size": state.conversation_window_size,
            "conversation_archive_count": state.conversation_archive_count,
            "conversation_archive_hit_count": len(state.conversation_archive_hits),
            "is_multi_turn_candidate": state.is_multi_turn_candidate,
            "boundary_clarification_open": state.boundary_clarification_open,
            "boundary_clarification_source_meal_id": state.boundary_clarification_source_meal_id,
        },
        planner_state_digest=state.planner_state_digest.model_dump(mode="json"),
        retrieved_transcript_chunks=[chunk.model_dump(mode="json") for chunk in state.retrieved_transcript_chunks],
        retrieved_meal_records=[chunk.model_dump(mode="json") for chunk in state.retrieved_meal_records],
        active_meal_summary=state.active_meal_summary.model_dump(mode="json"),
        session_summary=state.session_summary.model_dump(mode="json"),
        durable_memory_hits=[hit.model_dump(mode="json") for hit in state.durable_memory_hits],
        active_meal_state={
            "active_meal_id": state.latest_log_id,
            "active_meal_status": state.latest_log_status,
            "active_meal_title": state.latest_meal_title,
            "pending_question": state.pending_question,
        },
        time_distance_features={"active_meal_time_gap_seconds": state.active_meal_time_gap_seconds},
        boundary_state={
            "boundary_clarification_open": state.boundary_clarification_open,
            "boundary_clarification_source_meal_id": state.boundary_clarification_source_meal_id,
        },
        retrieved_conversation_context=[hit.model_dump(mode="json") for hit in state.conversation_archive_hits],
    )


def build_boundary_features(*, state: ConversationState, latest_log: Any | None) -> dict[str, Any]:
    return {
        "time_gap_seconds": int(state.active_meal_time_gap_seconds or 0),
        "pending_question_present": bool(
            (getattr(latest_log, "pending_question", None) if latest_log is not None else None)
            or state.pending_question
            or state.planner_state_digest.pending_question
        ),
        "active_meal_exists": bool(latest_log or state.active_meal_summary.meal_title),
        "active_meal_status": str(getattr(latest_log, "status", "") or ""),
        "transcript_link_hit_count": len([chunk for chunk in state.retrieved_transcript_chunks if str(chunk.linked_meal_id or "").strip()]),
        "meal_record_hit_count": len(state.retrieved_meal_records),
    }


def build_task_meal_link_payload(
    *,
    user_input: str,
    state: ConversationState,
    meal_log_summaries: list[dict[str, Any]],
    boundary_features: dict[str, Any],
) -> dict[str, Any]:
    return {
        "current_user_input": user_input,
        "recent_transcript": [_compact_chunk(chunk) for chunk in state.retrieved_transcript_chunks[:4]],
        "open_unresolved_meals": [
            _compact_open_meal(meal)
            for meal in state.retrieved_meal_records
            if str(getattr(meal, "status", "") or "") == "draft_unresolved"
        ][:3],
        "meal_log_summaries": meal_log_summaries[:5],
        "boundary_features": boundary_features,
        "active_meal_summary": state.active_meal_summary.model_dump(mode="json"),
        "linking_policy": {
            "prefer_create_new_meal_for_complete_intake": True,
            "attach_only_for_clear_continuation_or_pending_question_answer": True,
            "older_unresolved_meals_are_context_not_override": True,
        },
    }


def build_decision_payload(
    *,
    user_input: str,
    meal_state: CanonicalMealState | None,
    meal_link_result: TaskMealLinkResult,
    selected_evidence_summary: list[dict[str, Any]],
    available_tools: list[str],
    planning_brief: PlanningBrief | None = None,
) -> dict[str, Any]:
    portion_clues = extract_portion_clues(user_input)
    standardized_drink_like = looks_like_standardized_drink(user_input, selected_evidence_summary)
    drink_customization_clues = extract_drink_customization_clues(user_input) if standardized_drink_like else []
    exact_truth_candidates = []
    for item in selected_evidence_summary:
        if str(item.get("evidence_role") or "") != "exact_truth":
            continue
        exact_truth_candidates.append(
            {
                "title": str(item.get("title") or ""),
                "brand": str(item.get("brand") or ""),
                "source_class": str(item.get("source_class") or ""),
                "identity_confidence": str(item.get("identity_confidence") or "none"),
                "serving_basis": str(item.get("serving_basis") or ""),
                "kcal": item.get("kcal"),
                "match_path": str(item.get("match_path") or ""),
                "aliases": [str(alias) for alias in item.get("aliases", []) if str(alias).strip()][:5],
            }
        )
    generic_drink_packaged_refs = should_treat_exact_candidates_as_generic_drink_refs(
        user_input=user_input,
        standardized_drink_like=standardized_drink_like,
        portion_clues=portion_clues,
        exact_candidates=exact_truth_candidates,
    )
    if generic_drink_packaged_refs:
        exact_truth_candidates = []
    exact_title_match_present = any(
        str(item.get("match_path") or "") in {"exact_title", "exact_alias"}
        for item in exact_truth_candidates
    )
    scoped_meal_state = (
        meal_state.model_dump(mode="json")
        if meal_state and meal_link_result.meal_link_action == "attach_to_existing_meal"
        else {}
    )
    selected_evidence_payload = (
        filter_generic_drink_packaged_evidence(selected_evidence_summary)
        if generic_drink_packaged_refs
        else selected_evidence_summary
    )
    return {
        "current_user_input": user_input,
        "portion_clues": portion_clues,
        "drink_customization_clues": drink_customization_clues,
        "standardized_drink_like": standardized_drink_like,
        "size_missing_for_standardized_drink": standardized_drink_like and not portion_clues,
        "generic_drink_customization_present": standardized_drink_like and bool(drink_customization_clues) and not portion_clues,
        "exact_title_match_present": exact_title_match_present,
        "single_exact_candidate_present": len(exact_truth_candidates) == 1,
        "generic_drink_packaged_refs": generic_drink_packaged_refs,
        "canonical_meal_state": scoped_meal_state,
        "meal_link_result": meal_link_result.model_dump(mode="json"),
        "selected_evidence_summary": selected_evidence_payload,
        "exact_truth_available": bool(exact_truth_candidates),
        "exact_truth_candidates": exact_truth_candidates[:5],
        "available_tools": available_tools,
        "planning_brief": planning_brief.model_dump(mode="json") if planning_brief else {},
        "slot_state": planning_brief.slot_state if planning_brief else None,
    }


def build_nutrition_resolution_payload(
    *,
    meal_state: CanonicalMealState | None,
    meal_link_result: TaskMealLinkResult,
    decision_result: DecisionPassResult,
    normalized_evidence: list[dict[str, Any]],
    calibration_packet: dict[str, Any] | None,
    user_input: str,
    partial_grounding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    portion_clues = extract_portion_clues(user_input)
    standardized_drink_like = looks_like_standardized_drink(user_input, [dict(item.get("raw") or {}) for item in normalized_evidence])
    drink_customization_clues = extract_drink_customization_clues(user_input) if standardized_drink_like else []
    exact_truth_candidates = []
    for item in normalized_evidence:
        raw = dict(item.get("raw") or {})
        if str(raw.get("evidence_role") or "") != "exact_truth":
            continue
        exact_truth_candidates.append(
            {
                "title": str(raw.get("title") or ""),
                "brand": str(raw.get("brand") or ""),
                "kcal": raw.get("label_kcal") or raw.get("kcal"),
                "label_macros": raw.get("label_macros") or raw.get("macros") or {},
                "match_quality": str(
                    raw.get("match_confidence")
                    or raw.get("identity_confidence")
                    or item.get("match_quality")
                    or "unknown"
                ),
                "match_path": str(raw.get("match_path") or ""),
                "source_class": str(raw.get("source_class") or raw.get("source_type") or ""),
                "portion_basis_quality": str(raw.get("portion_basis_quality") or ""),
                "serving_basis": str(raw.get("serving_basis") or raw.get("portion_basis") or raw.get("serving_size") or ""),
                "aliases": [str(alias) for alias in raw.get("aliases", []) if str(alias).strip()][:5],
            }
        )
    generic_drink_packaged_refs = should_treat_exact_candidates_as_generic_drink_refs(
        user_input=user_input,
        standardized_drink_like=standardized_drink_like,
        portion_clues=portion_clues,
        exact_candidates=exact_truth_candidates,
    )
    if generic_drink_packaged_refs:
        exact_truth_candidates = []
    exact_title_match_present = any(
        str(item.get("match_path") or "") in {"exact_title", "exact_alias"}
        for item in exact_truth_candidates
    )
    scoped_meal_state = (
        meal_state.model_dump(mode="json")
        if meal_state and meal_link_result.meal_link_action == "attach_to_existing_meal"
        else {}
    )
    normalized_evidence_payload = (
        [
            item
            for item in normalized_evidence
            if str(dict(item.get("raw") or {}).get("evidence_role") or "") != "exact_truth"
            or str(dict(item.get("raw") or {}).get("source_class") or dict(item.get("raw") or {}).get("source_type") or "") != "exact_item_db"
        ]
        if generic_drink_packaged_refs
        else normalized_evidence
    )
    return {
        "current_user_input": user_input,
        "portion_clues": portion_clues,
        "drink_customization_clues": drink_customization_clues,
        "standardized_drink_like": standardized_drink_like,
        "size_missing_for_standardized_drink": standardized_drink_like and not portion_clues,
        "generic_drink_customization_present": standardized_drink_like and bool(drink_customization_clues) and not portion_clues,
        "exact_title_match_present": exact_title_match_present,
        "single_exact_candidate_present": len(exact_truth_candidates) == 1,
        "generic_drink_packaged_refs": generic_drink_packaged_refs,
        "canonical_meal_state": scoped_meal_state,
        "meal_link_result": meal_link_result.model_dump(mode="json"),
        "decision_result": decision_result.model_dump(mode="json"),
        "normalized_evidence": normalized_evidence_payload,
        "exact_truth_available": bool(exact_truth_candidates),
        "exact_truth_candidates": exact_truth_candidates[:5],
        "calibration_packet": calibration_packet or {},
        "partial_grounding": partial_grounding or {},
        "active_unresolved_meal_id": (
            meal_state.meal_id
            if meal_state
            and meal_link_result.meal_link_action == "attach_to_existing_meal"
            and meal_state.status != "completed_meal"
            else None
        ),
    }


def build_four_pass_final_response_payload(
    *,
    user_input: str,
    task_meal_link_result: TaskMealLinkResult,
    decision_result: DecisionPassResult,
    nutrition_result: NutritionResolutionResult,
    active_meal_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "user_input": user_input,
        "task_meal_link_result": task_meal_link_result.model_dump(mode="json"),
        "decision_result": decision_result.model_dump(mode="json"),
        "nutrition_result": nutrition_result.model_dump(mode="json"),
        "active_meal_summary": active_meal_summary,
    }


def build_context_pack_trace(
    *,
    state: ConversationState,
    evidence_bundle: dict[str, Any],
    available_tools: list[str],
    evidence_guardrail_prompt: str,
) -> ContextPackTrace:
    sections = [
        {"name": "evidence_guardrail_prompt", "estimated_tokens": estimate_token_count(evidence_guardrail_prompt)},
        {"name": "session_summary", "estimated_tokens": estimate_token_count(state.session_summary.model_dump(mode="json"))},
        {"name": "active_meal_summary", "estimated_tokens": estimate_token_count(state.active_meal_summary.model_dump(mode="json"))},
        {"name": "recent_turn_summary", "estimated_tokens": estimate_token_count(state.recent_turn_summary.model_dump(mode="json"))},
        {"name": "retrieved_transcript_chunks", "estimated_tokens": estimate_token_count([chunk.model_dump(mode="json") for chunk in state.retrieved_transcript_chunks])},
        {"name": "retrieved_meal_records", "estimated_tokens": estimate_token_count([chunk.model_dump(mode="json") for chunk in state.retrieved_meal_records])},
        {"name": "retrieval_diagnostics", "estimated_tokens": estimate_token_count(state.retrieval_diagnostics)},
        {"name": "durable_memory_hits", "estimated_tokens": estimate_token_count([hit.model_dump(mode="json") for hit in state.durable_memory_hits])},
        {"name": "evidence_bundle", "estimated_tokens": estimate_token_count(evidence_bundle)},
        {"name": "available_tools", "estimated_tokens": estimate_token_count(available_tools)},
    ]
    return ContextPackTrace(
        sections=sections,
        total_estimated_tokens=sum(int(section["estimated_tokens"]) for section in sections),
    )
