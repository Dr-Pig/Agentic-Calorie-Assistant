from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

WorkflowFamily = Literal[
    "intake",
    "rescue",
    "calibration",
    "recommendation",
    "body_observation",
    "general_chat",
]
WorkflowDisposition = Literal[
    "create",
    "continue",
    "correct",
    "accept",
    "reject",
    "defer",
    "adjust",
    "answer_only",
    "open_new_workflow",
]
RoutingConfidence = Literal["high", "medium", "low"]
AmbiguityPosture = Literal["none", "allow_uncertain"]


@dataclass(frozen=True)
class WorkflowRoutingStateHints:
    has_open_rescue_proposal: bool = False
    has_pending_intake_followup: bool = False
    has_active_body_plan: bool = False
    recent_message_summary: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowRoutingResult:
    target_workflow_family: WorkflowFamily
    disposition: WorkflowDisposition
    routing_confidence: RoutingConfidence
    ambiguity_posture: AmbiguityPosture
    reasoning_summary: str
    required_read_surfaces: list[str] = field(default_factory=list)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(token in text for token in keywords)


def _looks_like_remaining_budget_query(text: str) -> bool:
    return _contains_any(
        text,
        ("還能吃多少", "還剩多少", "剩多少", "剩餘熱量", "剩下多少熱量", "目標是多少", "每日目標", "熱量目標"),
    )


def _looks_like_rescue_request(text: str, *, has_open_rescue_proposal: bool) -> tuple[bool, WorkflowDisposition]:
    if has_open_rescue_proposal:
        if _contains_any(text, ("接受", "可以", "好，就這樣", "照這個", "用這個方案")):
            return True, "accept"
        if _contains_any(text, ("先不要", "不要這次", "拒絕", "不用了")):
            return True, "reject"
        if _contains_any(text, ("之後再看", "稍後", "晚點", "先這樣", "等等再說")):
            return True, "defer"
        if _contains_any(text, ("更短", "更積極", "更長", "更緩和", "改一下方案")):
            return True, "adjust"
        if _contains_any(text, ("為什麼", "理由", "怎麼算", "解釋一下")):
            return True, "answer_only"

    if _contains_any(text, ("超標了怎麼辦", "爆卡了怎麼辦", "幫我補救", "怎麼補救", "救一下今天")):
        return True, "open_new_workflow"
    return False, "answer_only"


def _looks_like_recommendation_request(text: str) -> bool:
    return _contains_any(
        text,
        ("推薦", "建議吃", "晚餐吃什麼", "午餐吃什麼", "早餐吃什麼", "幫我推薦", "附近有什麼可吃"),
    )


def _looks_like_body_observation_create(text: str) -> bool:
    return _contains_any(
        text,
        ("我今天", "我剛量", "體重", "公斤", "kg", "脂肪", "體脂"),
    ) and _contains_any(text, ("量", "變成", "現在", "今天", "剛"))


def _looks_like_calibration_request(text: str) -> bool:
    return _contains_any(
        text,
        ("重新調整目標", "重新計算目標", "調整熱量", "校準", "最近都沒變", "幫我調整 body plan", "重新設定計畫"),
    )


def _looks_like_intake_continuation(text: str, *, has_pending_intake_followup: bool) -> bool:
    if not has_pending_intake_followup:
        return False
    return not _contains_any(text, ("推薦", "補救", "校準", "體重", "目標")) and bool(text.strip())


def _looks_like_intake_request(text: str) -> bool:
    return _contains_any(
        text,
        ("我吃了", "我剛吃", "早餐我吃", "午餐我吃", "晚餐我吃", "幫我記", "記一下", "加到今天"),
    )


def build_workflow_routing_decision(
    *,
    raw_user_input: str,
    state_hints: WorkflowRoutingStateHints | None = None,
) -> WorkflowRoutingResult:
    hints = state_hints or WorkflowRoutingStateHints()
    text = raw_user_input.strip()

    if _looks_like_remaining_budget_query(text):
        surfaces = ["CurrentBudgetView"]
        if _contains_any(text, ("目標",)):
            surfaces.append("ActiveBodyPlanView")
        return WorkflowRoutingResult(
            target_workflow_family="general_chat",
            disposition="answer_only",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="budget-or-goal query uses shared read surfaces and should stay in general_chat",
            required_read_surfaces=surfaces,
        )

    rescue_hit, rescue_disposition = _looks_like_rescue_request(
        text,
        has_open_rescue_proposal=hints.has_open_rescue_proposal,
    )
    if rescue_hit:
        return WorkflowRoutingResult(
            target_workflow_family="rescue",
            disposition=rescue_disposition,
            routing_confidence="high" if hints.has_open_rescue_proposal else "medium",
            ambiguity_posture="none",
            reasoning_summary="rescue request or proposal action should route into rescue family",
            required_read_surfaces=[],
        )

    if _looks_like_recommendation_request(text):
        return WorkflowRoutingResult(
            target_workflow_family="recommendation",
            disposition="answer_only",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="meal suggestion request should stay non-mutating in recommendation",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
        )

    if _looks_like_calibration_request(text):
        return WorkflowRoutingResult(
            target_workflow_family="calibration",
            disposition="open_new_workflow",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="explicit plan-adjustment request belongs to calibration family",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
        )

    if _looks_like_body_observation_create(text):
        return WorkflowRoutingResult(
            target_workflow_family="body_observation",
            disposition="create",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="body metric update should route to body_observation create path",
            required_read_surfaces=[],
        )

    if _looks_like_intake_continuation(text, has_pending_intake_followup=hints.has_pending_intake_followup):
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="continue",
            routing_confidence="medium",
            ambiguity_posture="none",
            reasoning_summary="pending intake follow-up is present, so this turn continues intake by default",
            required_read_surfaces=[],
        )

    if _looks_like_intake_request(text):
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="open_new_workflow",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="meal logging request should hand off into intake",
            required_read_surfaces=[],
        )

    return WorkflowRoutingResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        routing_confidence="low",
        ambiguity_posture="allow_uncertain",
        reasoning_summary="no formal workflow signal dominated, so stay in general_chat with ambiguity visible",
        required_read_surfaces=[],
    )
