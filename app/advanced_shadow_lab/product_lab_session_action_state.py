from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_action_state import (
    empty_product_lab_action_state,
    reduce_product_lab_action_state,
)
from app.advanced_shadow_lab.product_lab_chat_actions import (
    apply_product_lab_chat_actions,
)


def initial_session_action_state() -> dict[str, Any]:
    return empty_product_lab_action_state()


def post_turn_action_state(
    *,
    prior_state: Mapping[str, Any],
    chat_action_outcomes: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    return reduce_product_lab_action_state(
        prior_state=prior_state,
        action_outcomes=chat_action_outcomes,
    )


def post_turn_chat_actions_and_state(
    *,
    turn_spec: Mapping[str, Any],
    turn_artifact: Mapping[str, Any],
    prior_state: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[str]]:
    action_outcomes = apply_product_lab_chat_actions(
        messages=_chat_messages(turn_artifact),
        action_specs=_post_turn_chat_actions(turn_spec),
    )
    action_state, action_state_delta = post_turn_action_state(
        prior_state=prior_state,
        chat_action_outcomes=action_outcomes,
    )
    blockers = [
        str(blocker)
        for outcome in action_outcomes
        for blocker in outcome.get("blockers") or []
    ]
    return action_outcomes, action_state, action_state_delta, blockers


def _post_turn_chat_actions(turn_spec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in turn_spec.get("post_turn_chat_actions") or []
        if isinstance(item, Mapping)
    ]


def _chat_messages(turn_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    surface = turn_artifact.get("lab_chat_surface")
    if not isinstance(surface, Mapping):
        return []
    return [
        item for item in surface.get("messages") or [] if isinstance(item, Mapping)
    ]


__all__ = [
    "initial_session_action_state",
    "post_turn_chat_actions_and_state",
    "post_turn_action_state",
]
