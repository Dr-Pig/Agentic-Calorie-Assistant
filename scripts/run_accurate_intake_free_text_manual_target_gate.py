from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import secrets
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_free_text_manual_target_gate.json"


class _ManualTargetFixtureProvider:
    def __init__(self, target_kcal: int | None) -> None:
        self.target_kcal = target_kcal
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "manual_target_fixture", "live_llm_invoked": False}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "raw_user_input": user_payload.get("raw_user_input"),
                "available_tools": list(user_payload.get("available_tools") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        target_attachment: dict[str, Any] = {"mode": "manual_daily_target"}
        answer_contract: dict[str, Any] = {"reply_text": "manual target update requested"}
        semantic_decision: dict[str, Any] = {
            "semantic_authority": "deterministic_fake_provider",
            "current_turn_intent": "set_manual_daily_target",
            "target_attachment": dict(target_attachment),
            "workflow_effect": "manual_daily_target_update",
            "final_action_candidate": "target_updated",
            "estimation_posture": "not_applicable",
            "followup_posture": "none",
            "followup_targets": [],
            "mutation_intent_candidate": "budget_target_write",
            "uncertainty_posture": "bounded",
            "source": "manual_target_fixture",
            "semantic_owner": "manager",
            "deterministic_role": "fixture_simulates_manager_output_only",
        }
        if self.target_kcal is not None:
            target_attachment["daily_target_kcal"] = self.target_kcal
            answer_contract["daily_target_kcal"] = self.target_kcal
            semantic_decision["target_attachment"] = dict(target_attachment)
            semantic_decision["daily_target_kcal"] = self.target_kcal
        return (
            {
                "manager_action": "final",
                "intent": "set_manual_daily_target",
                "intent_type": "set_manual_daily_target",
                "final_action": "target_updated",
                "workflow_effect": "manual_daily_target_update",
                "target_attachment": target_attachment,
                "exactness": "deterministic_fixture",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": answer_contract,
                "response_summary": "manual_daily_target_update",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "not_applicable",
                "semantic_decision": semantic_decision,
                "tool_calls": [],
            },
            {"source": "manual_target_fixture", "live_llm_invoked": False},
        )


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _client(db: Session, provider: _ManualTargetFixtureProvider) -> TestClient:
    previous_manager = intake_routes.manager_provider
    previous_search = intake_routes.search_provider
    previous_extract = intake_routes.extract_provider
    intake_routes.manager_provider = provider
    intake_routes.search_provider = None
    intake_routes.extract_provider = None

    app = FastAPI()
    app.include_router(router)

    def override_get_db() -> Any:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client._accurate_intake_previous_providers = (  # type: ignore[attr-defined]
        previous_manager,
        previous_search,
        previous_extract,
    )
    return client


def _close_client(client: TestClient) -> None:
    previous_manager, previous_search, previous_extract = client._accurate_intake_previous_providers  # type: ignore[attr-defined]
    intake_routes.manager_provider = previous_manager
    intake_routes.search_provider = previous_search
    intake_routes.extract_provider = previous_extract
    client.close()


def _json(response: Any) -> dict[str, Any]:
    payload = response.json()
    return dict(payload) if isinstance(payload, dict) else {}


def _run_case(*, target_kcal: int | None, user_id: str, text: str) -> dict[str, Any]:
    db = _session()
    provider = _ManualTargetFixtureProvider(target_kcal)
    client = _client(db, provider)
    try:
        debug_token = secrets.token_urlsafe(24)
        response = client.post(
            "/estimate",
            json={"text": text, "allow_search": False, "user_id": user_id},
            headers={"X-Local-Debug-Token": debug_token},
        )
        payload = _json(response)
        response_payload = dict(payload.get("payload") or {})
        today = client.get("/today/current-budget", params={"user_id": user_id})
        return {
            "status_code": response.status_code,
            "coach_message": payload.get("coach_message"),
            "payload": response_payload,
            "today": _json(today),
            "provider_calls": list(provider.calls),
        }
    finally:
        _close_client(client)
        db.close()


def build_free_text_manual_target_gate_artifact() -> dict[str, Any]:
    updated = _run_case(
        target_kcal=1600,
        user_id="free-text-target-gate-user",
        text="set today's daily target to 1600",
    )
    unsafe = _run_case(
        target_kcal=300,
        user_id="unsafe-target-gate-user",
        text="set today's daily target to 300",
    )
    ambiguous = _run_case(
        target_kcal=None,
        user_id="ambiguous-target-gate-user",
        text="change today's daily target",
    )

    updated_payload = dict(updated.get("payload") or {})
    unsafe_payload = dict(unsafe.get("payload") or {})
    ambiguous_payload = dict(ambiguous.get("payload") or {})
    updated_delta = dict(updated_payload.get("state_delta") or {})
    unsafe_delta = dict(unsafe_payload.get("state_delta") or {})
    ambiguous_delta = dict(ambiguous_payload.get("state_delta") or {})
    updated_budget = dict(updated_payload.get("remaining_budget") or {})

    blockers: list[str] = []
    if updated.get("status_code") != 200:
        blockers.append("manual_target_update_route_failed")
    if unsafe.get("status_code") != 200:
        blockers.append("unsafe_target_route_failed")
    if ambiguous.get("status_code") != 200:
        blockers.append("ambiguous_target_route_failed")
    if updated_delta.get("manual_daily_target_updated") is not True:
        blockers.append("manual_target_not_updated")
    if updated_budget.get("daily_target_kcal") != 1600:
        blockers.append("manual_target_budget_not_rendered")
    if unsafe_delta.get("manual_daily_target_blocked") is not True:
        blockers.append("unsafe_target_not_blocked")
    if ambiguous_delta.get("manual_daily_target_blocked") is not True:
        blockers.append("ambiguous_target_not_blocked")
    for case_id, delta in (
        ("updated", updated_delta),
        ("unsafe", unsafe_delta),
        ("ambiguous", ambiguous_delta),
    ):
        if delta.get("meal_logged") is not False:
            blockers.append(f"{case_id}_meal_logged")
        if delta.get("canonical_commit") is not False:
            blockers.append(f"{case_id}_canonical_commit")
    if not any("body.get_active_plan" in call.get("available_tools", []) for call in updated["provider_calls"]):
        blockers.append("manager_provider_did_not_receive_active_plan_tool")

    return {
        "artifact_schema_version": "1.0",
        "gate_id": "accurate_intake_free_text_manual_target_gate",
        "claim_scope": "free_text_manual_target_manager_path_gate",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "blockers": blockers,
        "manual_target_updated": updated_delta.get("manual_daily_target_updated") is True,
        "unsafe_target_blocked": unsafe_delta.get("manual_daily_target_blocked") is True,
        "ambiguous_target_blocked": ambiguous_delta.get("manual_daily_target_blocked") is True,
        "meal_mutation_performed": any(
            dict(payload.get("state_delta") or {}).get("meal_logged") is True
            for payload in (updated_payload, unsafe_payload, ambiguous_payload)
        ),
        "canonical_commit_performed": any(
            dict(payload.get("state_delta") or {}).get("canonical_commit") is True
            for payload in (updated_payload, unsafe_payload, ambiguous_payload)
        ),
        "manager_fixture_used": True,
        "semantic_owner": "fixture_manager_structured_decision",
        "deterministic_role": "validate_manager_decision_and_apply_existing_target_service",
        "frontend_semantic_owner": False,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_packet_schema_changed": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
        "fooddb_truth_updated": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "case_summaries": {
            "updated": {
                "target_kcal": updated_budget.get("daily_target_kcal"),
                "remaining_kcal": updated_budget.get("remaining_kcal"),
                "provider_call_count": len(updated["provider_calls"]),
            },
            "unsafe": {"blocked": unsafe_delta.get("manual_daily_target_blocked") is True},
            "ambiguous": {"blocked": ambiguous_delta.get("manual_daily_target_blocked") is True},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the free-text manual target Manager path gate without live providers."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_free_text_manual_target_gate_artifact()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "manual_target_updated": artifact["manual_target_updated"],
                "unsafe_target_blocked": artifact["unsafe_target_blocked"],
                "ambiguous_target_blocked": artifact["ambiguous_target_blocked"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
