from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sys
import threading
import time
from typing import Any
import urllib.request

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_local_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False, encoding="utf-8-sig")
        return
    except ModuleNotFoundError:
        pass
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_local_env(ROOT / ".env")

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.composition import accurate_intake_debug_routes, intake_chat_turn_routes, intake_routes  # noqa: E402
from app.composition.current_shell_golden_set_grader import (  # noqa: E402
    load_golden_set_manifest,
)
from app.composition.current_shell_golden_set_manifest_access import (  # noqa: E402
    assert_golden_set_suite_inventory,
    golden_set_cases_for_scope,
    golden_set_suite_inventory,
)
from app.composition.current_shell_golden_set_request_trace_adapter import (  # noqa: E402
    build_golden_case_trace_from_request_trace,
    build_golden_trace_artifact_from_request_traces,
)
from app.composition.onboarding_service import (  # noqa: E402
    OnboardingBootstrapInput,
    bootstrap_body_plan_for_date,
)
from app.database import get_db, get_or_create_user  # noqa: E402
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord  # noqa: E402
from app.logging import REQUEST_TRACE_DIR  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.shared.infra.models import MessageBuffer, utcnow  # noqa: E402
from scripts.build_current_shell_self_use_golden_set_replay import (  # noqa: E402
    DEFAULT_OUTPUT_PATH as DEFAULT_REPLAY_OUTPUT_PATH,
    build_golden_set_replay,
)
from scripts.run_accurate_intake_mvp_manager_style_smoke import (  # noqa: E402
    DeterministicSelfUseManagerProvider,
)
from scripts.run_accurate_intake_browser_shell_smoke import (  # noqa: E402
    _install_fetch_recorder,
    _load_sync_playwright,
)


DEFAULT_MANIFEST_PATH = ROOT / "docs" / "quality" / "current_shell_self_use_golden_set_manifest.yaml"
DEFAULT_DB_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_e2e.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_e2e_report.json"
DEFAULT_TRACE_ARTIFACT_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_trace_artifact.json"
DEFAULT_LOCAL_DATE = "2026-05-14"


class _RecordedGoldenWebSearchPort:
    """Recorded provider rows for WebSearch golden cases.

    This port is only a tool data source. It never chooses intent, workflow
    effect, commit posture, or response text; the Manager must call the search
    path before these rows enter the runtime.
    """

    def __init__(self, *, case_id: str) -> None:
        self.case_id = case_id
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "recorded_golden_websearch",
            "configured": True,
            "recorded_candidate_only": True,
            "semantic_owner": "manager",
        }

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "max_results": max_results})
        return _recorded_websearch_hits(self.case_id)[:max_results]


class _RecordedGoldenWebExtractPort:
    def __init__(self, *, case_id: str) -> None:
        self.case_id = case_id
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "recorded_golden_web_extract",
            "configured": True,
            "recorded_candidate_only": True,
            "semantic_owner": "manager",
        }

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.calls.append({"urls": list(urls), "query": query})
        rows = _recorded_web_extract_rows(self.case_id)
        wanted = {str(url).strip() for url in urls}
        return [row for row in rows if str(row.get("url") or "").strip() in wanted]


def _recorded_websearch_ports_for_case(case_id: str) -> tuple[Any | None, Any | None]:
    if case_id not in {"GSW2", "GSW3", "GSW4"}:
        return None, None
    return (
        _RecordedGoldenWebSearchPort(case_id=case_id),
        _RecordedGoldenWebExtractPort(case_id=case_id),
    )


def _recorded_websearch_hits(case_id: str) -> list[dict[str, Any]]:
    if case_id == "GSW2":
        return [
            {
                "title": "松屋 牛燒肉定食 Matsuya gyu yakiniku teishoku nutrition",
                "url": "https://matsuya.example/menu/gyu-yakiniku-teishoku",
                "snippet": "Official menu page lists serving calories for 松屋 牛燒肉定食 / gyu yakiniku teishoku.",
                "score": 0.95,
                "officialness": "official",
                "source_class": "brand_menu_page",
                "source_quality_label": "high",
                "brand_detected": "Matsuya",
                "serving_basis": "per_set",
                "nutrition_fields_present": ["kcal"],
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "identity_confidence": "high",
                "applicability_confidence": "high",
                "raw_ref": "recorded/websearch/gsw2#0",
            }
        ]
    if case_id == "GSW3":
        return [
            {
                "title": "Peeled chili chicken hot pot frozen retail pack",
                "url": "https://shop.example/frozen-peeled-chili-chicken-hotpot",
                "snippet": "Retail frozen pack nutrition for a packaged product, not in-store hot pot.",
                "score": 0.86,
                "officialness": "unknown",
                "source_class": "ecommerce_or_frozen_package",
                "source_quality_label": "low",
                "brand_detected": "retail pack",
                "serving_basis": "per_package",
                "nutrition_fields_present": ["kcal"],
                "license_status": "unknown",
                "robots_status": "allowed",
                "identity_confidence": "medium",
                "applicability_confidence": "low",
                "raw_ref": "recorded/websearch/gsw3#0",
            }
        ]
    if case_id == "GSW4":
        return [
            {
                "title": "麥當勞 大麥克 McDonalds Big Mac nutrition",
                "url": "https://mcdonalds.example/menu/big-mac",
                "snippet": "Official component page for 麥當勞 大麥克 / Big Mac.",
                "score": 0.96,
                "officialness": "official",
                "source_class": "brand_menu_component_page",
                "source_quality_label": "high",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "nutrition_fields_present": ["kcal"],
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "identity_confidence": "high",
                "applicability_confidence": "high",
                "raw_ref": "recorded/websearch/gsw4#big-mac",
            },
            {
                "title": "麥當勞 中薯 McDonalds medium fries nutrition",
                "url": "https://mcdonalds.example/menu/medium-fries",
                "snippet": "Official component page for 麥當勞 中薯 / medium fries.",
                "score": 0.94,
                "officialness": "official",
                "source_class": "brand_menu_component_page",
                "source_quality_label": "high",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "nutrition_fields_present": ["kcal"],
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "identity_confidence": "high",
                "applicability_confidence": "high",
                "raw_ref": "recorded/websearch/gsw4#fries",
            },
            {
                "title": "麥當勞 中杯可樂 McDonalds medium coke nutrition",
                "url": "https://mcdonalds.example/menu/medium-coke",
                "snippet": "Official component page for 麥當勞 中杯可樂 / medium Coke.",
                "score": 0.94,
                "officialness": "official",
                "source_class": "brand_menu_component_page",
                "source_quality_label": "high",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "nutrition_fields_present": ["kcal"],
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "identity_confidence": "high",
                "applicability_confidence": "high",
                "raw_ref": "recorded/websearch/gsw4#coke",
            },
        ]
    return []


def _recorded_web_extract_rows(case_id: str) -> list[dict[str, Any]]:
    if case_id == "GSW2":
        return [
            {
                "url": "https://matsuya.example/menu/gyu-yakiniku-teishoku",
                "title": "松屋 牛燒肉定食 Matsuya gyu yakiniku teishoku nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_set",
                "brand_detected": "Matsuya",
                "raw_content": "松屋 牛燒肉定食 / Gyu yakiniku teishoku 720 kcal per set.",
                "raw_ref": "recorded/webextract/gsw2#0",
            }
        ]
    if case_id == "GSW3":
        return [
            {
                "url": "https://shop.example/frozen-peeled-chili-chicken-hotpot",
                "title": "Peeled chili chicken hot pot frozen retail pack",
                "source_type": "third_party_ecommerce",
                "officialness": "unknown",
                "serving_basis": "per_package",
                "brand_detected": "retail pack",
                "raw_content": "Frozen package nutrition; not applicable to in-store meal.",
                "raw_ref": "recorded/webextract/gsw3#0",
            }
        ]
    if case_id == "GSW4":
        return [
            {
                "url": "https://mcdonalds.example/menu/big-mac",
                "title": "麥當勞 大麥克 McDonalds Big Mac nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "麥當勞 大麥克 / Big Mac 560 kcal.",
                "raw_ref": "recorded/webextract/gsw4#big-mac",
            },
            {
                "url": "https://mcdonalds.example/menu/medium-fries",
                "title": "麥當勞 中薯 McDonalds medium fries nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "麥當勞 中薯 / Medium fries 320 kcal.",
                "raw_ref": "recorded/webextract/gsw4#fries",
            },
            {
                "url": "https://mcdonalds.example/menu/medium-coke",
                "title": "麥當勞 中杯可樂 McDonalds medium Coke nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "麥當勞 中杯可樂 / Medium Coke 210 kcal.",
                "raw_ref": "recorded/webextract/gsw4#coke",
            },
        ]
    return []


def build_current_shell_golden_set_e2e_report(
    *,
    case_ids: list[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    trace_artifact_path: Path = DEFAULT_TRACE_ARTIFACT_PATH,
    replay_output_path: Path = DEFAULT_REPLAY_OUTPUT_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    provider_mode: str = "configured",
    local_date: str = DEFAULT_LOCAL_DATE,
    allow_search: bool = False,
    entrypoint_mode: str = "estimate",
    suite_scope: str = "core",
) -> dict[str, Any]:
    manifest = _read_manifest(manifest_path)
    assert_golden_set_suite_inventory(manifest)
    selected_cases = _select_cases(manifest, case_ids, suite_scope=suite_scope)
    engine, SessionLocal = _session_factory(db_path)
    provider = _provider_for_mode(provider_mode)
    client = _build_test_client(
        SessionLocal,
        provider=provider,
        feedback_dir=db_path.parent / f"{db_path.stem}_feedback",
    )
    case_runs: list[dict[str, Any]] = []
    case_traces: list[dict[str, Any]] = []

    try:
        for case in selected_cases:
            case_run, request_trace = _run_case(
                client=client,
                SessionLocal=SessionLocal,
                case=case,
                local_date=local_date,
                allow_search=allow_search,
                provider_mode=provider_mode,
                provider=provider,
                entrypoint_mode=entrypoint_mode,
            )
            case_runs.append(case_run)
            if request_trace:
                case_traces.append(
                    _build_case_trace(
                        case_id=str(case.get("case_id") or ""),
                        request_trace=request_trace,
                        provider_mode=provider_mode,
                    )
                )
    finally:
        _close_test_client(client)
        engine.dispose()

    trace_artifact = build_golden_trace_artifact_from_request_traces(case_traces)
    replay_manifest = _manifest_for_selected_cases(
        manifest,
        selected_cases,
        suite_scope="explicit" if case_ids else suite_scope,
    )
    replay = build_golden_set_replay(manifest=replay_manifest, trace_artifact=trace_artifact)
    report = _json_safe(
        {
            "artifact_type": "current_shell_self_use_golden_set_e2e_report",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "real_entrypoint_runtime_projection",
            "entrypoint": "browser_ui" if entrypoint_mode == "browser" else "/estimate",
            "entrypoint_mode": entrypoint_mode,
            "suite_scope": "explicit" if case_ids else suite_scope,
            "provider_mode": provider_mode,
            "live_invoked_by_runner": _live_invoked(case_traces),
            "runner_inferred_semantics": False,
            "semantic_keyword_oracle_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "whole_product_mvp_claimed": False,
            "summary": {
                **golden_set_suite_inventory(manifest),
                "selected_suite_scope": "explicit" if case_ids else suite_scope,
                "selected_case_count": len(selected_cases),
                "request_trace_case_count": len(case_traces),
                "strict_golden_set_replay_passed": replay["summary"][
                    "strict_golden_set_replay_passed"
                ],
                "failed_case_count": replay["summary"]["failed_case_count"],
                "missing_case_count": replay["summary"]["missing_case_count"],
            },
            "case_runs": case_runs,
            "trace_artifact": trace_artifact,
            "replay": replay,
        }
    )
    _write_json(trace_artifact_path, trace_artifact)
    _write_json(replay_output_path, replay)
    _write_json(output_path, report)
    return report


def _run_case(
    *,
    client: TestClient,
    SessionLocal: sessionmaker[Session],
    case: dict[str, Any],
    local_date: str,
    allow_search: bool,
    provider_mode: str,
    provider: Any | None,
    entrypoint_mode: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    case_id = str(case.get("case_id") or "")
    user_external_id = f"gs-e2e-{case_id.lower()}-{secrets.token_hex(3)}"
    _seed_case_state(SessionLocal, case=case, user_external_id=user_external_id, local_date=local_date)
    if entrypoint_mode == "browser" and case_id == "GS17":
        return _run_browser_feedback_case(
            SessionLocal=SessionLocal,
            provider=provider,
            case=case,
            user_external_id=user_external_id,
            local_date=local_date,
        )
    if entrypoint_mode == "browser" and case_id not in {"GS17", "GS19"}:
        return _run_browser_chat_case(
            SessionLocal=SessionLocal,
            provider=provider,
            provider_mode=provider_mode,
            case=case,
            user_external_id=user_external_id,
            local_date=local_date,
            allow_search=allow_search,
        )
    if case_id == "GS17":
        return _run_feedback_case(
            client=client,
            case=case,
            user_external_id=user_external_id,
            local_date=local_date,
        )
    if case_id == "GS19":
        return _run_browser_correlated_case(
            SessionLocal=SessionLocal,
            provider=provider,
            case=case,
            user_external_id=user_external_id,
            local_date=local_date,
        )
    recorded_search_port, recorded_extract_port = _recorded_websearch_ports_for_case(case_id)
    previous_search_provider = intake_routes.search_provider
    previous_extract_provider = intake_routes.extract_provider
    if allow_search and recorded_search_port is not None and recorded_extract_port is not None:
        intake_routes.search_provider = recorded_search_port
        intake_routes.extract_provider = recorded_extract_port
    turn_reports: list[dict[str, Any]] = []
    request_traces: list[dict[str, Any]] = []
    last_request_trace: dict[str, Any] | None = None
    try:
        for index, turn in enumerate(_script_turns(case), start=1):
            request_id = f"{case_id.lower()}-turn{index}-{secrets.token_hex(8)}"
            trace_path = REQUEST_TRACE_DIR / f"{request_id}.json"
            started = datetime.now(UTC)
            response = client.post(
                "/estimate",
                json={
                    "text": str(turn.get("utterance_zh_tw") or turn.get("utterance") or ""),
                    "allow_search": allow_search,
                    "user_id": user_external_id,
                    "local_date": local_date,
                    "request_id": request_id,
                },
            )
            elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            request_trace = _read_json(trace_path) if trace_path.exists() else None
            if request_trace:
                request_traces.append(request_trace)
                last_request_trace = request_trace
            turn_reports.append(
                {
                    "turn": index,
                    "entrypoint": "/estimate",
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    "request_trace_path": str(trace_path),
                    "request_trace_exists": trace_path.exists(),
                    "response_has_payload": bool(_response_json(response).get("payload")),
                    "runner_inferred_semantics": False,
                    "semantic_keyword_oracle_used": False,
                }
            )
    finally:
        if recorded_search_port is not None or recorded_extract_port is not None:
            intake_routes.search_provider = previous_search_provider
            intake_routes.extract_provider = previous_extract_provider
    if _should_aggregate_session(case):
        return (
            {
                "case_id": case_id,
                "entrypoint": "/estimate",
                "user_external_id": user_external_id,
                "local_date": local_date,
                "turns": turn_reports,
                "request_trace_selected": "aggregate_turns",
                "runner_inferred_semantics": False,
            },
            {
                "golden_case_trace_direct": _aggregate_long_session_case_trace(
                    case_id=case_id,
                    request_traces=request_traces,
                    provider_mode=provider_mode,
                    expected_runtime=_dict(case.get("expected_runtime")),
                )
            },
        )
    return (
        {
            "case_id": case_id,
            "entrypoint": "/estimate",
            "user_external_id": user_external_id,
            "local_date": local_date,
            "turns": turn_reports,
            "request_trace_selected": "last_turn",
            "runner_inferred_semantics": False,
        },
        last_request_trace,
    )


def _should_aggregate_session(case: dict[str, Any]) -> bool:
    expected_runtime = _dict(case.get("expected_runtime"))
    return str(expected_runtime.get("workflow_effect") or "") in {
        "multi_turn_mixed_actions",
        "commit_then_refine",
    }


def _aggregate_long_session_case_trace(
    *,
    case_id: str,
    request_traces: list[dict[str, Any]],
    provider_mode: str,
    expected_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    turn_traces = [
        _build_case_trace(
            case_id=case_id,
            request_trace=request_trace,
            provider_mode=provider_mode,
        )
        for request_trace in request_traces
    ]
    return {
        "case_id": case_id,
        "trace_id": _aggregate_trace_id(turn_traces),
        "manager_provider": _aggregate_manager_provider(turn_traces),
        "prompt_registry": _first_present_mapping(turn_traces, "prompt_registry"),
        "provider_profile": _first_present_mapping(turn_traces, "provider_profile"),
        "current_turn_context_packet": _aggregate_context_packet(turn_traces),
        "react_trace": _aggregate_react_trace(turn_traces),
        "requested_tools": _flatten_lists(turn_traces, "requested_tools"),
        "filtered_tool_plan": _aggregate_filtered_tool_plan(turn_traces),
        "executed_tools": _flatten_lists(turn_traces, "executed_tools"),
        "compact_packets": _flatten_lists(turn_traces, "compact_packets"),
        "guard_result": _aggregate_named_results(turn_traces, "guard_result"),
        "mutation_result": _aggregate_named_results(turn_traces, "mutation_result"),
        "renderer_input_basis": _aggregate_named_results(turn_traces, "renderer_input_basis"),
        "final_response_basis": _aggregate_named_results(turn_traces, "final_response_basis"),
        "runtime": _aggregate_runtime(
            turn_traces,
            expected_workflow_effect=str(_dict(expected_runtime).get("workflow_effect") or ""),
        ),
        "ui": _aggregate_ui(turn_traces),
        "response": _aggregate_response(turn_traces),
        "latency": _aggregate_latency(turn_traces),
        "dogfood_trace": _aggregate_dogfood_trace(turn_traces),
        "generalization": _aggregate_generalization(turn_traces),
        "turn_traces": _summarize_turn_traces(turn_traces),
    }


def _aggregate_trace_id(turn_traces: list[dict[str, Any]]) -> str:
    ids = [str(trace.get("trace_id") or "").strip() for trace in turn_traces]
    ids = [trace_id for trace_id in ids if trace_id]
    if not ids:
        return ""
    return f"{ids[0]}..{ids[-1]}" if len(ids) > 1 else ids[0]


def _aggregate_manager_provider(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    providers = [_dict(trace.get("manager_provider")) for trace in turn_traces]
    if any("fixture" in str(provider.get("semantic_source") or "").lower() for provider in providers):
        return {
            "provider": "deterministic_self_use_manager_fixture",
            "semantic_source": "fixture_provider",
            "live_llm_invoked": False,
        }
    live = next((provider for provider in providers if provider.get("live_llm_invoked") is True), {})
    if live:
        return live
    return next((provider for provider in providers if provider), {})


def _first_present_mapping(turn_traces: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return next((_dict(trace.get(key)) for trace in turn_traces if _dict(trace.get(key))), {})


def _aggregate_context_packet(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    context = dict(_first_present_mapping(list(reversed(turn_traces)), "current_turn_context_packet"))
    context["aggregate_turn_count"] = len(turn_traces)
    context["aggregate_context_source"] = "per_turn_context_packets"
    return context


def _aggregate_react_trace(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    react_traces = [_dict(trace.get("react_trace")) for trace in turn_traces]
    return {
        "manager_pass_count": sum(int(_dict(trace.get("latency")).get("llm_calls") or 0) for trace in turn_traces),
        "tool_call_count": sum(int(_dict(trace.get("latency")).get("tool_calls") or 0) for trace in turn_traces),
        "turn_count": len(turn_traces),
        "aggregate_source": "per_turn_react_traces",
        "manager_pass_1": {
            "aggregate_source": "per_turn_manager_pass_1",
            "present_turn_count": sum(1 for trace in react_traces if _dict(trace.get("manager_pass_1"))),
        },
        "manager_pass_final": {
            "aggregate_source": "per_turn_manager_pass_final",
            "present_turn_count": sum(
                1 for trace in react_traces if _dict(trace.get("manager_pass_final"))
            ),
        },
    }


def _flatten_lists(turn_traces: list[dict[str, Any]], key: str) -> list[Any]:
    flattened: list[Any] = []
    for trace in turn_traces:
        flattened.extend(_list(trace.get(key)))
    return flattened


def _aggregate_filtered_tool_plan(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    plans = [_dict(trace.get("filtered_tool_plan")) for trace in turn_traces]
    return {"turns": [plan for plan in plans if plan], "aggregate_source": "per_turn_tool_plans"}


def _aggregate_named_results(turn_traces: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [_dict(trace.get(key)) for trace in turn_traces]
    return {"turns": [value for value in values if value], "aggregate_source": f"per_turn_{key}"}


def _aggregate_runtime(
    turn_traces: list[dict[str, Any]],
    *,
    expected_workflow_effect: str = "",
) -> dict[str, Any]:
    runtimes = [_dict(trace.get("runtime")) for trace in turn_traces]
    runtime: dict[str, Any] = {
        "workflow_effect": "multi_turn_mixed_actions",
        "turn_count": len(turn_traces),
        "source": "aggregated_real_turn_traces",
    }
    if expected_workflow_effect == "commit_then_refine" and _commit_then_refine(runtimes):
        runtime["workflow_effect"] = "commit_then_refine"
        runtime["old_version_superseded"] = True
        runtime["ledger_delta_trace_required"] = True
        runtime["mutation_allowed"] = True
        runtime["target_attachment"] = _last_mapping(runtimes, "target_attachment")
    if len(runtimes) >= 2 and runtimes[1].get("mutation_allowed") is not None:
        runtime["inquiry_turn_mutates"] = runtimes[1].get("mutation_allowed") is True
    if _pending_then_commit_then_correction_then_budget_query(turn_traces):
        runtime["pending_then_commit_then_correction_then_budget_query"] = True
    if _old_and_new_versions_not_double_counted(turn_traces):
        runtime["old_and_new_versions_double_counted"] = False
    if all(runtime_item.get("fallback_400_allowed") is not True for runtime_item in runtimes):
        runtime["fallback_400_allowed"] = False
    if any(runtime_item.get("pre_manager_estimability_shortcut_allowed") is True for runtime_item in runtimes):
        runtime["pre_manager_estimability_shortcut_allowed"] = True
    elif any("pre_manager_estimability_shortcut_allowed" in runtime_item for runtime_item in runtimes):
        runtime["pre_manager_estimability_shortcut_allowed"] = False
    return runtime


def _commit_then_refine(runtimes: list[dict[str, Any]]) -> bool:
    commit_index: int | None = None
    for index, runtime in enumerate(runtimes):
        if runtime.get("final_action") == "commit" or runtime.get("canonical_commit_status") == "committed":
            commit_index = index
            break
    if commit_index is None:
        return False
    return any(
        runtime.get("final_action") == "correction_applied"
        and runtime.get("old_version_superseded") is True
        for runtime in runtimes[commit_index + 1 :]
    )


def _last_mapping(items: list[dict[str, Any]], key: str) -> dict[str, Any]:
    for item in reversed(items):
        value = _dict(item.get(key))
        if value:
            return value
    return {}


def _pending_then_commit_then_correction_then_budget_query(turn_traces: list[dict[str, Any]]) -> bool:
    runtimes = [_dict(trace.get("runtime")) for trace in turn_traces]
    semantic_decisions = [
        _dict(_dict(trace.get("final_response_basis")).get("semantic_decision"))
        for trace in turn_traces
    ]
    has_pending = any(
        runtime.get("pending_followup_saved") is True
        or runtime.get("final_action") == "ask_followup"
        or runtime.get("workflow_effect") == "ask_followup"
        or semantic.get("final_action_candidate") == "ask_followup"
        for runtime, semantic in zip(runtimes, semantic_decisions, strict=False)
    )
    has_commit = any(
        runtime.get("final_action") == "commit"
        or runtime.get("canonical_commit_status") == "committed"
        or semantic.get("final_action_candidate") == "commit"
        or semantic.get("mutation_intent_candidate") == "canonical_write"
        for runtime, semantic in zip(runtimes, semantic_decisions, strict=False)
    )
    has_correction = any(
        runtime.get("final_action") == "correction_applied"
        or runtime.get("workflow_effect") in {"correction", "correction_write", "correction_applied"}
        or semantic.get("final_action_candidate") == "correction_applied"
        or semantic.get("current_turn_intent") == "correct_meal"
        for runtime, semantic in zip(runtimes, semantic_decisions, strict=False)
    )
    has_budget_query = any(
        runtime.get("workflow_effect") in {"answer_query", "budget_query", "remaining_query"}
        or runtime.get("final_action") in {"answer_remaining_budget", "answer_budget_query"}
        or runtime.get("current_turn_intent") in {"budget_query", "remaining_query"}
        or semantic.get("current_turn_intent") == "answer_remaining_budget"
        or semantic.get("final_action_candidate") == "answer_remaining_budget"
        for runtime, semantic in zip(runtimes, semantic_decisions, strict=False)
    )
    return has_pending and has_commit and has_correction and has_budget_query


def _old_and_new_versions_not_double_counted(turn_traces: list[dict[str, Any]]) -> bool:
    for trace in turn_traces:
        runtime = _dict(trace.get("runtime"))
        ui = _dict(trace.get("ui"))
        if runtime.get("old_version_superseded") is True and (
            runtime.get("ledger_recomputed") is True
            or ui.get("old_version_not_counted") is True
            or ui.get("removed_item_not_counted") is True
        ):
            return True
    return False


def _aggregate_ui(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    ui_values = [_dict(trace.get("ui")) for trace in turn_traces]
    ui: dict[str, Any] = {}
    if all(ui_value.get("frontend_nutrition_math_allowed") is not True for ui_value in ui_values):
        ui["frontend_nutrition_math_allowed"] = False
    if any(ui_value.get("today_consumed_updates") is True for ui_value in ui_values):
        ui["chat_today_same_truth_required"] = True
    if any(
        ui_value.get("pending_question_visible") is True
        or _dict(trace.get("runtime")).get("pending_followup_saved") is True
        for trace, ui_value in zip(turn_traces, ui_values, strict=False)
    ):
        ui["queued_or_pending_state_preserved"] = True
    for flag in (
        "old_version_not_counted",
        "removed_item_not_counted",
        "today_consumed_updates",
        "frontend_nutrition_math_allowed",
        "frontend_remaining_math_allowed",
    ):
        if any(ui_value.get(flag) is True for ui_value in ui_values):
            ui[flag] = True
    if all(ui_value.get("frontend_nutrition_math_allowed") is not True for ui_value in ui_values):
        ui["frontend_nutrition_math_allowed"] = False
    if all(ui_value.get("frontend_remaining_math_allowed") is not True for ui_value in ui_values):
        ui["frontend_remaining_math_allowed"] = False
    return ui


def _aggregate_response(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    responses = [_dict(trace.get("response")) for trace in turn_traces]
    visible_text = "\n".join(
        str(response.get("assistant_message") or response.get("visible_text") or "").strip()
        for response in responses
        if str(response.get("assistant_message") or response.get("visible_text") or "").strip()
    )
    response: dict[str, Any] = {}
    if visible_text:
        response["visible_text"] = visible_text
        response["assistant_message"] = visible_text
    for forbidden_flag in (
        "internal_debug_words_present",
        "state_contradiction",
        "invented_nutrition_fact",
    ):
        if any(response_item.get(forbidden_flag) is True for response_item in responses):
            response[forbidden_flag] = True
    if responses and all(response_item.get("zh_tw_primary") is not False for response_item in responses):
        response["zh_tw_primary"] = True
    return response


def _aggregate_latency(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    latency_values = [_dict(trace.get("latency")) for trace in turn_traces]
    return {
        "timeout_is_product_target": False,
        "llm_calls": sum(int(latency.get("llm_calls") or 0) for latency in latency_values),
        "tool_calls": sum(int(latency.get("tool_calls") or 0) for latency in latency_values),
        "total_latency_ms": sum(int(latency.get("total_latency_ms") or 0) for latency in latency_values),
    }


def _aggregate_dogfood_trace(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    dogfood_traces = [_dict(trace.get("dogfood_trace")) for trace in turn_traces]
    return {
        "trace_id": _aggregate_trace_id(turn_traces),
        "session_id": _aggregate_trace_id(turn_traces),
        "feedback_links_to_trace": any(
            dogfood_trace.get("feedback_links_to_trace") is True for dogfood_trace in dogfood_traces
        ),
    }


def _aggregate_generalization(turn_traces: list[dict[str, Any]]) -> dict[str, Any]:
    generalizations = [_dict(trace.get("generalization")) for trace in turn_traces]
    merged: dict[str, Any] = {}
    for generalization in generalizations:
        for key, value in generalization.items():
            if value is True:
                merged[key] = True
    return merged


def _summarize_turn_traces(turn_traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for index, trace in enumerate(turn_traces, start=1):
        runtime = _dict(trace.get("runtime"))
        summaries.append(
            {
                "turn": index,
                "trace_id": trace.get("trace_id"),
                "workflow_effect": runtime.get("workflow_effect"),
                "final_action": runtime.get("final_action"),
                "mutation_allowed": runtime.get("mutation_allowed"),
            }
        )
    return summaries


def _run_feedback_case(
    *,
    client: TestClient,
    case: dict[str, Any],
    user_external_id: str,
    local_date: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_id = str(case.get("case_id") or "")
    request_id = f"{case_id.lower()}-feedback-{secrets.token_hex(8)}"
    token = _local_debug_token()
    started = datetime.now(UTC)
    response = client.post(
        "/accurate-intake/feedback",
        headers={"X-Local-Debug-Token": token},
        json={
            "category": "manager_behavior",
            "feedback_text": "\u525b\u525b\u9435\u677f\u9eb5\u4f30\u932f",
            "page": "chat",
            "selected_date": local_date,
            "user_external_id": user_external_id,
            "severity": "medium",
            "ui_event": {
                "source_page": "chat",
                "route": "/static/accurate-intake-chat.html",
                "feedback_drawer": "inline",
                "draft_survives_navigation": True,
                "user_entered_trace_id": False,
                "user_entered_request_id": False,
                "request_id": request_id,
            },
        },
    )
    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    payload = _response_json(response)
    case_trace = _feedback_case_trace(
        case_id=case_id,
        response_payload=payload,
        elapsed_ms=elapsed_ms,
    )
    return (
        {
            "case_id": case_id,
            "entrypoint": "/accurate-intake/feedback",
            "user_external_id": user_external_id,
            "local_date": local_date,
            "turns": [
                {
                    "turn": 1,
                    "entrypoint": "/accurate-intake/feedback",
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    "response_has_payload": bool(payload),
                    "user_entered_trace_id": False,
                    "user_entered_request_id": False,
                    "runner_inferred_semantics": False,
                    "semantic_keyword_oracle_used": False,
                }
            ],
            "request_trace_selected": "feedback_route_response",
            "runner_inferred_semantics": False,
        },
        {"golden_case_trace_direct": case_trace},
    )


def _run_browser_feedback_case(
    *,
    SessionLocal: sessionmaker[Session],
    provider: Any | None,
    case: dict[str, Any],
    user_external_id: str,
    local_date: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_id = str(case.get("case_id") or "")
    token = _local_debug_token()
    app = _build_browser_app(
        SessionLocal,
        provider=provider,
        feedback_dir=DEFAULT_DB_PATH.parent / f"{case_id.lower()}_feedback",
    )
    port = _free_port()
    server, thread = _run_uvicorn_in_thread(app, port=port)
    base_url = f"http://127.0.0.1:{port}"
    started = datetime.now(UTC)
    try:
        _wait_for_http(f"{base_url}/static/accurate-intake-feedback.html", timeout_seconds=20)
        browser_result = _run_gs17_browser_feedback_sequence(
            base_url=base_url,
            user_external_id=user_external_id,
            local_date=local_date,
            local_debug_token=token,
            timeout_ms=120_000,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        _restore_browser_app(app)
    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    record = _dict(browser_result.get("feedback_record"))
    case_trace = _feedback_case_trace(
        case_id=case_id,
        response_payload=record,
        elapsed_ms=elapsed_ms,
    )
    ui_event_trace = _dict(case_trace.get("ui_event_trace"))
    ui_event_trace.update(
        {
            "browser_executed": browser_result.get("browser_executed") is True,
            "entrypoint": "browser_ui_feedback",
            "user_entered_trace_id": browser_result.get("user_entered_trace_id") is True,
            "trace_id_auto_attached": browser_result.get("trace_id_auto_attached") is True,
            "draft_survives_navigation": browser_result.get("draft_survives_navigation") is True,
            "status_text": browser_result.get("status_text"),
        }
    )
    case_trace["ui_event_trace"] = ui_event_trace
    ui = _dict(case_trace.get("ui"))
    ui["draft_survives_navigation"] = browser_result.get("draft_survives_navigation") is True
    ui["browser_executed"] = browser_result.get("browser_executed") is True
    ui["user_enters_trace_id"] = browser_result.get("user_entered_trace_id") is True
    case_trace["ui"] = ui
    case_trace["browser"] = browser_result
    return (
        {
            "case_id": case_id,
            "entrypoint": "browser_ui_feedback",
            "user_external_id": user_external_id,
            "local_date": local_date,
            "turns": [
                {
                    "turn": 1,
                    "entrypoint": "browser_ui_feedback",
                    "status_text": browser_result.get("status_text"),
                    "user_entered_trace_id": browser_result.get("user_entered_trace_id") is True,
                    "trace_id_auto_attached": browser_result.get("trace_id_auto_attached") is True,
                    "runner_inferred_semantics": False,
                    "semantic_keyword_oracle_used": False,
                }
            ],
            "request_trace_selected": "browser_feedback_route_response",
            "browser_executed": browser_result.get("browser_executed") is True,
            "runner_inferred_semantics": False,
        },
        {"golden_case_trace_direct": case_trace},
    )


def _run_browser_correlated_case(
    *,
    SessionLocal: sessionmaker[Session],
    provider: Any | None,
    case: dict[str, Any],
    user_external_id: str,
    local_date: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_id = str(case.get("case_id") or "")
    token = _local_debug_token()
    runtime_provider = provider if provider is not None else intake_routes.manager_provider
    delayed_provider = _FirstCallDelayProvider(runtime_provider, delay_seconds=8.0)
    app = _build_browser_app(
        SessionLocal,
        provider=delayed_provider,
        feedback_dir=DEFAULT_DB_PATH.parent / f"{case_id.lower()}_feedback",
    )
    port = _free_port()
    server, thread = _run_uvicorn_in_thread(app, port=port)
    base_url = f"http://127.0.0.1:{port}"
    started = datetime.now(UTC)
    try:
        _wait_for_http(f"{base_url}/static/accurate-intake-chat.html", timeout_seconds=20)
        browser_result = _run_gs19_browser_sequence(
            base_url=base_url,
            user_external_id=user_external_id,
            local_date=local_date,
            local_debug_token=token,
            timeout_ms=240_000,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        _restore_browser_app(app)
    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    request_traces = _request_traces_for_ids(browser_result.get("trace_ids") or [])
    turn_traces = [
        _build_case_trace(case_id=case_id, request_trace=trace, provider_mode="configured")
        for trace in request_traces
    ]
    case_trace = _browser_correlated_case_trace(
        case_id=case_id,
        browser_result=browser_result,
        turn_traces=turn_traces,
        elapsed_ms=elapsed_ms,
    )
    return (
        {
            "case_id": case_id,
            "entrypoint": "browser_ui",
            "user_external_id": user_external_id,
            "local_date": local_date,
            "turns": browser_result.get("turns") or [],
            "request_trace_selected": "browser_correlated_turns",
            "browser_executed": browser_result.get("browser_executed") is True,
            "runner_inferred_semantics": False,
        },
        {"golden_case_trace_direct": case_trace},
    )


def _run_browser_chat_case(
    *,
    SessionLocal: sessionmaker[Session],
    provider: Any | None,
    provider_mode: str,
    case: dict[str, Any],
    user_external_id: str,
    local_date: str,
    allow_search: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_id = str(case.get("case_id") or "")
    token = _local_debug_token()
    recorded_search_port, recorded_extract_port = _recorded_websearch_ports_for_case(case_id)
    app = _build_browser_app(
        SessionLocal,
        provider=provider,
        feedback_dir=DEFAULT_DB_PATH.parent / f"{case_id.lower()}_feedback",
        search_provider=recorded_search_port if allow_search else None,
        extract_provider=recorded_extract_port if allow_search else None,
    )
    port = _free_port()
    server, thread = _run_uvicorn_in_thread(app, port=port)
    base_url = f"http://127.0.0.1:{port}"
    started = datetime.now(UTC)
    try:
        _wait_for_http(f"{base_url}/static/accurate-intake-chat.html", timeout_seconds=20)
        browser_result = _run_golden_case_browser_chat_sequence(
            base_url=base_url,
            case=case,
            user_external_id=user_external_id,
            local_date=local_date,
            local_debug_token=token,
            timeout_ms=240_000,
            allow_search=allow_search,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        _restore_browser_app(app)
    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    request_traces = _request_traces_for_ids(browser_result.get("trace_ids") or [])
    if _should_aggregate_session(case):
        case_trace = _aggregate_long_session_case_trace(
            case_id=case_id,
            request_traces=request_traces,
            provider_mode=provider_mode,
            expected_runtime=_dict(case.get("expected_runtime")),
        )
    else:
        last_trace = request_traces[-1] if request_traces else {}
        case_trace = _build_case_trace(
            case_id=case_id,
            request_trace=last_trace,
            provider_mode=provider_mode,
        )
    _attach_browser_chat_evidence(
        case_trace,
        browser_result=browser_result,
        elapsed_ms=elapsed_ms,
    )
    return (
        {
            "case_id": case_id,
            "entrypoint": "browser_ui_chat",
            "user_external_id": user_external_id,
            "local_date": local_date,
            "turns": browser_result.get("turns") or [],
            "request_trace_selected": "aggregate_turns" if _should_aggregate_session(case) else "last_browser_turn",
            "browser_executed": browser_result.get("browser_executed") is True,
            "runner_inferred_semantics": False,
        },
        {"golden_case_trace_direct": case_trace},
    )


class _FirstCallDelayProvider:
    def __init__(self, provider: Any | None, *, delay_seconds: float) -> None:
        self.provider = provider
        self.delay_seconds = delay_seconds
        self._delayed = False

    def readiness(self) -> dict[str, Any]:
        if hasattr(self.provider, "readiness"):
            return dict(self.provider.readiness())
        return {}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self._delayed:
            self._delayed = True
            await asyncio.sleep(self.delay_seconds)
        if self.provider is None:
            raise RuntimeError("manager_provider_missing")
        return await self.provider.complete_with_trace(**kwargs)


def _build_browser_app(
    SessionLocal: sessionmaker[Session],
    *,
    provider: Any | None,
    feedback_dir: Path | None = None,
    search_provider: Any | None = None,
    extract_provider: Any | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    previous = (
        intake_routes.manager_provider,
        intake_routes.search_provider,
        intake_routes.extract_provider,
        intake_chat_turn_routes.SessionLocal,
        accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR,
        accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
    )
    if provider is not None:
        intake_routes.manager_provider = provider
    if search_provider is not None or extract_provider is not None:
        intake_routes.search_provider = search_provider
        intake_routes.extract_provider = extract_provider
    intake_chat_turn_routes.SessionLocal = SessionLocal
    if feedback_dir is not None:
        accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR = feedback_dir
        accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = (
            feedback_dir / "review_queue.json"
        )
    os.environ.setdefault("LOCAL_DEBUG_API_TOKEN", _local_debug_token())
    app.state.current_shell_golden_set_restore_runtime = previous
    return app


def _restore_browser_app(app: FastAPI) -> None:
    previous = getattr(app.state, "current_shell_golden_set_restore_runtime", None)
    if previous is None:
        return
    (
        intake_routes.manager_provider,
        intake_routes.search_provider,
        intake_routes.extract_provider,
        intake_chat_turn_routes.SessionLocal,
        accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR,
        accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
    ) = previous


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"server_not_ready:{last_error}")


def _run_uvicorn_in_thread(app: FastAPI, *, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def _run_gs19_browser_sequence(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    local_debug_token: str,
    timeout_ms: int,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script(
            f"""
            (() => {{
              window.LOCAL_DEBUG_API_TOKEN = {json.dumps(local_debug_token)};
            }})();
            """
        )
        _install_fetch_recorder(page)
        try:
            chat_url = (
                f"{base_url}/static/accurate-intake-chat.html?"
                f"user_id={user_external_id}&local_date={local_date}"
            )
            first_message = "早餐吃鐵板麵、荷包蛋"
            queued_message = "還有一杯紅茶"
            page.goto(chat_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector("#message-input", timeout=timeout_ms)
            page.fill("#message-input", first_message)
            page.click("#send-button")
            page.wait_for_function(
                """() => {
                  const text = document.querySelector("#chat-history-status")?.textContent || "";
                  const chat = document.querySelector("#chat-scroll")?.textContent || "";
                  return text.includes("processing") || chat.includes("處理中");
                }""",
                timeout=timeout_ms,
            )
            processing_before_nav = _page_has_processing_state(page)
            page.click('[data-nav-target="today"]')
            page.wait_for_selector("#today-status", timeout=timeout_ms)
            today_loaded_during_processing = page.locator("main").inner_text(timeout=timeout_ms)
            page.click('[data-nav-target="body"]')
            page.wait_for_selector("#body-status", timeout=timeout_ms)
            body_loaded_during_processing = page.locator("main").inner_text(timeout=timeout_ms)
            page.goto(chat_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector("#message-input", timeout=timeout_ms)
            processing_after_nav = _page_has_processing_state(page)
            send_disabled_while_processing = page.locator("#send-button").is_disabled()
            page.fill("#message-input", queued_message)
            page.click("#send-button")
            page.wait_for_function(
                """() => {
                  const chat = document.querySelector("#chat-scroll")?.textContent || "";
                  return chat.includes("已排隊") || chat.includes("queued") || chat.includes("紅茶");
                }""",
                timeout=timeout_ms,
            )
            queued_visible_after_nav = page.locator("#chat-scroll").inner_text(timeout=timeout_ms)
            _wait_for_chat_history_completion(
                base_url=base_url,
                user_external_id=user_external_id,
                local_date=local_date,
                token=local_debug_token,
                timeout_seconds=240,
            )
            page.goto(chat_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector("#message-input", timeout=timeout_ms)
            chat_after_reload = page.locator("#chat-scroll").inner_text(timeout=timeout_ms)
            page.goto(
                f"{base_url}/static/accurate-intake-today.html?user_id={user_external_id}&local_date={local_date}",
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            page.wait_for_selector("#today-status", timeout=timeout_ms)
            today_after = {
                "consumed_kcal": page.locator("#consumed-kcal").inner_text(timeout=timeout_ms),
                "remaining_kcal": page.locator("#remaining-kcal").inner_text(timeout=timeout_ms),
                "meal_text": page.locator("#meal-list").inner_text(timeout=timeout_ms),
                "macro_state": page.locator("#macro-panel").get_attribute("data-macro-state", timeout=timeout_ms),
                "protein_g": page.locator("#protein-g").text_content(timeout=timeout_ms),
                "carbs_g": page.locator("#carbs-g").text_content(timeout=timeout_ms),
                "fat_g": page.locator("#fat-g").text_content(timeout=timeout_ms),
                "macro_guard_reason": page.locator("#macro-guard-reason").text_content(timeout=timeout_ms),
            }
            current_budget = _current_budget_payload(
                base_url=base_url,
                user_external_id=user_external_id,
                local_date=local_date,
                token=local_debug_token,
            )
            page.goto(
                f"{base_url}/static/accurate-intake-body.html?user_id={user_external_id}&local_date={local_date}",
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            page.wait_for_selector("#body-status", timeout=timeout_ms)
            body_after = {
                "active_target": page.locator("#body-active-target").inner_text(timeout=timeout_ms),
                "remaining_kcal": page.locator("#body-remaining-kcal").inner_text(timeout=timeout_ms),
            }
            chat_history = _http_json(
                f"{base_url}/accurate-intake/chat-history?user_id={user_external_id}&local_date={local_date}",
                token=local_debug_token,
            )
            fetch_sequence = page.evaluate("window.__accurateIntakeFetches || []")
            messages = _list(chat_history.get("messages"))
            trace_ids = sorted(
                {
                    str(_dict(message).get("trace_id") or "")
                    for message in messages
                    if str(_dict(message).get("trace_id") or "").strip()
                }
            )
            return {
                "browser_executed": True,
                "turns": [
                    {"turn": 1, "text": first_message},
                    {"turn": 2, "text": queued_message},
                ],
                "processing_state_survives_navigation": processing_before_nav and processing_after_nav,
                "queued_message_survives_navigation": queued_message in queued_visible_after_nav
                and queued_message in chat_after_reload,
                "send_disabled_while_processing": send_disabled_while_processing,
                "chat_after_reload": chat_after_reload,
                "today_after": today_after,
                "current_budget": current_budget,
                "body_after": body_after,
                "today_loaded_during_processing": bool(today_loaded_during_processing),
                "body_loaded_during_processing": bool(body_loaded_during_processing),
                "chat_history": chat_history,
                "trace_ids": trace_ids,
                "fetch_sequence": fetch_sequence,
            }
        finally:
            browser.close()


def _run_gs17_browser_feedback_sequence(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    local_debug_token: str,
    timeout_ms: int,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script(
            f"""
            (() => {{
              window.LOCAL_DEBUG_API_TOKEN = {json.dumps(local_debug_token)};
            }})();
            """
        )
        _install_fetch_recorder(page)
        try:
            feedback_url = (
                f"{base_url}/static/accurate-intake-feedback.html?"
                f"user_id={user_external_id}&local_date={local_date}&source_page=chat"
            )
            page.goto(feedback_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector("#feedback-text", timeout=timeout_ms)
            trace_id_auto_attached = bool(page.locator("#trace-id").input_value(timeout=timeout_ms).strip())
            feedback_text = "剛剛那次鐵板麵估算不符合我的理解。"
            page.fill("#feedback-text", feedback_text)
            page.goto(
                f"{base_url}/static/accurate-intake-today.html?user_id={user_external_id}&local_date={local_date}",
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            page.wait_for_selector("#today-status", timeout=timeout_ms)
            page.goto(feedback_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector("#feedback-text", timeout=timeout_ms)
            draft_after_navigation = page.locator("#feedback-text").input_value(timeout=timeout_ms)
            page.click("#submit-feedback")
            page.wait_for_function(
                """() => (document.querySelector("#feedback-status")?.textContent || "").includes("Captured")""",
                timeout=timeout_ms,
            )
            status_text = page.locator("#feedback-status").inner_text(timeout=timeout_ms)
            review_payload = _http_json(
                f"{base_url}/accurate-intake/review-queue",
                token=local_debug_token,
            )
            records = _list(review_payload.get("desktop_feedback_records"))
            record = _dict(records[-1]) if records else {}
            return {
                "browser_executed": True,
                "status_text": status_text,
                "feedback_record": record,
                "review_queue": review_payload,
                "fetch_sequence": page.evaluate("window.__accurateIntakeFetches || []"),
                "user_entered_trace_id": False,
                "trace_id_auto_attached": trace_id_auto_attached,
                "draft_survives_navigation": draft_after_navigation == feedback_text,
            }
        finally:
            browser.close()


def _run_golden_case_browser_chat_sequence(
    *,
    base_url: str,
    case: dict[str, Any],
    user_external_id: str,
    local_date: str,
    local_debug_token: str,
    timeout_ms: int,
    allow_search: bool,
) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "")
    sync_playwright = _load_sync_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script(
            f"""
            (() => {{
              window.LOCAL_DEBUG_API_TOKEN = {json.dumps(local_debug_token)};
            }})();
            """
        )
        _install_fetch_recorder(page)
        try:
            chat_url = (
                f"{base_url}/static/accurate-intake-chat.html?"
                f"user_id={user_external_id}&local_date={local_date}"
                f"&allow_search={'1' if allow_search else '0'}"
            )
            page.goto(chat_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector("#message-input", timeout=timeout_ms)
            turn_reports: list[dict[str, Any]] = []
            for index, turn in enumerate(_script_turns(case), start=1):
                text = str(turn.get("utterance_zh_tw") or turn.get("utterance") or "")
                page.fill("#message-input", text)
                page.click("#send-button")
                history = _wait_for_chat_history_completion(
                    base_url=base_url,
                    user_external_id=user_external_id,
                    local_date=local_date,
                    token=local_debug_token,
                    timeout_seconds=240,
                    expected_user_count=index,
                )
                page.goto(chat_url, wait_until="networkidle", timeout=timeout_ms)
                page.wait_for_selector("#message-input", timeout=timeout_ms)
                turn_reports.append(
                    {
                        "turn": index,
                        "text": text,
                        "completed_message_count": history.get("message_count"),
                    }
                )
            chat_after_reload = page.locator("#chat-scroll").inner_text(timeout=timeout_ms)
            page.goto(
                f"{base_url}/static/accurate-intake-today.html?user_id={user_external_id}&local_date={local_date}",
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            page.wait_for_selector("#today-status", timeout=timeout_ms)
            today_after = {
                "consumed_kcal": page.locator("#consumed-kcal").inner_text(timeout=timeout_ms),
                "remaining_kcal": page.locator("#remaining-kcal").inner_text(timeout=timeout_ms),
                "meal_text": page.locator("#meal-list").inner_text(timeout=timeout_ms),
                "macro_state": page.locator("#macro-panel").get_attribute("data-macro-state", timeout=timeout_ms),
                "protein_g": page.locator("#protein-g").text_content(timeout=timeout_ms),
                "carbs_g": page.locator("#carbs-g").text_content(timeout=timeout_ms),
                "fat_g": page.locator("#fat-g").text_content(timeout=timeout_ms),
                "macro_guard_reason": page.locator("#macro-guard-reason").text_content(timeout=timeout_ms),
            }
            current_budget = _current_budget_payload(
                base_url=base_url,
                user_external_id=user_external_id,
                local_date=local_date,
                token=local_debug_token,
            )
            page.goto(
                f"{base_url}/static/accurate-intake-body.html?user_id={user_external_id}&local_date={local_date}",
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            page.wait_for_selector("#body-status", timeout=timeout_ms)
            body_after = {
                "active_target": page.locator("#body-active-target").inner_text(timeout=timeout_ms),
                "remaining_kcal": page.locator("#body-remaining-kcal").inner_text(timeout=timeout_ms),
            }
            chat_history = _http_json(
                f"{base_url}/accurate-intake/chat-history?user_id={user_external_id}&local_date={local_date}",
                token=local_debug_token,
            )
            messages = [_dict(message) for message in _list(chat_history.get("messages"))]
            trace_ids = _unique_trace_ids_in_message_order(messages)
            fetch_sequence = page.evaluate("window.__accurateIntakeFetches || []")
            return {
                "browser_executed": True,
                "case_id": case_id,
                "turns": turn_reports,
                "chat_after_reload": chat_after_reload,
                "today_after": today_after,
                "current_budget": current_budget,
                "body_after": body_after,
                "chat_history": chat_history,
                "trace_ids": trace_ids,
                "fetch_sequence": fetch_sequence,
                "chat_response_visible": _latest_assistant_message_visible(messages, chat_after_reload),
                "today_loaded": True,
                "body_loaded": True,
            }
        finally:
            browser.close()


def _page_has_processing_state(page: Any) -> bool:
    text = page.locator("#chat-scroll").inner_text(timeout=30_000)
    status = page.locator("#chat-history-status").inner_text(timeout=30_000)
    return "處理中" in text or "processing" in status or "in_progress" in text


def _http_json(url: str, *, token: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"X-Local-Debug-Token": token})
    with urllib.request.urlopen(request, timeout=30) as response:
        return _dict(json.loads(response.read().decode("utf-8")))


def _current_budget_payload(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    token: str,
) -> dict[str, Any]:
    url = f"{base_url}/today/current-budget?user_id={user_external_id}&local_date={local_date}"
    return _http_json(url, token=token)


def _wait_for_chat_history_completion(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    token: str,
    timeout_seconds: float,
    expected_user_count: int = 2,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_payload: dict[str, Any] = {}
    url = f"{base_url}/accurate-intake/chat-history?user_id={user_external_id}&local_date={local_date}"
    while time.monotonic() < deadline:
        last_payload = _http_json(url, token=token)
        messages = [_dict(message) for message in _list(last_payload.get("messages"))]
        statuses = [str(message.get("runtime_turn_status") or "") for message in messages]
        user_count = sum(1 for message in messages if message.get("role") == "user")
        if user_count >= expected_user_count and statuses and all(status == "completed" for status in statuses):
            return last_payload
        time.sleep(1)
    raise RuntimeError(f"chat_history_not_completed:{last_payload}")


def _request_traces_for_ids(trace_ids: list[Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for trace_id in trace_ids:
        trace_path = REQUEST_TRACE_DIR / f"{trace_id}.json"
        if trace_path.exists():
            traces.append(_read_json(trace_path))
    return traces


def _unique_trace_ids_in_message_order(messages: list[dict[str, Any]]) -> list[str]:
    trace_ids: list[str] = []
    for message in messages:
        trace_id = str(message.get("trace_id") or "").strip()
        if trace_id and trace_id not in trace_ids:
            trace_ids.append(trace_id)
    return trace_ids


def _latest_assistant_message_visible(messages: list[dict[str, Any]], page_text: str) -> bool:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        content = str(message.get("content") or "").strip()
        if content and content in page_text:
            return True
    return False


def _attach_browser_chat_evidence(
    case_trace: dict[str, Any],
    *,
    browser_result: dict[str, Any],
    elapsed_ms: int,
) -> None:
    ui_event_trace = _dict(case_trace.get("ui_event_trace"))
    ui_event_trace.update(
        {
            "browser_executed": browser_result.get("browser_executed") is True,
            "entrypoint": "browser_ui_chat",
            "fetch_sequence": browser_result.get("fetch_sequence") or [],
        }
    )
    case_trace["ui_event_trace"] = ui_event_trace
    ui = _dict(case_trace.get("ui"))
    ui.setdefault("browser_executed", browser_result.get("browser_executed") is True)
    ui.setdefault("chat_response_visible", browser_result.get("chat_response_visible") is True)
    ui.setdefault("today_page_loaded", browser_result.get("today_loaded") is True)
    ui.setdefault("body_page_loaded", browser_result.get("body_loaded") is True)
    ui.setdefault("today_kcal_matches_read_model", _browser_today_kcal_matches_read_model(browser_result))
    ui.setdefault("today_meal_list_matches_read_model", _browser_meal_list_matches_read_model(browser_result))
    ui.setdefault("today_macro_visibility_matches_read_model", _browser_macro_visibility_matches_read_model(browser_result))
    case_trace["ui"] = ui
    runtime = _dict(case_trace.get("runtime"))
    runtime.setdefault("browser_action_maps_to_trace", bool(browser_result.get("trace_ids")))
    case_trace["runtime"] = runtime
    dogfood_trace = _dict(case_trace.get("dogfood_trace"))
    dogfood_trace.setdefault("feedback_links_to_trace", bool(browser_result.get("trace_ids")))
    case_trace["dogfood_trace"] = dogfood_trace
    latency = _dict(case_trace.get("latency"))
    latency.setdefault("browser_total_latency_ms", elapsed_ms)
    latency.setdefault("timeout_is_product_target", False)
    case_trace["latency"] = latency
    case_trace["browser"] = browser_result


def _browser_correlated_case_trace(
    *,
    case_id: str,
    browser_result: dict[str, Any],
    turn_traces: list[dict[str, Any]],
    elapsed_ms: int,
) -> dict[str, Any]:
    aggregate = {
        "case_id": case_id,
        "trace_id": _aggregate_trace_id(turn_traces),
        "manager_provider": _aggregate_manager_provider(turn_traces),
        "prompt_registry": _first_present_mapping(turn_traces, "prompt_registry"),
        "provider_profile": _first_present_mapping(turn_traces, "provider_profile"),
        "current_turn_context_packet": _aggregate_context_packet(turn_traces),
        "react_trace": _aggregate_react_trace(turn_traces),
        "guard_result": _aggregate_named_results(turn_traces, "guard_result"),
        "mutation_result": _aggregate_named_results(turn_traces, "mutation_result"),
        "renderer_input_basis": _aggregate_named_results(turn_traces, "renderer_input_basis"),
        "final_response_basis": _aggregate_named_results(turn_traces, "final_response_basis"),
        "ui_event_trace": {
            "browser_executed": browser_result.get("browser_executed") is True,
            "fetch_sequence": browser_result.get("fetch_sequence") or [],
        },
        "feedback_linkage": {"feedback_links_to_trace": bool(browser_result.get("trace_ids"))},
        "runtime": {
            "workflow_effect": "correlated_full_stack_e2e",
            "browser_action_maps_to_trace": bool(turn_traces),
            "read_model_after_matches_ui": _browser_read_model_matches_ui(browser_result),
        },
        "ui": {
            "browser_executed": browser_result.get("browser_executed") is True,
            "queued_message_survives_navigation": browser_result.get("queued_message_survives_navigation") is True,
            "processing_state_survives_navigation": browser_result.get("processing_state_survives_navigation") is True,
            "no_duplicate_send": _browser_no_duplicate_send(browser_result),
            "chat_today_body_same_truth": _browser_read_model_matches_ui(browser_result),
            "today_kcal_matches_read_model": _browser_today_kcal_matches_read_model(browser_result),
            "today_meal_list_matches_read_model": _browser_meal_list_matches_read_model(browser_result),
            "today_macro_visibility_matches_read_model": _browser_macro_visibility_matches_read_model(browser_result),
        },
        "response": _aggregate_response(turn_traces),
        "latency": {
            **_aggregate_latency(turn_traces),
            "total_latency_ms": elapsed_ms,
            "timeout_is_product_target": False,
        },
        "dogfood_trace": {
            "trace_id": _aggregate_trace_id(turn_traces),
            "feedback_links_to_trace": bool(browser_result.get("trace_ids")),
            "correlates_ui_runtime_read_model_response": _browser_read_model_matches_ui(browser_result),
        },
        "generalization": {},
        "browser": browser_result,
        "turn_traces": _summarize_turn_traces(turn_traces),
    }
    if not turn_traces:
        aggregate["manager_provider"] = {}
    return aggregate


def _browser_read_model_matches_ui(browser_result: dict[str, Any]) -> bool:
    if not _browser_today_kcal_matches_read_model(browser_result):
        return False
    today = _dict(browser_result.get("today_after"))
    body = _dict(browser_result.get("body_after"))
    today_remaining = _first_int(today.get("remaining_kcal"))
    body_remaining = _first_int(body.get("remaining_kcal"))
    return (
        _first_int(today.get("consumed_kcal")) is not None
        and today_remaining is not None
        and today_remaining == body_remaining
    )


def _browser_today_kcal_matches_read_model(browser_result: dict[str, Any]) -> bool:
    today = _dict(browser_result.get("today_after"))
    current_budget = _dict(browser_result.get("current_budget"))
    if not current_budget:
        return False
    return (
        _first_int(today.get("consumed_kcal")) == _first_int(current_budget.get("consumed_kcal"))
        and _first_int(today.get("remaining_kcal")) == _first_int(current_budget.get("remaining_kcal"))
    )


def _browser_meal_list_matches_read_model(browser_result: dict[str, Any]) -> bool:
    today = _dict(browser_result.get("today_after"))
    current_budget = _dict(browser_result.get("current_budget"))
    meal_text = str(today.get("meal_text") or "")
    meals = [_dict(meal) for meal in _list(current_budget.get("meals"))]
    if not meals:
        return "No meals logged for this day." in meal_text
    for meal in meals:
        title = str(meal.get("meal_title") or "").strip()
        kcal = meal.get("total_kcal")
        if title and title not in meal_text:
            return False
        if kcal is not None and str(kcal) not in meal_text:
            return False
    return True


def _browser_macro_visibility_matches_read_model(browser_result: dict[str, Any]) -> bool:
    today = _dict(browser_result.get("today_after"))
    current_budget = _dict(browser_result.get("current_budget"))
    if not current_budget:
        return False
    show_macro = current_budget.get("show_macro") is True
    if show_macro:
        return (
            str(today.get("macro_state") or "") == "visible"
            and _first_int(today.get("protein_g")) == _first_int(current_budget.get("consumed_protein"))
            and _first_int(today.get("carbs_g")) == _first_int(current_budget.get("consumed_carbs"))
            and _first_int(today.get("fat_g")) == _first_int(current_budget.get("consumed_fat"))
        )
    return str(today.get("macro_state") or "") == "guarded"


def _first_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    match = re.search(r"-?\d+", str(value or ""))
    if match is None:
        return None
    return int(match.group(0))


def _browser_no_duplicate_send(browser_result: dict[str, Any]) -> bool:
    messages = _list(_dict(browser_result.get("chat_history")).get("messages"))
    user_messages = [
        str(_dict(message).get("content") or "")
        for message in messages
        if _dict(message).get("role") == "user"
    ]
    return len(user_messages) == len(set(user_messages)) and len(user_messages) >= 2


def _feedback_case_trace(
    *,
    case_id: str,
    response_payload: dict[str, Any],
    elapsed_ms: int,
) -> dict[str, Any]:
    linked_context = _dict(response_payload.get("linked_context"))
    return {
        "case_id": case_id,
        "trace_id": str(linked_context.get("trace_id") or linked_context.get("request_id") or ""),
        "trace_layers": {
            "ui_event_trace": True,
            "feedback_linkage": True,
            "latency_cost_cache_usage": True,
        },
        "runtime": {
            "workflow_effect": "feedback_capture",
            "mutation_allowed": False,
            "feedback_is_product_truth": response_payload.get("product_truth_update_allowed") is True,
            "review_record_created": response_payload.get("status") == "captured",
        },
        "ui": {
            "inline_drawer_available": True,
            "user_enters_trace_id": False,
            "user_enters_request_id": False,
            "draft_survives_navigation": _dict(response_payload.get("ui_event")).get("draft_survives_navigation")
            is True,
        },
        "response": {
            "visible_text": "\u56de\u5831\u5df2\u5132\u5b58",
            "zh_tw_primary": True,
        },
        "latency": {
            "timeout_is_product_target": False,
            "llm_calls": 0,
            "tool_calls": 1,
            "total_ms": elapsed_ms,
        },
        "dogfood_trace": {
            "trace_id": str(linked_context.get("trace_id") or ""),
            "feedback_links_to_trace": linked_context.get("feedback_links_to_trace") is True,
            "feedback_record_id": str(response_payload.get("feedback_id") or ""),
            "feedback_linkage_source": "feedback_record"
            if str(response_payload.get("feedback_id") or "")
            else "missing_feedback_record",
            "auto_attaches_recent_messages": bool(linked_context.get("recent_messages")),
            "auto_attaches_read_model_snapshot": bool(linked_context.get("read_model_snapshot")),
        },
        "fixture_decisions": {
            "intent": False,
            "action": False,
            "attach_target": False,
            "mutation_outcome": False,
            "response_meaning": False,
        },
    }


def _build_case_trace(
    *,
    case_id: str,
    request_trace: dict[str, Any],
    provider_mode: str,
) -> dict[str, Any]:
    direct_trace = _dict(request_trace.get("golden_case_trace_direct"))
    if direct_trace:
        return direct_trace
    case_trace = build_golden_case_trace_from_request_trace(case_id, request_trace)
    if provider_mode.strip().lower() == "scripted":
        case_trace["manager_provider"] = {
            **_dict(case_trace.get("manager_provider")),
            "provider": "deterministic_self_use_manager_fixture",
            "semantic_source": "fixture_provider",
            "live_llm_invoked": False,
        }
    return case_trace


def _seed_case_state(
    SessionLocal: sessionmaker[Session],
    *,
    case: dict[str, Any],
    user_external_id: str,
    local_date: str,
) -> None:
    db = SessionLocal()
    try:
        user = get_or_create_user(db, user_external_id)
        seed_state = _dict(case.get("seed_state"))
        if seed_state.get("body_plan") != "missing":
            bootstrap_body_plan_for_date(
                db,
                user=user,
                inputs=OnboardingBootstrapInput(
                    sex="female",
                    age_years=34,
                    height_cm=170,
                    current_weight_kg=70,
                    goal_type="lose_weight",
                    weekly_target_rate_kg=0.5,
                    timezone="Asia/Taipei",
                    daily_lifestyle="sedentary_with_some_walking",
                    weekly_exercise_days_band="1_2",
                    local_date=local_date,
                ),
            )
        if seed_state.get("recent_meal_thread") in {
            "committed_teppan_or_generic_meal",
            "committed_teppan_combo",
        }:
            _seed_committed_teppan_context_meal(
                db,
                user_id=user.id,
                local_date=local_date,
                source_request_id=f"{case.get('case_id')}-seed-meal",
            )
        if seed_state.get("current_day_meals") == "recent_and_named_slot_meals":
            _seed_recent_and_named_slot_meals(
                db,
                user_id=user.id,
                local_date=local_date,
                source_request_id=f"{case.get('case_id')}-seed-current-day",
            )
        if seed_state.get("current_day_meals") == "two_breakfast_candidates":
            _seed_two_breakfast_candidate_meals(
                db,
                user_id=user.id,
                local_date=local_date,
                source_request_id=f"{case.get('case_id')}-seed-current-day",
            )
        if seed_state.get("recent_trace") == "available":
            _seed_recent_feedback_context(
                db,
                user_id=user.id,
                local_date=local_date,
                trace_id=f"{case.get('case_id')}-recent-trace",
            )
        db.commit()
    finally:
        db.close()


def _seed_committed_teppan_context_meal(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    source_request_id: str,
    occurred_at: datetime | None = None,
) -> None:
    """Seed read-model state only; never decide the Golden case semantics."""

    meal_title = "\u65e9\u9910\u5e97\u9435\u677f\u9eb5\u5957\u9910"
    _seed_committed_context_meal(
        db,
        user_id=user_id,
        local_date=local_date,
        source_request_id=source_request_id,
        meal_title=meal_title,
        raw_input="\u65e9\u9910\u5e97\u9435\u677f\u9eb5\u5957\u9910\uff0c\u542b\u9435\u677f\u9eb5\u3001\u8377\u5305\u86cb\u3001\u8c6c\u8089\u7247",
        total_kcal=620,
        protein_g=24,
        carb_g=70,
        fat_g=22,
        items=[
            {
                "name": "\u9435\u677f\u9eb5",
                "quantity_hint": "1 \u4efd",
                "source": "fooddb",
                "evidence_role": "component",
                "estimate_basis": "fooddb_generic_component",
                "confidence_tier": "medium",
                "estimated_kcal": 420,
                "protein_g": 10,
                "carb_g": 62,
                "fat_g": 14,
                "evidence_ids_json": ["gs-seed-teppan-noodles"],
            },
            {
                "name": "\u8377\u5305\u86cb",
                "quantity_hint": "1 \u9846",
                "source": "fooddb",
                "evidence_role": "component",
                "estimate_basis": "fooddb_component",
                "confidence_tier": "high",
                "estimated_kcal": 90,
                "protein_g": 6,
                "carb_g": 1,
                "fat_g": 7,
                "evidence_ids_json": ["gs-seed-fried-egg"],
            },
            {
                "name": "\u8c6c\u8089\u7247",
                "quantity_hint": "\u5c0f\u4efd",
                "source": "fooddb",
                "evidence_role": "component",
                "estimate_basis": "fooddb_component",
                "confidence_tier": "medium",
                "estimated_kcal": 110,
                "protein_g": 8,
                "carb_g": 7,
                "fat_g": 1,
                "evidence_ids_json": ["gs-seed-pork-slices"],
            },
        ],
        occurred_at=occurred_at,
    )


def _seed_recent_and_named_slot_meals(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    source_request_id: str,
) -> None:
    created_at = utcnow()
    _seed_committed_teppan_context_meal(
        db,
        user_id=user_id,
        local_date=local_date,
        source_request_id=f"{source_request_id}-breakfast",
        occurred_at=created_at - timedelta(hours=4),
    )
    _seed_committed_context_meal(
        db,
        user_id=user_id,
        local_date=local_date,
        source_request_id=f"{source_request_id}-recent",
        meal_title="\u5348\u9910\u96de\u8089\u98ef",
        raw_input="\u5348\u9910\u5403\u96de\u8089\u98ef\u548c\u9752\u83dc",
        total_kcal=560,
        protein_g=28,
        carb_g=72,
        fat_g=14,
        items=[
            {
                "name": "\u96de\u8089\u98ef",
                "quantity_hint": "1 \u7897",
                "source": "fooddb",
                "evidence_role": "component",
                "estimate_basis": "fooddb_generic_component",
                "confidence_tier": "medium",
                "estimated_kcal": 520,
                "protein_g": 26,
                "carb_g": 70,
                "fat_g": 13,
                "evidence_ids_json": ["gs-seed-chicken-rice"],
            },
            {
                "name": "\u9752\u83dc",
                "quantity_hint": "\u5c0f\u4efd",
                "source": "fooddb",
                "evidence_role": "component",
                "estimate_basis": "fooddb_component",
                "confidence_tier": "medium",
                "estimated_kcal": 40,
                "protein_g": 2,
                "carb_g": 2,
                "fat_g": 1,
                "evidence_ids_json": ["gs-seed-greens"],
            },
        ],
        occurred_at=created_at - timedelta(hours=1),
    )


def _seed_two_breakfast_candidate_meals(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    source_request_id: str,
) -> None:
    created_at = utcnow()
    _seed_committed_teppan_context_meal(
        db,
        user_id=user_id,
        local_date=local_date,
        source_request_id=f"{source_request_id}-teppan",
        occurred_at=created_at - timedelta(hours=5),
    )
    _seed_committed_context_meal(
        db,
        user_id=user_id,
        local_date=local_date,
        source_request_id=f"{source_request_id}-riceball",
        meal_title="\u65e9\u9910\u98ef\u7cf0",
        raw_input="\u65e9\u9910\u5403\u98ef\u7cf0\u548c\u8c46\u6f3f",
        total_kcal=430,
        protein_g=13,
        carb_g=65,
        fat_g=12,
        items=[
            {
                "name": "\u98ef\u7cf0",
                "quantity_hint": "1 \u9846",
                "source": "fooddb",
                "evidence_role": "component",
                "estimate_basis": "fooddb_generic_component",
                "confidence_tier": "medium",
                "estimated_kcal": 360,
                "protein_g": 8,
                "carb_g": 60,
                "fat_g": 10,
                "evidence_ids_json": ["gs-seed-riceball"],
            },
            {
                "name": "\u7121\u7cd6\u8c46\u6f3f",
                "quantity_hint": "1 \u676f",
                "source": "fooddb",
                "evidence_role": "component",
                "estimate_basis": "fooddb_component",
                "confidence_tier": "medium",
                "estimated_kcal": 70,
                "protein_g": 5,
                "carb_g": 5,
                "fat_g": 2,
                "evidence_ids_json": ["gs-seed-soymilk"],
            },
        ],
        occurred_at=created_at - timedelta(hours=3),
    )


def _seed_committed_context_meal(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    source_request_id: str,
    meal_title: str,
    raw_input: str,
    total_kcal: int,
    protein_g: int,
    carb_g: int,
    fat_g: int,
    items: list[dict[str, Any]],
    occurred_at: datetime | None = None,
) -> None:
    """Seed committed read-model state only; the Manager still owns all case semantics."""

    created_at = occurred_at or utcnow()
    thread = MealThreadRecord(
        user_id=user_id,
        title=meal_title,
        thread_kind="golden_set_seed",
        active_version_id=None,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(thread)
    db.flush()
    version = MealVersionRecord(
        meal_thread_id=thread.id,
        version_status="active",
        version_reason="golden_set_state_seed",
        reason_payload_json={"fixture_state_only": True, "semantic_authority": False},
        resolution_status="completed_meal",
        meal_title=meal_title,
        raw_input=raw_input,
        source_request_id=source_request_id,
        manager_intent="seeded_prior_committed_meal",
        local_date=local_date,
        occurred_at=created_at,
        total_kcal=total_kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        created_at=created_at,
    )
    db.add(version)
    db.flush()
    thread.active_version_id = version.id
    db.add_all(
        [
            thread,
            *[
                MealItemRecord(
                    meal_version_id=version.id,
                    item_index=index,
                    name=str(item.get("name") or ""),
                    quantity_hint=str(item.get("quantity_hint") or ""),
                    source=str(item.get("source") or "fooddb"),
                    evidence_role=str(item.get("evidence_role") or "component"),
                    estimate_basis=str(item.get("estimate_basis") or "fooddb_component"),
                    confidence_tier=str(item.get("confidence_tier") or "medium"),
                    estimated_kcal=int(item.get("estimated_kcal") or 0),
                    protein_g=int(item.get("protein_g") or 0),
                    carb_g=int(item.get("carb_g") or 0),
                    fat_g=int(item.get("fat_g") or 0),
                    evidence_ids_json=list(_list(item.get("evidence_ids_json"))),
                )
                for index, item in enumerate(items)
            ],
        ]
    )


def _build_test_client(
    SessionLocal: sessionmaker[Session],
    *,
    provider: Any | None,
    feedback_dir: Path | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    token = _local_debug_token()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    previous = (
        intake_routes.manager_provider,
        intake_routes.search_provider,
        intake_routes.extract_provider,
        intake_chat_turn_routes.SessionLocal,
        accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR,
        accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
    )
    if provider is not None:
        intake_routes.manager_provider = provider
        intake_routes.search_provider = None
        intake_routes.extract_provider = None
    intake_chat_turn_routes.SessionLocal = SessionLocal
    if feedback_dir is not None:
        accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR = feedback_dir
        accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = (
            feedback_dir / "review_queue.json"
        )
    os.environ.setdefault("LOCAL_DEBUG_API_TOKEN", token)
    app.state.current_shell_golden_set_restore_runtime = previous
    return TestClient(app)


def _close_test_client(client: TestClient) -> None:
    previous = getattr(client.app.state, "current_shell_golden_set_restore_runtime", None)
    client.close()
    if previous is None:
        return
    (
        intake_routes.manager_provider,
        intake_routes.search_provider,
        intake_routes.extract_provider,
        intake_chat_turn_routes.SessionLocal,
        accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR,
        accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
    ) = previous


def _local_debug_token() -> str:
    token = os.getenv("LOCAL_DEBUG_API_TOKEN", "").strip()
    if token:
        return token
    return "golden-set-local-debug-token"


def _seed_recent_feedback_context(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    trace_id: str,
) -> None:
    runtime_turn_trace = {
        "local_date": local_date,
        "trace_chain": {
            "manager_decision_present": True,
            "evidence_packet_present": True,
            "evidence_requirement_satisfied": True,
            "final_mapping_present": True,
            "state_before_present": True,
            "state_after_present": True,
        },
        "chat_linkage": {
            "user_message_id": "seed-user",
            "assistant_message_id": "seed-assistant",
        },
    }
    created_at = utcnow()
    db.add_all(
        [
            MessageBuffer(
                user_id=user_id,
                role="user",
                content="\u65e9\u9910\u5403\u9435\u677f\u9eb5",
                created_at=created_at - timedelta(minutes=3),
                trace_id=trace_id,
                trace_json={"runtime_turn_trace": runtime_turn_trace},
            ),
            MessageBuffer(
                user_id=user_id,
                role="assistant",
                content="\u5df2\u8a18\u9304\u9019\u7b46\u9910\u9ede\u3002",
                created_at=created_at - timedelta(minutes=2),
                trace_id=trace_id,
                trace_json={"runtime_turn_trace": runtime_turn_trace},
            ),
        ]
    )


def _session_factory(db_path: Path) -> tuple[Any, sessionmaker[Session]]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _provider_for_mode(provider_mode: str) -> Any | None:
    normalized = provider_mode.strip().lower()
    if normalized == "scripted":
        return DeterministicSelfUseManagerProvider()
    if normalized == "configured":
        return None
    raise ValueError(f"unsupported provider_mode: {provider_mode}")


def _select_cases(
    manifest: dict[str, Any],
    case_ids: list[str] | None,
    *,
    suite_scope: str = "core",
) -> list[dict[str, Any]]:
    manifest_cases = _manifest_cases(manifest, suite_scope="all_defined" if case_ids else suite_scope)
    if not case_ids:
        return manifest_cases
    wanted = {case_id.strip() for case_id in case_ids if case_id.strip()}
    selected = [case for case in manifest_cases if str(case.get("case_id") or "") in wanted]
    missing = sorted(wanted - {str(case.get("case_id") or "") for case in selected})
    if missing:
        raise ValueError(f"unknown golden set case id(s): {', '.join(missing)}")
    return selected


def _manifest_cases(manifest: dict[str, Any], *, suite_scope: str = "core") -> list[dict[str, Any]]:
    return [_dict(item) for item in golden_set_cases_for_scope(manifest, suite_scope)]


def _manifest_for_selected_cases(
    manifest: dict[str, Any],
    selected_cases: list[dict[str, Any]],
    *,
    suite_scope: str,
) -> dict[str, Any]:
    selected_ids = {str(case.get("case_id") or "") for case in selected_cases}
    core_cases = [
        _dict(case)
        for case in _list(manifest.get("cases"))
        if str(_dict(case).get("case_id") or "") in selected_ids
    ]
    extension = _dict(manifest.get("websearch_extension"))
    holdout_extension = _dict(manifest.get("holdout_extension"))
    holdout_cases = [
        _dict(case)
        for case in _list(holdout_extension.get("cases"))
        if str(_dict(case).get("case_id") or "") in selected_ids
    ]
    extension_cases = [
        _dict(case)
        for case in _list(extension.get("cases"))
        if str(_dict(case).get("case_id") or "") in selected_ids
    ]
    replay_manifest = {
        **manifest,
        "cases": core_cases,
        "case_count": len(core_cases),
        "selected_suite_scope": suite_scope,
        "suite_inventory": _selected_suite_inventory(
            manifest,
            core_case_count=len(core_cases),
            holdout_case_count=len(holdout_cases),
            websearch_case_count=len(extension_cases),
        ),
    }
    if holdout_extension:
        replay_manifest["holdout_extension"] = {
            **holdout_extension,
            "cases": holdout_cases,
            "case_count": len(holdout_cases),
        }
    if extension:
        replay_manifest["websearch_extension"] = {
            **extension,
            "cases": extension_cases,
            "case_count": len(extension_cases),
        }
    return replay_manifest


def _selected_suite_inventory(
    manifest: dict[str, Any],
    *,
    core_case_count: int,
    holdout_case_count: int,
    websearch_case_count: int,
) -> dict[str, Any]:
    websearch_extension = _dict(manifest.get("websearch_extension"))
    declared = _dict(manifest.get("suite_inventory"))
    return {
        "core_case_count": core_case_count,
        "holdout_case_count": holdout_case_count,
        "websearch_extension_case_count": websearch_case_count,
        "core_closeout_case_count": core_case_count,
        "self_use_closeout_case_count": core_case_count + holdout_case_count,
        "total_defined_case_count": core_case_count + holdout_case_count + websearch_case_count,
        "default_runner_scope": str(declared.get("default_runner_scope") or "core"),
        "default_replay_scope": str(declared.get("default_replay_scope") or "closeout"),
        "websearch_extension_blocking": bool(websearch_extension.get("core_closeout_blocking")),
        "websearch_extension_status": str(websearch_extension.get("status") or ""),
    }


def _script_turns(case: dict[str, Any]) -> list[dict[str, Any]]:
    turns = [_dict(turn) for turn in _list(case.get("script"))]
    if not turns:
        raise ValueError(f"case {case.get('case_id')} has no script turns")
    for turn in turns:
        if not str(turn.get("utterance_zh_tw") or turn.get("utterance") or "").strip():
            raise ValueError(f"case {case.get('case_id')} has an empty turn utterance")
    return turns


def _live_invoked(case_traces: list[dict[str, Any]]) -> bool:
    for case_trace in case_traces:
        manager_provider = _dict(case_trace.get("manager_provider"))
        if manager_provider.get("live_llm_invoked") is True:
            return True
    return False


def _response_json(response: Any) -> dict[str, Any]:
    try:
        loaded = response.json()
    except Exception:
        return {}
    return _dict(loaded)


def _read_manifest(path: Path) -> dict[str, Any]:
    if path == DEFAULT_MANIFEST_PATH:
        return load_golden_set_manifest(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return _dict(loaded)


def _read_json(path: Path) -> dict[str, Any]:
    return _dict(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Current Shell self-use Golden Set cases through the real /estimate entrypoint."
    )
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--trace-artifact", default=str(DEFAULT_TRACE_ARTIFACT_PATH))
    parser.add_argument("--replay-output", default=str(DEFAULT_REPLAY_OUTPUT_PATH))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--provider-mode", choices=("configured", "scripted"), default="configured")
    parser.add_argument("--entrypoint-mode", choices=("estimate", "browser"), default="estimate")
    parser.add_argument("--suite-scope", choices=("core", "holdout", "closeout", "websearch", "all_defined"), default="core")
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--allow-search", action="store_true")
    args = parser.parse_args(argv)
    report = build_current_shell_golden_set_e2e_report(
        case_ids=list(args.case_id),
        db_path=Path(args.db_path),
        output_path=Path(args.output),
        trace_artifact_path=Path(args.trace_artifact),
        replay_output_path=Path(args.replay_output),
        manifest_path=Path(args.manifest),
        provider_mode=str(args.provider_mode),
        entrypoint_mode=str(args.entrypoint_mode),
        suite_scope=str(args.suite_scope),
        local_date=str(args.local_date),
        allow_search=bool(args.allow_search),
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "trace_artifact": str(Path(args.trace_artifact)),
                "replay_output": str(Path(args.replay_output)),
                "provider_mode": report["provider_mode"],
                "entrypoint_mode": report["entrypoint_mode"],
                "live_invoked_by_runner": report["live_invoked_by_runner"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["summary"]["strict_golden_set_replay_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
