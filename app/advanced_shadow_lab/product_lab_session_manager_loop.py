from __future__ import annotations

from typing import Any, Mapping


def turn_manager_script(turn_spec: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    if "manager_script" not in turn_spec:
        return None
    return [
        item for item in turn_spec.get("manager_script") or [] if isinstance(item, Mapping)
    ]


def turn_manager_tool_summary(turn_artifact: Mapping[str, Any]) -> dict[str, Any]:
    loop = _mapping(turn_artifact.get("manager_tool_loop_artifact"))
    return {
        "manager_tool_loop_enabled": turn_artifact.get("manager_tool_loop_enabled")
        is True,
        "manager_tool_loop_status": str(loop.get("status") or "not_run"),
        "manager_tool_loop_source_refs": [
            str(ref) for ref in turn_artifact.get("manager_tool_loop_source_refs") or []
        ],
        "manager_tool_loop_blockers": [
            str(blocker) for blocker in loop.get("blockers") or []
        ],
    }


def session_manager_tool_summary(
    turn_summaries: list[Mapping[str, Any]],
) -> dict[str, Any]:
    source_refs = [
        str(ref)
        for turn in turn_summaries
        for ref in turn.get("manager_tool_loop_source_refs") or []
    ]
    blockers = [
        str(blocker)
        for turn in turn_summaries
        for blocker in turn.get("manager_tool_loop_blockers") or []
    ]
    return {
        "manager_tool_loop_turn_count": sum(
            1 for turn in turn_summaries if turn.get("manager_tool_loop_enabled") is True
        ),
        "manager_tool_loop_source_refs": source_refs,
        "manager_tool_loop_blockers": blockers,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "session_manager_tool_summary",
    "turn_manager_script",
    "turn_manager_tool_summary",
]
