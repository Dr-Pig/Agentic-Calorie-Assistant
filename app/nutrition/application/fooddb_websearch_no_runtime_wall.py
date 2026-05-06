from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from .exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from .exact_evidence_lane_policy import build_exact_evidence_lane_policy_artifact
from .exact_evidence_lane_status_packet import build_exact_evidence_lane_status_packet
from .fooddb_activation_gap_report import build_fooddb_activation_gap_report
from .fooddb_evidence_status_packet import build_fooddb_evidence_status_packet
from .fooddb_integration_readiness_matrix import build_fooddb_integration_readiness_matrix
from .fooddb_runtime_anchor_batch import (
    build_fooddb_runtime_coverage_matrix,
    build_fooddb_status_packet,
    build_internal_seed_runtime_anchor_batch,
)
from .websearch_cache_rate_license_wall import build_websearch_cache_rate_license_wall
from .websearch_candidate_lane_status_packet import build_websearch_candidate_lane_status_packet
from .websearch_candidate_packet_smoke import build_websearch_candidate_packet_smoke
from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic
from .websearch_exact_candidate_review_packet import build_websearch_exact_candidate_review_packet
from .websearch_extract_result_candidate_smoke import build_websearch_extract_result_candidate_smoke
from .websearch_grokfast_live_diagnostic_case_matrix import (
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)
from .websearch_live_extract_preflight import build_websearch_live_extract_preflight
from .websearch_selected_extract_packet_smoke import build_websearch_selected_extract_packet_smoke
from .websearch_source_policy import build_websearch_source_policy_artifact
from .websearch_source_adapter_guard import build_websearch_source_adapter_guard


FORBIDDEN_TRUE_KEYS = frozenset(
    {
        "approval_allowed_by_this_packet",
        "exact_card_created",
        "exact_card_creation_allowed",
        "live_extract_used",
        "live_provider_used",
        "live_websearch_used",
        "manager_context_changed",
        "manager_context_packet_changed",
        "mutation_changed",
        "packet_ready_truth_allowed",
        "packetizer_format_changed",
        "private_self_use_approved",
        "product_readiness_claimed",
        "production_selected",
        "promotion_allowed",
        "raw_content_allowed_in_manager_context",
        "raw_content_included",
        "raw_source_rows_included",
        "readiness_claimed",
        "runtime_mutation_allowed",
        "runtime_mutation_attempted",
        "runtime_truth_changed",
        "selected_extract_truth_allowed",
        "self_use_approved",
        "shared_contract_changed",
        "snippet_truth_allowed",
        "websearch_runtime_truth_allowed",
    }
)


def build_default_fooddb_websearch_no_runtime_wall() -> dict[str, Any]:
    exact_lane = build_exact_evidence_lane_policy_artifact()
    exact_readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=exact_lane
    )
    selected_extract = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=exact_readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected_extract
    )
    exact_review = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )
    websearch_status = build_websearch_candidate_lane_status_packet()
    artifacts = (
        *_default_fooddb_status_artifacts(),
        build_fooddb_integration_readiness_matrix(),
        build_websearch_source_policy_artifact(),
        build_websearch_source_adapter_guard(),
        build_websearch_cache_rate_license_wall(),
        build_websearch_candidate_pipeline_diagnostic(),
        build_websearch_candidate_packet_smoke(),
        selected_extract,
        extract_result,
        exact_review,
        build_websearch_grokfast_live_diagnostic_case_matrix_artifact(),
        build_websearch_live_extract_preflight(
            exact_review_packet_artifact=exact_review,
        ),
        exact_lane,
        exact_readiness,
        websearch_status,
        build_exact_evidence_lane_status_packet(websearch_status_packet=websearch_status),
    )
    return build_fooddb_websearch_no_runtime_wall(artifacts=artifacts)


def build_fooddb_websearch_no_runtime_wall(
    *,
    artifacts: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    artifact_results = [_artifact_result(artifact) for artifact in artifacts]
    blockers = [
        blocker
        for result in artifact_results
        for blocker in result["blockers"]
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_fooddb_websearch_no_runtime_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_no_runtime_wall_only",
        "claim_scope": "fooddb_websearch_candidate_preflight_report_no_runtime_effect_wall",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "artifact_results": artifact_results,
        "summary": {
            "artifact_count": len(artifact_results),
            "pass_count": sum(1 for result in artifact_results if result["status"] == "pass"),
            "blocked_count": sum(1 for result in artifact_results if result["status"] != "pass"),
            "runtime_truth_leak_count": sum(
                1
                for result in artifact_results
                for blocker in result["blockers"]
                if "runtime_truth" in blocker
            ),
            "live_or_readiness_leak_count": sum(
                1
                for result in artifact_results
                for blocker in result["blockers"]
                if "live_" in blocker or "readiness" in blocker or "self_use" in blocker
            ),
        },
        "policy": {
            "deterministic_wall_scope": "candidate_preflight_status_report_artifacts",
            "allowed_fooddb_runtime_anchor_presence": (
                "not_evaluated_here; this wall checks effect/claim leakage only"
            ),
            "websearch_candidate_runtime_truth": "forbidden",
            "exact_card_candidate_runtime_truth": "forbidden",
            "mutation": "forbidden",
            "live_calls": "forbidden",
            "readiness_claims": "forbidden",
        },
        "next_required_slice": (
            "grokfast_fooddb_or_websearch_packet_live_diagnostic"
            if clear
            else "inspect_fooddb_websearch_no_runtime_wall_blockers"
        ),
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_runtime_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_websearch_runtime_truth",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _artifact_result(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact_type = str(artifact.get("artifact_type") or "unknown_artifact")
    paths = _stable_unique(_forbidden_paths(artifact, artifact_type=artifact_type))
    blockers = [f"{artifact_type}:{path}" for path in paths]
    return {
        "artifact_type": artifact_type,
        "status": "pass" if not blockers else "blocked",
        "classification": artifact.get("classification"),
        "claim_scope": artifact.get("claim_scope"),
        "blockers": blockers,
        "checked_forbidden_key_count": len(FORBIDDEN_TRUE_KEYS),
        "checked_forbidden_pattern_policy": (
            "status_blocker_count_suffix_and_candidate_lane_fail_closed"
        ),
    }


def _forbidden_paths(
    value: Any,
    *,
    path: str = "$",
    artifact_type: str = "",
    parent: dict[str, Any] | None = None,
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _status_is_blocked(key, child, child_path):
                violations.append(child_path)
            if _blocker_list_is_non_empty(key, child):
                violations.append(child_path)
            if _value_is_claim_signal(child) and _truthy_key_forbidden(
                key,
                child_path,
                artifact_type=artifact_type,
                parent=value,
            ):
                violations.append(child_path)
            if _count_key_forbidden(key, child, child_path):
                violations.append(child_path)
            violations.extend(
                _forbidden_paths(
                    child,
                    path=child_path,
                    artifact_type=artifact_type,
                    parent=value,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(
                _forbidden_paths(
                    child,
                    path=f"{path}[{index}]",
                    artifact_type=artifact_type,
                    parent=parent,
                )
            )
    return violations


def _stable_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _default_fooddb_status_artifacts() -> tuple[dict[str, Any], ...]:
    small_anchor_payload = _read_repo_json("app/knowledge/small_anchor_store_tw.json")
    tfda_source_payload = _read_repo_json("app/knowledge/tfda_per100g_source_evidence_tw.json")
    exact_card_payload = _read_repo_json("app/knowledge/exact_item_cards_tw.json")
    coverage_matrix = build_fooddb_runtime_coverage_matrix(small_anchor_payload=small_anchor_payload)
    runtime_batch = build_internal_seed_runtime_anchor_batch(small_anchor_payload=small_anchor_payload)
    return (
        build_fooddb_evidence_status_packet(
            small_anchor_payload=small_anchor_payload,
            tfda_source_payload=tfda_source_payload,
            exact_card_payload=exact_card_payload,
        ),
        build_fooddb_activation_gap_report(
            small_anchor_payload=small_anchor_payload,
            tfda_source_payload=tfda_source_payload,
            exact_card_payload=exact_card_payload,
        ),
        build_fooddb_status_packet(
            small_anchor_payload=small_anchor_payload,
            coverage_matrix=coverage_matrix,
            runtime_batch=runtime_batch,
        ),
    )


def _read_repo_json(relative_path: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    payload = json.loads((root / relative_path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"fooddb_no_runtime_wall_payload_must_be_object:{relative_path}")
    return payload


def _truthy_key_forbidden(
    key: str,
    path: str,
    *,
    artifact_type: str,
    parent: dict[str, Any],
) -> bool:
    lowered = key.lower()
    if lowered == "runtime_truth_allowed" and path.endswith(".approval_metadata.runtime_truth_allowed"):
        return _path_is_candidate_lane(f"{artifact_type}.{path}")
    if _metadata_key_allowed(lowered):
        return False
    if lowered in FORBIDDEN_TRUE_KEYS:
        return True
    if lowered == "runtime_truth_allowed":
        return not (
            _approved_fooddb_common_serving_anchor(parent)
            and not _path_is_candidate_lane(f"{artifact_type}.{path}")
        )
    candidate_context = _path_is_candidate_lane(f"{artifact_type}.{path}")
    if _runtime_truth_key_forbidden(lowered):
        return True
    if _candidate_truth_key_forbidden(lowered, path, candidate_context=candidate_context):
        return True
    if _mutation_key_forbidden(lowered):
        return True
    if _live_usage_key_forbidden(lowered):
        return True
    if _promotion_key_forbidden(lowered):
        return True
    if _readiness_key_forbidden(lowered):
        return True
    if _context_or_schema_change_key_forbidden(lowered):
        return True
    if _contract_or_format_change_key_forbidden(lowered):
        return True
    if _product_loop_key_forbidden(lowered):
        return True
    if _source_blocker_family_key(lowered):
        return True
    return False


def _status_is_blocked(key: str, value: Any, path: str) -> bool:
    if key.lower() != "status" or path != "$.status":
        return False
    status = str(value).strip().lower()
    if not status:
        return False
    return status not in {"pass", "passed"}


def _blocker_list_is_non_empty(key: str, value: Any) -> bool:
    lowered = key.lower()
    if not (
        lowered == "blockers"
        or lowered == "violations"
        or "blocker" in lowered
        or "leak" in lowered
        or "violation" in lowered
        or lowered.endswith("_blockers")
        or lowered.endswith("_violations")
    ):
        return False
    return (
        (isinstance(value, list) and bool(value))
        or (isinstance(value, dict) and bool(value))
        or _value_is_claim_signal(value)
    )


def _count_key_forbidden(key: str, value: Any, path: str) -> bool:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    if value <= 0:
        return False
    lowered = key.lower()
    if lowered == "runtime_truth_allowed_count":
        return _path_is_candidate_lane(path)
    return any(
        marker in lowered
        for marker in (
            "exact_card_created",
            "blocker_count",
            "blockers_count",
            "invocation_count",
            "leak_count",
            "live_provider_used",
            "live_websearch_used",
            "mutation_allowed",
            "mutation_attempted",
            "promotion_allowed",
            "readiness_claimed",
            "ready_for_runtime_truth",
            "runtime_mutation",
            "runtime_truth",
            "runtime_truth_changed",
            "selected_extract_truth_allowed",
            "self_use_approved",
            "snippet_truth_allowed",
            "violation_count",
            "violations_count",
            "websearch_runtime_truth",
        )
    )


def _value_is_claim_signal(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float) and not isinstance(value, bool):
        return value > 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized or normalized in {"0", "false", "no", "none", "null", "not_used"}:
            return False
        return not any(token in normalized for token in ("false", "no", "none", "not", "null"))
    if isinstance(value, list | dict):
        return bool(value)
    return False


def _live_usage_key_forbidden(lowered_key: str) -> bool:
    actors = ("live", "llm", "provider", "websearch", "web_search", "tavily")
    if not any(actor in lowered_key for actor in actors):
        return False
    if "allowed" in lowered_key:
        return True
    return any(
        marker in lowered_key
        for marker in (
            "call",
            "called",
            "call_used",
            "enabled",
            "invoked",
            "invocation",
            "invocations",
            "request",
            "request_sent",
            "sent",
            "used",
            "usage",
        )
    ) or (
        "allowed" in lowered_key
        and ("call" in lowered_key or "live" in lowered_key or "runtime" in lowered_key)
    )


def _mutation_key_forbidden(lowered_key: str) -> bool:
    return "mutation" in lowered_key or lowered_key == "ledger_mutated"


def _promotion_key_forbidden(lowered_key: str) -> bool:
    if "promot" not in lowered_key:
        return False
    return any(
        marker in lowered_key
        for marker in (
            "allowed",
            "created",
            "promoted",
            "runtime_truth",
            "truth",
        )
    )


def _readiness_key_forbidden(lowered_key: str) -> bool:
    if "readiness_claim" in lowered_key:
        return True
    if "self_use" in lowered_key and "approved" in lowered_key:
        return True
    if "claimed" in lowered_key or "claim" in lowered_key:
        return any(
            marker in lowered_key
            for marker in (
                "private_self_use",
                "product",
                "production",
                "self_use",
            )
        )
    if "ready" not in lowered_key and "readiness" not in lowered_key:
        return False
    return any(
        marker in lowered_key
        for marker in (
            "private_self_use",
            "product",
            "production",
            "self_use",
        )
    )


def _context_or_schema_change_key_forbidden(lowered_key: str) -> bool:
    if not _change_family_key(lowered_key):
        return False
    return any(
        marker in lowered_key
        for marker in (
            "context",
            "manager_context",
            "schema",
        )
    )


def _contract_or_format_change_key_forbidden(lowered_key: str) -> bool:
    if not _change_family_key(lowered_key):
        return False
    return any(
        marker in lowered_key
        for marker in (
            "contract",
            "format",
            "packet",
            "packetizer",
            "shared",
        )
    )


def _product_loop_key_forbidden(lowered_key: str) -> bool:
    if "product_loop" in lowered_key and (
        "activat" in lowered_key
        or "claim" in lowered_key
        or "consum" in lowered_key
        or "integrat" in lowered_key
        or "integration" in lowered_key
        or "ready" in lowered_key
        or "readiness" in lowered_key
    ):
        return True
    return "completed_product_loop" in lowered_key


def _source_blocker_family_key(lowered_key: str) -> bool:
    return any(marker in lowered_key for marker in ("blocker", "leak", "violation"))


def _metadata_key_allowed(lowered_key: str) -> bool:
    return lowered_key == "artifact_type" or lowered_key.endswith("_artifact_type")


def _change_family_key(lowered_key: str) -> bool:
    return any(
        marker in lowered_key
        for marker in ("change", "changed", "modif", "modified", "update", "updated")
    )


def _runtime_truth_key_forbidden(lowered_key: str) -> bool:
    if "runtime_truth" not in lowered_key:
        return False
    if "required_before_runtime_truth" in lowered_key:
        return False
    return any(
        marker in lowered_key
        for marker in (
            "allowed",
            "changed",
            "created",
            "leak",
            "promoted",
            "ready",
            "readiness",
        )
    )


def _candidate_truth_key_forbidden(
    lowered_key: str,
    path: str,
    *,
    candidate_context: bool,
) -> bool:
    if "required_before_runtime_truth" in lowered_key:
        return False
    if not candidate_context:
        return False
    if lowered_key in {
        "exact_card",
        "final_truth",
        "packet_truth",
        "promotion",
        "runtime_truth",
        "selected_truth",
        "truth",
    }:
        return True
    if not any(marker in lowered_key for marker in ("exact_card", "promot", "truth")):
        return False
    return any(
        marker in lowered_key
        for marker in (
            "allowed",
            "created",
            "final",
            "promoted",
            "ready",
            "readiness",
            "selected",
        )
    )


def _approved_fooddb_common_serving_anchor(parent: dict[str, Any]) -> bool:
    approval = parent.get("approval_metadata")
    return (
        parent.get("runtime_role") == "common_serving_anchor"
        and parent.get("runtime_truth_allowed") is True
        and isinstance(approval, dict)
        and approval.get("runtime_truth_allowed") is True
    )


def _path_is_candidate_lane(path: str) -> bool:
    lowered = path.lower()
    return any(
        token in lowered
        for token in (
            "websearch",
            "candidate",
            "selected_extract",
            "extract_result",
            "exact_evidence",
            "exact_lane",
            "exact_source",
            "exact_item",
            "exact_card",
            "review_packet",
        )
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FORBIDDEN_TRUE_KEYS",
    "build_default_fooddb_websearch_no_runtime_wall",
    "build_fooddb_websearch_no_runtime_wall",
]
