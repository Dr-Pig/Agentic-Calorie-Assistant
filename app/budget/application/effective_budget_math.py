from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


_MANUAL_SUBTRACTIVE_ENTRY_TYPES = frozenset({"manual_adjustment"})
_SIGNED_EFFECTIVE_BUDGET_ENTRY_TYPES = frozenset({"calibration_adjustment", "rescue_overlay"})


@dataclass(frozen=True)
class BudgetAdjustmentLayerSummary:
    manual_adjustment_total_kcal: int
    calibration_adjustment_total_kcal: int
    rescue_overlay_total_kcal: int
    known_adjustment_entry_total_kcal: int
    all_adjustment_entry_total_kcal: int
    unclassified_adjustment_total_kcal: int
    signed_effective_budget_delta_kcal: int
    runtime_adjustment_total_kcal: int
    sign_policy: str = "type_aware_signed_layers_to_legacy_subtractive_adjustment"


def _entry_field(entry: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(entry, dict):
        return entry.get(field_name, default)
    return getattr(entry, field_name, default)


def runtime_adjustment_delta_for_entry(*, entry_type: str, delta_kcal: int) -> int:
    normalized_type = str(entry_type or "").strip()
    normalized_delta = int(delta_kcal or 0)
    if normalized_type in _SIGNED_EFFECTIVE_BUDGET_ENTRY_TYPES:
        return -normalized_delta
    return normalized_delta


def effective_budget_delta_for_entry(*, entry_type: str, delta_kcal: int) -> int:
    return -runtime_adjustment_delta_for_entry(entry_type=entry_type, delta_kcal=delta_kcal)


def summarize_budget_adjustment_layers(entries: Iterable[Any]) -> BudgetAdjustmentLayerSummary:
    manual_total = 0
    calibration_total = 0
    rescue_total = 0
    known_total = 0
    all_total = 0
    unclassified_total = 0
    signed_effective_budget_delta = 0
    runtime_adjustment_total = 0

    for entry in entries:
        entry_type = str(_entry_field(entry, "entry_type", "") or "").strip()
        delta = int(_entry_field(entry, "delta_kcal", 0) or 0)
        if entry_type == "meal_consumption":
            continue
        all_total += delta
        runtime_adjustment_total += runtime_adjustment_delta_for_entry(
            entry_type=entry_type,
            delta_kcal=delta,
        )
        signed_effective_budget_delta += effective_budget_delta_for_entry(
            entry_type=entry_type,
            delta_kcal=delta,
        )
        if entry_type == "manual_adjustment":
            manual_total += delta
            known_total += delta
        elif entry_type == "calibration_adjustment":
            calibration_total += delta
            known_total += delta
        elif entry_type == "rescue_overlay":
            rescue_total += delta
            known_total += delta
        else:
            unclassified_total += delta

    return BudgetAdjustmentLayerSummary(
        manual_adjustment_total_kcal=manual_total,
        calibration_adjustment_total_kcal=calibration_total,
        rescue_overlay_total_kcal=rescue_total,
        known_adjustment_entry_total_kcal=known_total,
        all_adjustment_entry_total_kcal=all_total,
        unclassified_adjustment_total_kcal=unclassified_total,
        signed_effective_budget_delta_kcal=signed_effective_budget_delta,
        runtime_adjustment_total_kcal=runtime_adjustment_total,
    )


__all__ = [
    "BudgetAdjustmentLayerSummary",
    "effective_budget_delta_for_entry",
    "runtime_adjustment_delta_for_entry",
    "summarize_budget_adjustment_layers",
]
