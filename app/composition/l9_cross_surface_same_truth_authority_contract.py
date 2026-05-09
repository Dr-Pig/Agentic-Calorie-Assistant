from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


ALLOWED_SURFACE_ROLES = {
    "diagnostic_gate",
    "offline_sidecar_shadow",
    "read_model_mirror",
    "render_mirror",
}
FORBIDDEN_TRUTH_OWNER_TOKENS = {
    "benchmark",
    "fixture",
    "frontend",
    "runner",
    "sidecar",
    "trace",
    "ui",
}
FORBIDDEN_TRUE_FLAGS = (
    "frontend_semantic_owner",
    "runtime_connected",
    "runtime_truth_changed",
    "mutation_changed",
    "live_llm_invoked",
    "web_tavily_used",
    "fooddb_evidence_used",
    "product_readiness_claimed",
    "private_self_use_approved",
    "recommendation_served",
    "durable_memory_written",
    "proactive_sent",
    "scheduler_enabled",
    "manager_context_injected",
    "rescue_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
)
SIDECAR_FALSE_FLAGS = (
    "offline_only",
    "activation_blocked",
    "not_runtime_authority",
)
SIDECAR_TRUE_FLAGS = (
    "user_facing_activation",
    "mutation_authority",
    "product_intelligence_readiness_participant",
)


def build_l9_cross_surface_same_truth_authority_contract(
    surface_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    normalized_rows = []
    for index, row in enumerate(surface_rows, 1):
        surface_id = str(row.get("surface_id") or f"surface_{index}")
        artifact = _dict(row.get("artifact"))
        row_blockers = _row_blockers(surface_id, row, artifact)
        blockers.extend(row_blockers)
        normalized_rows.append(
            {
                "surface_id": surface_id,
                "surface_role": row.get("surface_role"),
                "canonical_truth_owner": row.get("canonical_truth_owner"),
                "authority": {
                    "may_mirror_canonical_fields": True,
                    "may_infer_product_truth": False,
                    "may_mutate_product_state": False,
                    "may_connect_runtime": False,
                },
                "blockers": row_blockers,
            }
        )

    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "l9_cross_surface_same_truth_authority_contract",
            "claim_scope": "l9_cross_surface_contract_only_no_runtime_authority",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "status": "pass" if not blockers else "blocked",
            "blockers": sorted(set(blockers)),
            "summary": {
                "surface_count": len(surface_rows),
                "role_counts": _role_counts(surface_rows),
            },
            "surfaces": normalized_rows,
            "local_only": True,
            "diagnostic_only": True,
            "frontend_semantic_owner": False,
            "runtime_connected": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
        }
    )


def _row_blockers(surface_id: str, row: dict[str, Any], artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    role = str(row.get("surface_role") or "")
    if role not in ALLOWED_SURFACE_ROLES:
        blockers.append(f"{surface_id}.surface_role_invalid")
    if _truth_owner_invalid(str(row.get("canonical_truth_owner") or "")):
        blockers.append(f"{surface_id}.canonical_truth_owner_invalid")
    combined = {**artifact, **{key: value for key, value in row.items() if key != "artifact"}}
    for flag in FORBIDDEN_TRUE_FLAGS:
        if combined.get(flag) is True:
            blockers.append(f"{surface_id}.{flag}")
    if role == "offline_sidecar_shadow":
        for flag in SIDECAR_FALSE_FLAGS:
            if combined.get(flag) is not True:
                blockers.append(f"{surface_id}.{flag}")
        for flag in SIDECAR_TRUE_FLAGS:
            if combined.get(flag) is not False:
                blockers.append(f"{surface_id}.{flag}")
    if role == "render_mirror" and combined.get("frontend_semantic_owner") is not False:
        blockers.append(f"{surface_id}.frontend_semantic_owner")
    if role == "read_model_mirror" and combined.get("read_only") is not True:
        blockers.append(f"{surface_id}.read_only")
    if role == "diagnostic_gate" and combined.get("diagnostic_only") is not True:
        blockers.append(f"{surface_id}.diagnostic_only")
    return sorted(set(blockers))


def _truth_owner_invalid(value: str) -> bool:
    normalized = value.strip().lower()
    return not normalized or normalized in FORBIDDEN_TRUTH_OWNER_TOKENS


def _role_counts(surface_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in surface_rows:
        role = str(row.get("surface_role") or "missing")
        counts[role] = counts.get(role, 0) + 1
    return dict(sorted(counts.items()))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


__all__ = ["build_l9_cross_surface_same_truth_authority_contract"]
