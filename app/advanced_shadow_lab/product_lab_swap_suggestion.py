from __future__ import annotations

from typing import Any, Mapping


def swap_suggestion_context(
    *,
    turn: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if turn.get("turn_mode") != "swap_suggestion":
        return {}
    source = _mapping(payload.get("swap_suggestion_context"))
    history_sufficient = source.get("history_sufficient") is True
    return {
        "mode": "swap_suggestion",
        "trigger_source": str(source.get("trigger_source") or ""),
        "history_sufficient": history_sufficient,
        "original_item_name": str(source.get("original_item_name") or ""),
        "original_kcal": _int(source.get("original_kcal")),
        "suggested_item_name": str(source.get("suggested_item_name") or ""),
        "suggested_kcal": _int(source.get("suggested_kcal")),
        "weekly_frequency_estimate": _int_or_none(
            source.get("weekly_frequency_estimate")
        ),
        "suggestion_basis": str(source.get("suggestion_basis") or ""),
        "source_refs": [str(ref) for ref in source.get("source_refs") or []],
    }


def swap_suggestion_packet(
    *,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    if context.get("mode") != "swap_suggestion":
        return {}
    if context.get("history_sufficient") is not True:
        return {}
    original_kcal = _int(context.get("original_kcal"))
    suggested_kcal = _int(context.get("suggested_kcal"))
    saving = max(original_kcal - suggested_kcal, 0)
    frequency = _int_or_none(context.get("weekly_frequency_estimate"))
    return {
        "mode": "swap_suggestion",
        "original_item_name": str(context.get("original_item_name") or ""),
        "original_kcal": original_kcal,
        "suggested_item_name": str(context.get("suggested_item_name") or ""),
        "suggested_kcal": suggested_kcal,
        "kcal_saving_per_instance": saving,
        "weekly_saving_estimate": saving * frequency if frequency else None,
        "suggestion_basis": str(context.get("suggestion_basis") or ""),
        "source_refs": [str(ref) for ref in context.get("source_refs") or []],
        "canonical_commit_requested": False,
        "durable_product_memory_written": False,
    }


def swap_suggestion_copy(packet: Mapping[str, Any]) -> str:
    if not packet:
        return ""
    weekly = packet.get("weekly_saving_estimate")
    weekly_text = f"; about {weekly} kcal/week" if isinstance(weekly, int) else ""
    return (
        f"Swap {packet.get('original_item_name')} to "
        f"{packet.get('suggested_item_name')} to save "
        f"{packet.get('kcal_saving_per_instance')} kcal{weekly_text}."
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


__all__ = [
    "swap_suggestion_context",
    "swap_suggestion_copy",
    "swap_suggestion_packet",
]
