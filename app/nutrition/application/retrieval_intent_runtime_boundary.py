from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any

from .exact_brand_web_canary import ExactBrandWebCanaryOutcome, run_exact_brand_web_canary
from .food_evidence_retriever_router import (
    FoodEvidenceRetrieverRoutePlan,
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan_for_request,
)
from .retrieval_intent import RAW_TEXT_RETRIEVAL_INTENT_POLICY, build_raw_text_retrieval_hint
from .retrieval_request import build_retrieval_request_from_raw_text_hint


_RAW_HINT_BUILDER_NAME = "build_" "raw_text_retrieval_hint"
_RUNTIME_CALL_RE = re.compile(r"\b" + _RAW_HINT_BUILDER_NAME + r"\(")
_ALLOWED_RUNTIME_CALL_FILES = ("app/nutrition/application/exact_brand_web_canary.py",)
_IGNORED_AUDIT_FILES = (
    "app/nutrition/application/retrieval_intent_runtime_boundary.py",
    "app/nutrition/application/retrieval_intent.py",
    "app/nutrition/application/retrieval_request.py",
)


def build_retrieval_intent_runtime_boundary_artifact(
    *,
    raw_hint_route_plan: FoodEvidenceRetrieverRoutePlan | None = None,
    canary_outcome: ExactBrandWebCanaryOutcome | None = None,
    runtime_call_files: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    raw_hint = build_raw_text_retrieval_hint("星巴克冰拿鐵大杯")
    route_plan = raw_hint_route_plan or build_food_evidence_retriever_route_plan_for_request(
        build_retrieval_request_from_raw_text_hint("星巴克冰拿鐵大杯"),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
    )
    outcome = canary_outcome or asyncio.run(
        run_exact_brand_web_canary(
            raw_user_input="星巴克冰拿鐵大杯",
            manager_decision=None,
            search_port=None,
            extract_port=None,
            allow_search=True,
        )
    )
    call_files = runtime_call_files or tuple(_runtime_call_files())
    unexpected_call_files = tuple(
        sorted(path for path in call_files if path not in _ALLOWED_RUNTIME_CALL_FILES)
    )
    blockers = [
        *_route_plan_blockers(route_plan),
        *_canary_probe_blockers(outcome.trace, result_present=outcome.result is not None),
        *_runtime_call_file_blockers(call_files),
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_retrieval_intent_runtime_boundary_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_retrieval_intent_boundary_only",
        "claim_scope": "raw_text_retrieval_hint_must_not_own_runtime_execution",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "readiness_claimed": False,
        "raw_text_retrieval_intent_policy": dict(RAW_TEXT_RETRIEVAL_INTENT_POLICY),
        "runtime_route_probe": {
            "raw_text_hint_goal": raw_hint.retrieval_goal,
            "primary_backend": route_plan.primary_backend,
            "backend_sequence": list(route_plan.backend_sequence),
            "retrieval_intent_source": route_plan.retrieval_intent_source,
            "manager_owned_intent_required": route_plan.manager_owned_intent_required,
            "raw_text_hint_executed": route_plan.raw_text_hint_executed,
            "read_only": route_plan.read_only,
            "mutation_allowed": route_plan.mutation_allowed,
            "runtime_truth_source": route_plan.runtime_truth_source,
            "routing_reasons": list(route_plan.routing_reasons),
        },
        "exact_brand_web_canary_probe": {
            "result_present": outcome.result is not None,
            "skip_reason": outcome.trace.get("skip_reason"),
            "semantic_authority_source": outcome.trace.get("semantic_authority_source"),
            "retrieval_goal": outcome.trace.get("retrieval_goal"),
            "raw_text_retrieval_hint_goal": outcome.trace.get("raw_text_retrieval_hint_goal"),
            "attempted": outcome.trace.get("attempted") is True,
        },
        "runtime_call_site_audit": {
            "allowed_runtime_call_files": list(_ALLOWED_RUNTIME_CALL_FILES),
            "observed_runtime_call_files": list(call_files),
            "unexpected_runtime_call_files": list(unexpected_call_files),
        },
        "summary": {
            "observed_runtime_call_file_count": len(call_files),
            "unexpected_runtime_call_file_count": len(unexpected_call_files),
            "manager_owned_runtime_routes_required": route_plan.manager_owned_intent_required,
            "raw_text_runtime_execution_blocked": route_plan.primary_backend == "blocked_no_execution",
            "exact_brand_canary_manager_guard_clear": outcome.trace.get("skip_reason")
            == "manager_owned_retrieval_intent_required",
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_shared_contract_change",
            "no_readiness_claim",
        ],
    }


def _route_plan_blockers(route_plan: FoodEvidenceRetrieverRoutePlan) -> list[str]:
    blockers: list[str] = []
    if route_plan.retrieval_intent_source != "raw_text_hint":
        blockers.append("raw_text_hint_route_probe_wrong_source")
    expected_blocked = replace(
        route_plan,
        primary_backend="blocked_no_execution",
        backend_sequence=(),
        manager_owned_intent_required=True,
        raw_text_hint_executed=False,
        read_only=True,
        mutation_allowed=False,
        runtime_truth_source="manager_owned_retrieval_intent_required",
    )
    if route_plan.primary_backend != expected_blocked.primary_backend:
        blockers.append("raw_text_hint_route_not_blocked")
    if route_plan.backend_sequence != expected_blocked.backend_sequence:
        blockers.append("raw_text_hint_route_has_backend_sequence")
    if route_plan.manager_owned_intent_required is not True:
        blockers.append("raw_text_hint_route_missing_manager_guard")
    if route_plan.raw_text_hint_executed is not False:
        blockers.append("raw_text_hint_route_executed_runtime_lookup")
    if route_plan.read_only is not True:
        blockers.append("raw_text_hint_route_not_read_only")
    if route_plan.mutation_allowed is not False:
        blockers.append("raw_text_hint_route_allowed_mutation")
    if route_plan.runtime_truth_source != expected_blocked.runtime_truth_source:
        blockers.append("raw_text_hint_route_truth_source_mismatch")
    return blockers


def _canary_probe_blockers(trace: dict[str, Any], *, result_present: bool) -> list[str]:
    blockers: list[str] = []
    if result_present:
        blockers.append("exact_brand_canary_raw_hint_produced_runtime_result")
    if trace.get("skip_reason") != "manager_owned_retrieval_intent_required":
        blockers.append("exact_brand_canary_missing_manager_guard")
    if trace.get("semantic_authority_source") != "deterministic_raw_text_hint_only":
        blockers.append("exact_brand_canary_wrong_authority_source")
    if trace.get("retrieval_goal") is not None:
        blockers.append("exact_brand_canary_raw_hint_owned_retrieval_goal")
    if trace.get("raw_text_retrieval_hint_goal") != "exact_brand_lookup":
        blockers.append("exact_brand_canary_missing_trace_hint_goal")
    if trace.get("attempted") is True:
        blockers.append("exact_brand_canary_attempted_runtime_execution")
    return blockers


def _runtime_call_file_blockers(call_files: tuple[str, ...]) -> list[str]:
    unexpected = [
        path for path in call_files if path not in _ALLOWED_RUNTIME_CALL_FILES
    ]
    blockers = [
        f"unexpected_raw_text_retrieval_runtime_call:{path}"
        for path in sorted(unexpected)
    ]
    if not any(path in _ALLOWED_RUNTIME_CALL_FILES for path in call_files):
        blockers.append("allowed_runtime_trace_hint_call_missing")
    return blockers


def _runtime_call_files() -> list[str]:
    repo_root = Path(__file__).resolve().parents[3]
    search_roots = (
        repo_root / "app" / "nutrition" / "application",
        repo_root / "app" / "composition",
        repo_root / "app" / "runtime",
    )
    call_files: set[str] = set()
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            relative_path = path.relative_to(repo_root).as_posix()
            if relative_path in _IGNORED_AUDIT_FILES:
                continue
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if line.lstrip().startswith(f"def {_RAW_HINT_BUILDER_NAME}("):
                    continue
                if _RUNTIME_CALL_RE.search(line):
                    call_files.add(relative_path)
                    break
    return sorted(call_files)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_retrieval_intent_runtime_boundary_artifact"]
