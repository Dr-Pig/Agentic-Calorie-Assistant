from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .exact_brand_web_canary import run_exact_brand_web_canary
from .retrieval_semantic_decision import B2ManagerSemanticDecision


_PACKET_ONLY_LIVE_RUNNER_FILES = (
    "scripts/run_accurate_intake_grokfast_fooddb_packet_smoke.py",
    "scripts/run_accurate_intake_grokfast_websearch_packet_smoke.py",
)
_PROHIBITED_RETRIEVAL_CALLS = (
    "build_retrieval_intent(",
    "build_diagnostic_retrieval_intent(",
    "build_raw_text_retrieval_hint(",
    "build_retrieval_request_from_raw_text_hint(",
    "build_retrieval_request_from_manager_decision(",
)


class _FakeSearchPort:
    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        return [
            {
                "title": "Test Brand Matcha Latte",
                "url": "https://brand.example/products/matcha-latte",
                "snippet": "deterministic official result",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "Test Brand",
                "serving_basis": "per_cup",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
                "raw_ref": "raw:search:001",
            }
        ]


class _FakeExtractPort:
    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        return [
            {
                "url": "https://brand.example/products/matcha-latte",
                "title": "Test Brand Matcha Latte",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "Test Brand",
                "raw_content": "400 kcal",
                "raw_ref": "raw:extract:001",
            }
        ]


def build_retrieval_request_lineage_probe(
    *,
    manager_case_trace: dict[str, Any] | None = None,
    raw_text_case_trace: dict[str, Any] | None = None,
    prohibited_call_files: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    manager_trace = manager_case_trace or asyncio.run(_manager_case_trace())
    raw_trace = raw_text_case_trace or asyncio.run(_raw_text_case_trace())
    observed_prohibited_calls = tuple(prohibited_call_files or _scan_packet_only_live_runner_calls())
    blockers = [
        *_manager_case_blockers(manager_trace),
        *_raw_text_case_blockers(raw_trace),
        *[
            f"packet_only_live_runner_prohibited_call:{path}"
            for path in sorted(observed_prohibited_calls)
        ],
    ]
    return {
        "artifact_type": "accurate_intake_retrieval_request_lineage_probe_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_retrieval_request_lineage_only",
        "claim_scope": "manager_owned_request_lineage_for_live_fooddb_websearch_diagnostics",
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "readiness_claimed": False,
        "manager_case_trace": _trace_summary(manager_trace),
        "raw_text_case_trace": _trace_summary(raw_trace),
        "packet_only_live_runner_audit": {
            "audited_files": list(_PACKET_ONLY_LIVE_RUNNER_FILES),
            "prohibited_calls": list(_PROHIBITED_RETRIEVAL_CALLS),
            "unexpected_prohibited_call_files": list(observed_prohibited_calls),
        },
        "summary": {
            "packet_only_live_runner_count": len(_PACKET_ONLY_LIVE_RUNNER_FILES),
            "manager_owned_canary_clear": not _manager_case_blockers(manager_trace),
            "raw_text_guard_clear": not _raw_text_case_blockers(raw_trace),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


async def _manager_case_trace() -> dict[str, Any]:
    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        manager_decision=B2ManagerSemanticDecision(
            base_dish="Matcha Latte",
            aliases=["Test Brand Matcha Latte"],
            brand_hint="Test Brand",
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
        search_port=_FakeSearchPort(),
        extract_port=_FakeExtractPort(),
        allow_search=True,
    )
    return dict(outcome.trace)


async def _raw_text_case_trace() -> dict[str, Any]:
    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        manager_decision=None,
        search_port=_FakeSearchPort(),
        extract_port=_FakeExtractPort(),
        allow_search=True,
    )
    return dict(outcome.trace)


def _scan_packet_only_live_runner_calls() -> list[str]:
    repo_root = Path(__file__).resolve().parents[3]
    findings: list[str] = []
    for relative_path in _PACKET_ONLY_LIVE_RUNNER_FILES:
        path = repo_root / Path(relative_path)
        content = path.read_text(encoding="utf-8-sig")
        if any(call in content for call in _PROHIBITED_RETRIEVAL_CALLS):
            findings.append(relative_path)
    return findings


def _manager_case_blockers(trace: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if trace.get("retrieval_request_source") != "manager_decision":
        blockers.append("manager_canary_wrong_request_source")
    if trace.get("semantic_authority_source") not in {
        "synthetic_manager_structured_fixture",
        "live_manager_structured_output",
    }:
        blockers.append("manager_canary_wrong_semantic_authority_source")
    if trace.get("retrieval_goal") != "exact_brand_lookup":
        blockers.append("manager_canary_wrong_retrieval_goal")
    if trace.get("attempted") is not True:
        blockers.append("manager_canary_not_attempted")
    if trace.get("skip_reason") is not None:
        blockers.append("manager_canary_unexpected_skip")
    return blockers


def _raw_text_case_blockers(trace: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if trace.get("retrieval_request_source") != "raw_text_hint":
        blockers.append("raw_text_canary_wrong_request_source")
    if trace.get("semantic_authority_source") != "deterministic_raw_text_hint_only":
        blockers.append("raw_text_canary_wrong_semantic_authority_source")
    if trace.get("retrieval_goal") is not None:
        blockers.append("raw_text_canary_owned_runtime_goal")
    if trace.get("attempted") is True:
        blockers.append("raw_text_canary_attempted_runtime_execution")
    if trace.get("skip_reason") != "manager_owned_retrieval_intent_required":
        blockers.append("raw_text_canary_missing_manager_guard")
    return blockers


def _trace_summary(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "semantic_authority_source": trace.get("semantic_authority_source"),
        "retrieval_request_source": trace.get("retrieval_request_source"),
        "retrieval_goal": trace.get("retrieval_goal"),
        "raw_text_retrieval_hint_goal": trace.get("raw_text_retrieval_hint_goal"),
        "skip_reason": trace.get("skip_reason"),
        "attempted": trace.get("attempted") is True,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_retrieval_request_lineage_probe"]
