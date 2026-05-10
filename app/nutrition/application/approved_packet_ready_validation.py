from __future__ import annotations

from typing import Any

REQUIRED_PACKET_LANES = (
    "exact_item_card",
    "generic_common_serving",
    "listed_component",
)
MACRO_FIELDS = ("protein_g", "carbs_g", "fat_g")


def validate_approved_packet_ready_items(fooddb_artifact: dict[str, Any]) -> dict[str, Any]:
    raw_items = fooddb_artifact.get("packet_ready_items")
    items = list(raw_items) if isinstance(raw_items, list) else []
    lane_counts = {lane: 0 for lane in REQUIRED_PACKET_LANES}
    blockers: list[str] = []
    visible_count = 0
    hidden_count = 0

    if not isinstance(raw_items, list) or not items:
        blockers.append("fooddb_packet_ready_items_missing")

    for item in items:
        if not isinstance(item, dict):
            blockers.append("fooddb_packet_ready_item_invalid")
            continue
        lane = _text(item.get("source_lane"))
        if lane in lane_counts:
            lane_counts[lane] += 1
        else:
            blockers.append(f"fooddb_packet_ready_item_unsupported_lane:{lane or 'missing'}")
        visibility = _text(item.get("macro_visibility_status"))
        if visibility == "visible":
            visible_count += 1
        elif visibility == "hidden_missing_source":
            hidden_count += 1
        blockers.extend(_packet_item_blockers(item, lane=lane))

    for lane, count in lane_counts.items():
        if count < 1:
            blockers.append(f"fooddb_packet_ready_lane_missing:{lane}")

    return {
        "status": "approved_packet_ready_items_valid" if not blockers else "blocked",
        "item_count": len(items),
        "lane_counts": lane_counts,
        "macro_visible_item_count": visible_count,
        "macro_hidden_item_count": hidden_count,
        "blockers": blockers,
    }


def _packet_item_blockers(item: dict[str, Any], *, lane: str) -> list[str]:
    prefix = "fooddb_packet_ready_item"
    blockers: list[str] = []
    if item.get("runtime_truth_allowed") is not True:
        blockers.append(f"{prefix}_runtime_truth_not_allowed:{lane or 'missing'}")
    if not _text(item.get("runtime_usage_boundary")):
        blockers.append(f"{prefix}_missing_runtime_usage_boundary:{lane or 'missing'}")
    if _number(item.get("kcal_point")) is None:
        blockers.append(f"{prefix}_missing_kcal_point:{lane or 'missing'}")
    if not _valid_kcal_range(item.get("kcal_range")):
        blockers.append(f"{prefix}_invalid_kcal_range:{lane or 'missing'}")
    if not _object_dict(item.get("source_provenance")).get("source_id"):
        blockers.append(f"{prefix}_missing_source_provenance:{lane or 'missing'}")
    if _object_dict(item.get("approval_metadata")).get("runtime_truth_allowed") is not True:
        blockers.append(f"{prefix}_approval_metadata_not_runtime_allowed:{lane or 'missing'}")

    visibility = _text(item.get("macro_visibility_status"))
    if visibility == "visible":
        blockers.extend(_visible_macro_blockers(item, lane=lane))
    elif visibility == "hidden_missing_source":
        blockers.extend(_hidden_macro_blockers(item, lane=lane))
    else:
        blockers.append(f"{prefix}_invalid_macro_visibility:{lane or 'missing'}")
    return blockers


def _visible_macro_blockers(item: dict[str, Any], *, lane: str) -> list[str]:
    blockers: list[str] = []
    for field in MACRO_FIELDS:
        if _number(item.get(field)) is None:
            blockers.append(f"fooddb_packet_ready_item_visible_macro_missing:{lane}:{field}")
    if _text(item.get("macro_source_basis")) in {"", "unknown"}:
        blockers.append(f"fooddb_packet_ready_item_visible_macro_source_unknown:{lane}")
    if _text(item.get("macro_confidence")) in {"", "unknown"}:
        blockers.append(f"fooddb_packet_ready_item_visible_macro_confidence_unknown:{lane}")
    return blockers


def _hidden_macro_blockers(item: dict[str, Any], *, lane: str) -> list[str]:
    blockers: list[str] = []
    for field in MACRO_FIELDS:
        if item.get(field) is not None:
            blockers.append(f"fooddb_packet_ready_item_hidden_macro_value_present:{lane}:{field}")
    if _text(item.get("macro_source_basis")) != "unknown":
        blockers.append(f"fooddb_packet_ready_item_hidden_macro_source_not_unknown:{lane}")
    if _text(item.get("macro_confidence")) != "unknown":
        blockers.append(f"fooddb_packet_ready_item_hidden_macro_confidence_not_unknown:{lane}")
    return blockers


def _valid_kcal_range(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    low = _number(value[0])
    high = _number(value[1])
    return low is not None and high is not None and low <= high


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


__all__ = ["validate_approved_packet_ready_items"]
