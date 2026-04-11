from __future__ import annotations

from typing import Any

from ..application.context_assembly import build_four_pass_final_response_payload
from ..application.pass_runner import run_pass
from ..schemas import FinalResponseResult


FINAL_RESPONSE_PROMPT = """You are the final response layer for a food estimation assistant.

## Your Goal
Write a response that feels like a knowledgeable friend helping you track calories — not a nutrition calculator.

## Rules

1. **Lead with the number**: Start with the calorie estimate (e.g., "約 720 kcal")
2. **Keep it conversational**: Use 1-2 short sentences, not bullet lists
3. **Add one brief note** on what contributes most (optional, only if helpful)
4. **Only mention macros if requested or relevant** (skip unless the user asked)
5. **Skip uncertainty discussion** unless the range is unusually wide (>200 kcal)
6. **One follow-up question MAX** — only if the missing info would significantly improve estimate

## Upstream Contract
- Treat `decision_result` and `nutrition_result` as the source of truth for whether the system is still clarifying.
- If `decision_result.next_action` is `run_nutrition_resolution` and `nutrition_result.resolution_mode` is `exact_label_finalize` or `near_exact_finalize`, the answer is already finalized.
- In that finalized exact or near-exact case, do not add a new follow-up just because `nutrition_result.unresolved_info` contains a low-priority refinement note.
- If `nutrition_result.confidence` is `high` and the estimate is exact or near-exact, reply with the answer rather than a question.
- If `nutrition_result.estimate_mode` is `anchored_component` or `llm_only`, default to replying with the estimate instead of inventing a new follow-up.
- If the upstream nutrition result already gave a useful estimate for a branded ramen or tea-shop drink, do not add a new question unless the upstream result explicitly marked clarification as blocking.
- If `nutrition_result.resolution_mode` is `cannot_estimate_yet`, treat that as a typed abstain/no-canonical-write lane: ask one short follow-up and do not claim a calorie estimate.

### When to Follow-up
- Only ask if: portion size varies dramatically AND user can easily clarify
- Example good: "雞排比一般大 or 小？"
- Example bad: "請再描述更具體的食物名稱、份量或配料"

### When NOT to Follow-up
- The estimate is already reasonable (~±150 kcal)
- The dish is single-component (just rice, just bread)
- The user didn't ask for help estimating
- Generic customized drinks like `珍珠奶茶半糖去冰` already have a useful class-level estimate; do not ask about cup size unless the upstream result explicitly marked clarification as blocking.

## Output Format

Return JSON with:
- reply_text: your conversational response
- asked_follow_up: true only if truly needed
- ui_hints: {} (leave empty unless special UI needed)

## Important
- Do not introduce new information not provided upstream
- Never say "0 kcal" or "0g" as a final answer
- For recognizable dishes with kcal > 0, a simple number is better than nothing
"""


def fallback_final_response_result(
    *,
    user_input: str,
    primary_result: dict[str, Any],
) -> FinalResponseResult:
    answer_payload = dict(primary_result.get("answer_payload") or {})
    title = str(answer_payload.get("title") or user_input).strip() or user_input
    estimated_kcal = int(answer_payload.get("estimated_kcal") or 0)
    unresolved = [str(item) for item in primary_result.get("unresolved_info") or [] if str(item).strip()]
    if unresolved and primary_result.get("response_mode_hint") == "clarify_first":
        return FinalResponseResult(
            reply_text="請再描述更具體的食物名稱、份量或配料。",
            asked_follow_up=True,
            ui_hints={},
        )
    if estimated_kcal > 0:
        return FinalResponseResult(
            reply_text=f"{title} 我先抓約 {estimated_kcal} kcal。",
            asked_follow_up=False,
            ui_hints={},
        )
    return FinalResponseResult(
        reply_text="請再描述更具體的食物名稱、份量或配料。",
        asked_follow_up=bool(unresolved),
        ui_hints={},
    )


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no", ""}:
            return False
        return True
    return bool(value)


def _coerce_ui_hints(value: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    if isinstance(value, str) and value.strip():
        return {"note": value.strip()}
    return dict(fallback)


def normalize_final_response_result(raw: dict[str, Any], fallback: FinalResponseResult) -> FinalResponseResult:
    if not raw:
        return fallback
    reply_text = str(raw.get("reply_text") or "").strip() or fallback.reply_text
    asked_value = raw.get("asked_follow_up", fallback.asked_follow_up)
    if isinstance(asked_value, str) and "reply_text" not in raw:
        reply_text = asked_value.strip() or reply_text
        asked_follow_up = True
    else:
        asked_follow_up = _coerce_bool(asked_value, fallback.asked_follow_up)
    return FinalResponseResult(
        reply_text=reply_text,
        asked_follow_up=asked_follow_up,
        ui_hints=_coerce_ui_hints(raw.get("ui_hints"), fallback.ui_hints),
    )


def sanitize_final_response_result(
    *,
    result: FinalResponseResult,
    nutrition_result: Any,
    fallback: FinalResponseResult,
) -> FinalResponseResult:
    resolution_mode = str(getattr(nutrition_result, "resolution_mode", "") or "")
    answer_payload = dict(getattr(nutrition_result, "answer_payload", {}) or {})
    estimated_kcal = int(answer_payload.get("estimated_kcal") or 0)
    protein_g = int(answer_payload.get("protein_g") or 0)
    carb_g = int(answer_payload.get("carb_g") or 0)
    fat_g = int(answer_payload.get("fat_g") or 0)
    reply_text = str(result.reply_text or "").strip()
    zero_markers = ["0 kcal", "0g", "0 大卡"]
    if resolution_mode == "cannot_estimate_yet" and any(token in reply_text for token in zero_markers):
        return fallback
    if estimated_kcal <= 0 and any(token in reply_text for token in zero_markers):
        return fallback
    if resolution_mode in {"component_estimate", "provisional_estimate"} and estimated_kcal <= 0:
        return fallback
    if estimated_kcal <= 0 and (protein_g > 0 or carb_g > 0 or fat_g > 0):
        return fallback
    return result


async def run_four_pass_final_response(
    *,
    provider: Any,
    request_id: str,
    user_input: str,
    task_meal_link_result: Any,
    decision_result: Any,
    nutrition_result: Any,
    active_meal_summary: dict[str, Any],
    llm_traces: list[dict[str, Any]],
    max_tokens: int,
    run_stage: Any,
) -> FinalResponseResult:
    payload = build_four_pass_final_response_payload(
        user_input=user_input,
        task_meal_link_result=task_meal_link_result,
        decision_result=decision_result,
        nutrition_result=nutrition_result,
        active_meal_summary=active_meal_summary,
    )
    fallback = fallback_final_response_result(
        user_input=user_input,
        primary_result={
            "answer_payload": dict(getattr(nutrition_result, "answer_payload", {}) or {}),
            "unresolved_info": list(getattr(nutrition_result, "unresolved_info", []) or []),
            "response_mode_hint": "clarify_first"
            if str(getattr(nutrition_result, "resolution_mode", "")) == "cannot_estimate_yet"
            else "rough_estimate_ok",
        },
    )
    final_result, _ = await run_pass(
        provider=provider,
        stage="final_response_pass",
        system_prompt=FINAL_RESPONSE_PROMPT,
        user_payload=payload,
        max_tokens=max_tokens,
        fallback_result=fallback,
        normalize=normalize_final_response_result,
        dump=lambda result: result.model_dump(mode="json"),
        run_stage=run_stage,
        request_id=request_id,
        llm_traces=llm_traces,
        trigger_reason="final_response_four_pass",
        handoff_contract={
            "meal_link_action": getattr(task_meal_link_result, "meal_link_action", ""),
            "next_action": getattr(decision_result, "next_action", ""),
            "resolution_mode": getattr(nutrition_result, "resolution_mode", ""),
        },
        required_fields=["reply_text", "asked_follow_up"],
        required_fields_source="normalized",
    )
    return sanitize_final_response_result(
        result=final_result,
        nutrition_result=nutrition_result,
        fallback=fallback,
    )
