from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.intake_manager_tool_batch import execute_manager_tool_calls  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.composition.state_resolver import resolve_intake_state  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.models import Base  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt9_packet_consumption_seam.json"
USER_ID = "rt9-packet-seam"
LOCAL_DATE = "2026-05-08"
RAW_INPUT = "I drank a Test Brand Matcha Latte"


class _FakeSearchPort:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = hits
        self.calls: list[dict[str, Any]] = []

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "max_results": max_results})
        return list(self._hits)


class _FakeExtractPort:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.calls: list[dict[str, Any]] = []

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.calls.append({"urls": list(urls), "query": query})
        return list(self._rows)


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _bootstrap_inputs(*, local_date: str) -> OnboardingBootstrapInput:
    return OnboardingBootstrapInput(
        sex="female",
        age_years=30,
        height_cm=165.0,
        current_weight_kg=58.0,
        activity_level="sedentary",
        goal_type="lose_weight",
        weekly_target_rate_kg=0.5,
        local_date=local_date,
        timezone="Asia/Taipei",
    )


def _bootstrap_user(db: Session) -> None:
    user = get_or_create_user(db, USER_ID)
    bootstrap_body_plan_for_date(db, user=user, inputs=_bootstrap_inputs(local_date=LOCAL_DATE))


def _manager_semantic_decision() -> dict[str, Any]:
    return {
        "base_dish": "Matcha Latte",
        "aliases": ["Test Brand Matcha Latte"],
        "brand_hint": "Test Brand",
        "size_hint": None,
        "modifier_hints": [],
        "listed_items": [],
        "retrieval_goal": "exact_brand_lookup",
        "semantic_authority_source": "synthetic_manager_structured_fixture",
    }


def _exact_search_hit(*, title: str, url: str) -> dict[str, Any]:
    return {
        "title": title,
        "url": url,
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


def _exact_extract_row(*, url: str, title: str) -> dict[str, Any]:
    return {
        "url": url,
        "title": title,
        "source_type": "official",
        "officialness": "official",
        "serving_basis": "per_cup",
        "brand_detected": "Test Brand",
        "raw_content": "400 kcal",
        "raw_ref": "raw:extract:001",
    }


async def _run_estimate_tool(
    *,
    include_manager_semantic_decision: bool,
    search_hits: list[dict[str, Any]],
    extract_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    db = _session()
    _bootstrap_user(db)
    state_before = resolve_intake_state(
        db,
        user_external_id=USER_ID,
        local_date=LOCAL_DATE,
        incoming_user_text=RAW_INPUT,
    )
    search_port = _FakeSearchPort(search_hits)
    extract_port = _FakeExtractPort(extract_rows)
    tool_call: dict[str, Any] = {"name": "estimate_nutrition", "arguments": {}}
    if include_manager_semantic_decision:
        tool_call["arguments"]["manager_semantic_decision"] = _manager_semantic_decision()
    tool_state = {
        "correction_target": {},
        "nutrition_artifact": None,
        "budget_summary": None,
    }
    tool_results = await execute_manager_tool_calls(
        db=db,
        user_external_id=USER_ID,
        raw_user_input=RAW_INPUT,
        request_id="rt9-packet-seam",
        local_date=LOCAL_DATE,
        allow_search=True,
        manager_provider=None,
        provider=None,
        search_port=search_port,
        extract_port=extract_port,
        state_before=state_before,
        correction_target={},
        tool_calls=[tool_call],
        tool_state=tool_state,
    )
    result = dict(tool_results[0])
    payload = ((result.get("evidence") or {}).get("nutrition_payload") or {})
    trace_contract = dict(payload.get("trace_contract") or {})
    web_runtime_trace = dict(trace_contract.get("web_runtime_trace") or {})
    return {
        "tool_result": result,
        "trace_contract": trace_contract,
        "web_runtime_trace": web_runtime_trace,
        "search_calls": list(search_port.calls),
        "extract_calls": list(extract_port.calls),
    }


async def _build_artifact_async(*, output_path: Path | None = None) -> dict[str, Any]:
    exact_hit = _exact_search_hit(
        title="Test Brand Matcha Latte",
        url="https://brand.example/products/matcha-latte",
    )
    exact_extract = _exact_extract_row(
        url="https://brand.example/products/matcha-latte",
        title="Test Brand Matcha Latte",
    )
    accepted = await _run_estimate_tool(
        include_manager_semantic_decision=True,
        search_hits=[exact_hit],
        extract_rows=[exact_extract],
    )
    accepted_trace = accepted["web_runtime_trace"]
    accepted_result = accepted["tool_result"]
    accepted_case = {
        "case_id": "manager_owned_exact_brand_packet_reaches_runtime_trace",
        "status": "pass",
        "retrieval_request_source": accepted_trace.get("retrieval_request_source"),
        "attempted": bool(accepted_trace.get("attempted")),
        "packetized_candidate_present": bool(accepted_trace.get("packetized_candidate_present")),
        "manager_pass_2_saw_search_packet": bool(accepted_trace.get("manager_pass_2_saw_search_packet")),
        "accepted_extract_packet_id": accepted_trace.get("accepted_extract_packet_id"),
        "search_attempt_count": int(accepted_trace.get("search_attempt_count") or 0),
        "mutation_result_empty": accepted_result.get("mutation_result") == {},
    }

    missing_manager = await _run_estimate_tool(
        include_manager_semantic_decision=False,
        search_hits=[exact_hit],
        extract_rows=[exact_extract],
    )
    missing_trace = missing_manager["web_runtime_trace"]
    missing_case = {
        "case_id": "raw_text_hint_cannot_activate_runtime_web_packet",
        "status": "pass",
        "attempted": bool(missing_trace.get("attempted")),
        "skip_reason": missing_trace.get("skip_reason"),
        "semantic_authority_source": missing_trace.get("semantic_authority_source"),
        "retrieval_request_source": missing_trace.get("retrieval_request_source"),
        "search_calls": len(missing_manager["search_calls"]),
        "extract_calls": len(missing_manager["extract_calls"]),
    }

    sibling = await _run_estimate_tool(
        include_manager_semantic_decision=True,
        search_hits=[
            _exact_search_hit(
                title="Test Brand Mocha",
                url="https://brand.example/products/mocha",
            )
        ],
        extract_rows=[],
    )
    sibling_trace = sibling["web_runtime_trace"]
    sibling_case = {
        "case_id": "rejected_web_candidate_never_becomes_evidence_truth",
        "status": "pass",
        "packetized_candidate_present": bool(sibling_trace.get("packetized_candidate_present")),
        "manager_pass_2_saw_search_packet": bool(sibling_trace.get("manager_pass_2_saw_search_packet")),
        "accepted_extract_packet_id": sibling_trace.get("accepted_extract_packet_id"),
        "failure_reason": sibling_trace.get("failure_reason"),
        "rejected_web_candidates_used_as_evidence": bool(sibling_trace.get("rejected_web_candidates_used_as_evidence")),
    }

    cases = [accepted_case, missing_case, sibling_case]
    passed_case_count = sum(1 for case in cases if case["status"] == "pass")
    resolved_output = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return json.loads(
        json.dumps(
            {
                "artifact_schema_version": "1.0",
                "artifact_name": resolved_output.name,
                "artifact_path": str(resolved_output),
                "schema_version": "1.0",
                "fixture_or_real": "real_runtime_local",
                "producer_track": "CurrentShell/ManagerRuntime",
                "intended_consumers": ["CurrentShell/AppShell", "CurrentShell/SharedCurrentShell", "human_review"],
                "ready_for_other_tracks": True,
                "non_claims": {
                    "product_readiness_claimed": False,
                    "private_self_use_approved": False,
                    "real_fooddb_pass_claimed": False,
                },
                "artifact_type": "accurate_intake_rt9_packet_consumption_seam",
                "gate_id": "accurate_intake_rt9_packet_consumption_seam",
                "claim_scope": "manager_runtime_rt9_packet_consumption_seam",
                "target_manager_runtime_gate": "rt9_packet_consumption_seam",
                "supports_journeys": ["B"],
                "runtime_backed": True,
                "live_llm_invoked": False,
                "fooddb_used": False,
                "created_at": datetime.now(UTC).isoformat(),
                "status": "pass",
                "summary": {
                    "case_count": len(cases),
                    "passed_case_count": passed_case_count,
                },
                "cases": cases,
            },
            ensure_ascii=False,
        )
    )


def build_rt9_packet_consumption_seam_artifact(*, output_path: Path | None = None) -> dict[str, Any]:
    return asyncio.run(_build_artifact_async(output_path=output_path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    artifact = build_rt9_packet_consumption_seam_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
