from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from app.nutrition.application.fooddb_retrieval_policy import IndexedFoodRecord


class SupabaseRowsFoodEvidenceIndex:
    """Offline Supabase/Postgres row adapter for FoodEvidenceIndexPort.

    This adapter does not own a Supabase client or perform network I/O. It maps
    rows returned by a future Supabase/Postgres infrastructure layer into the
    same IndexedFoodRecord contract used by local JSON and SQLite FTS adapters.
    """

    def __init__(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        source_label: str = "supabase_food_evidence_rows",
        table_name: str = "food_evidence_records",
    ) -> None:
        self._raw_rows = tuple(dict(row) for row in rows)
        self._source_label = source_label
        self._table_name = table_name
        self._mapped_records, self._mapping_blockers = _map_rows(self._raw_rows)

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Mapping[str, Any]],
        *,
        source_label: str = "supabase_food_evidence_rows",
        table_name: str = "food_evidence_records",
    ) -> "SupabaseRowsFoodEvidenceIndex":
        return cls(rows, source_label=source_label, table_name=table_name)

    def load_records(self) -> tuple[IndexedFoodRecord, ...]:
        return self._mapped_records

    def describe_index(self) -> dict[str, Any]:
        runtime_records = [
            record
            for record in self._mapped_records
            if record.runtime_role == "common_serving_anchor"
        ]
        semantic_records = [
            record
            for record in self._mapped_records
            if record.runtime_role == "basket_family_semantic_only"
        ]
        return {
            "adapter_type": "supabase_rows_food_evidence_index",
            "source_label": self._source_label,
            "table_name": self._table_name,
            "record_contract": "IndexedFoodRecord",
            "runtime_truth_boundary": "adapter_returns_indexed_records_not_truth_decisions",
            "raw_row_count": len(self._raw_rows),
            "mapped_record_count": len(self._mapped_records),
            "mapping_status": "pass" if not self._mapping_blockers else "blocked",
            "mapping_blockers": list(self._mapping_blockers),
            "runtime_record_count": len(runtime_records),
            "semantic_record_count": len(semantic_records),
            "row_shape_policy": {
                "supported_array_columns": [
                    "aliases",
                    "kcal_range",
                    "followup_hints",
                    "major_modifiers",
                ],
                "supported_jsonb_columns": [
                    "portion_basis",
                    "source_provenance",
                    "approval_metadata",
                    "record_payload",
                    "payload_json",
                ],
                "network_io_allowed": False,
                "supabase_client_visible": False,
            },
            "future_backends": ["supabase_postgres"],
            "forbidden_policy_dependencies": [
                "sqlite_file_path",
                "supabase_client",
                "webshell",
                "manager_context_packet",
            ],
        }


def _map_rows(rows: tuple[dict[str, Any], ...]) -> tuple[tuple[IndexedFoodRecord, ...], tuple[str, ...]]:
    mapped: list[IndexedFoodRecord] = []
    blockers: list[str] = []
    for index, row in enumerate(rows):
        record, row_blockers = _record_from_row(index=index, row=row)
        blockers.extend(row_blockers)
        if record is not None:
            mapped.append(record)
    return tuple(sorted(mapped, key=lambda record: record.anchor_id)), tuple(blockers)


def _record_from_row(
    *,
    index: int,
    row: Mapping[str, Any],
) -> tuple[IndexedFoodRecord | None, list[str]]:
    payload, payload_blockers = _payload_from_row(row)
    values = {**payload, **{key: value for key, value in row.items() if value is not None}}
    blockers = [f"row_{index}:{blocker}" for blocker in payload_blockers]

    anchor_id = _text(values.get("anchor_id"))
    canonical_name = _text(values.get("canonical_name"))
    runtime_role = _text(values.get("runtime_role"))
    if not anchor_id:
        blockers.append(f"row_{index}:missing_anchor_id")
    if not canonical_name:
        blockers.append(f"row_{index}:missing_canonical_name")
    if not runtime_role:
        blockers.append(f"row_{index}:missing_runtime_role")
    if blockers:
        return None, blockers

    kcal_point, point_blocker = _optional_int(values.get("kcal_point"))
    if point_blocker:
        blockers.append(f"row_{index}:{point_blocker}")

    kcal_range, range_blocker = _range_tuple(values.get("kcal_range"), values)
    if range_blocker:
        blockers.append(f"row_{index}:{range_blocker}")
    if blockers:
        return None, blockers

    record = IndexedFoodRecord(
        anchor_id=anchor_id,
        canonical_name=canonical_name,
        aliases=_string_tuple(values.get("aliases")),
        dish_type=_text(values.get("dish_type")),
        runtime_truth_allowed=values.get("runtime_truth_allowed") is True,
        runtime_role=runtime_role,
        kcal_point=kcal_point,
        kcal_range=kcal_range,
        serving_basis=_text(values.get("serving_basis")),
        portion_basis=_json_object_or_value(values.get("portion_basis")),
        followup_hints=_string_tuple(values.get("followup_hints")),
        major_modifiers=_dict_tuple(values.get("major_modifiers")),
        runtime_usage_boundary=_text(values.get("runtime_usage_boundary")),
        source_provenance=_dict_value(values.get("source_provenance")),
        approval_metadata=_dict_value(values.get("approval_metadata")),
    )
    return record, blockers


def _payload_from_row(row: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    for key in ("record_payload", "payload_json"):
        if key not in row or row.get(key) in (None, ""):
            continue
        value = row[key]
        if isinstance(value, Mapping):
            return dict(value), []
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return {}, [f"invalid_{key}"]
            if isinstance(decoded, Mapping):
                return dict(decoded), []
            return {}, [f"{key}_not_object"]
        return {}, [f"{key}_unsupported_type"]
    return {}, []


def _text(value: object) -> str:
    return str(value or "").strip()


def _string_tuple(value: object) -> tuple[str, ...]:
    decoded = _json_object_or_value(value)
    if isinstance(decoded, (list, tuple)):
        return tuple(str(item).strip() for item in decoded if str(item).strip())
    if isinstance(decoded, str) and decoded.strip():
        return (decoded.strip(),)
    return ()


def _dict_tuple(value: object) -> tuple[dict[str, Any], ...]:
    decoded = _json_object_or_value(value)
    if not isinstance(decoded, (list, tuple)):
        return ()
    return tuple(dict(item) for item in decoded if isinstance(item, Mapping))


def _dict_value(value: object) -> dict[str, Any]:
    decoded = _json_object_or_value(value)
    return dict(decoded) if isinstance(decoded, Mapping) else {}


def _json_object_or_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    if text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _range_tuple(value: object, values: Mapping[str, Any]) -> tuple[tuple[int, int] | None, str | None]:
    decoded = _json_object_or_value(value)
    if isinstance(decoded, (list, tuple)) and len(decoded) >= 2:
        low, low_blocker = _optional_int(decoded[0], field_name="kcal_range_low")
        high, high_blocker = _optional_int(decoded[1], field_name="kcal_range_high")
        if low_blocker:
            return None, low_blocker
        if high_blocker:
            return None, high_blocker
        if low is None or high is None:
            return None, "invalid_kcal_range"
        return (low, high), None
    low = values.get("kcal_range_low")
    high = values.get("kcal_range_high")
    if low not in (None, "") and high not in (None, ""):
        low_value, low_blocker = _optional_int(low, field_name="kcal_range_low")
        high_value, high_blocker = _optional_int(high, field_name="kcal_range_high")
        if low_blocker:
            return None, low_blocker
        if high_blocker:
            return None, high_blocker
        if low_value is None or high_value is None:
            return None, "invalid_kcal_range"
        return (low_value, high_value), None
    if value not in (None, ""):
        return None, "invalid_kcal_range"
    return None, None


def _optional_int(
    value: object,
    *,
    field_name: str = "kcal_point",
) -> tuple[int | None, str | None]:
    if value in (None, ""):
        return None, None
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, f"invalid_{field_name}"


__all__ = ["SupabaseRowsFoodEvidenceIndex"]
