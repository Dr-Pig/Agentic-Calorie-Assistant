from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_accurate_intake_local_web_shell_smoke import (  # noqa: E402
    _build_test_client,
    _close_test_client,
    _json,
    _seed_body_plan,
    _session_factory,
    _status,
)
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider  # noqa: E402

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_chat_history_reload_gate.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_chat_history_reload_gate.json"
DEFAULT_CJK_MESSAGE = "早餐吃茶葉蛋和拿鐵"
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


def _message_contents(payload: dict[str, Any]) -> list[str]:
    return [str(message.get("content") or "") for message in payload.get("messages", []) if isinstance(message, dict)]


def _history_summary(payload: dict[str, Any]) -> dict[str, Any]:
    messages = [message for message in payload.get("messages", []) if isinstance(message, dict)]
    context_versions = [
        str(message.get("context_policy_version"))
        for message in messages
        if message.get("context_policy_version")
    ]
    target_candidate_counts = [
        int(message.get("target_candidate_count") or 0)
        for message in messages
        if isinstance(message.get("target_candidate_count"), int)
    ]
    return {
        "source": payload.get("source"),
        "frontend_semantic_owner": payload.get("frontend_semantic_owner"),
        "scope": payload.get("scope"),
        "long_term_memory_used": payload.get("long_term_memory_used"),
        "proactive_or_rescue_used": payload.get("proactive_or_rescue_used"),
        "message_count": payload.get("message_count"),
        "message_contents": _message_contents(payload),
        "runtime_turn_trace_present": any(message.get("runtime_turn_trace_present") is True for message in messages),
        "context_snapshot_present": any(message.get("context_snapshot_present") is True for message in messages),
        "trace_chain_complete": any(message.get("trace_chain_complete") is True for message in messages),
        "context_policy_version": context_versions[-1] if context_versions else None,
        "loaded_context_summary_present": any(
            isinstance(message.get("loaded_context_summary"), dict) for message in messages
        ),
        "omitted_context_summary_present": any(
            isinstance(message.get("omitted_context_summary"), dict) for message in messages
        ),
        "pending_pins_present": any(message.get("pending_pins_present") is True for message in messages),
        "target_candidate_count": max(target_candidate_counts) if target_candidate_counts else 0,
        "message_local_dates": sorted({str(message.get("local_date")) for message in messages if message.get("local_date")}),
        "mutation_authority": any(message.get("mutation_authority") is True for message in messages),
    }


def _debug_summary(payload: dict[str, Any]) -> dict[str, Any]:
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    same_truth = model.get("same_truth") if isinstance(model.get("same_truth"), dict) else {}
    today_summary = model.get("today_summary") if isinstance(model.get("today_summary"), dict) else {}
    return {
        "status_code_ok": True,
        "read_only": payload.get("read_only"),
        "local_date": payload.get("local_date"),
        "same_truth_status": same_truth.get("status"),
        "consumed_kcal": today_summary.get("consumed_kcal"),
    }


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    before = dict(report.get("before_reload") or {})
    after = dict(report.get("after_reload") or {})
    after_history = dict(after.get("chat_history") or {})
    before_history = dict(before.get("chat_history") or {})
    after_debug = dict(after.get("debug") or {})
    after_budget = dict(after.get("today_budget") or {})
    before_budget = dict(before.get("today_budget") or {})

    if before_history.get("message_count", 0) < 2:
        blockers.append("before_reload_history_missing_messages")
    if after_history.get("message_count") != before_history.get("message_count"):
        blockers.append("reload_history_message_count_changed")
    if after_history.get("source") != "sqlite_message_buffer":
        blockers.append("reload_history_not_sqlite_backed")
    if after_history.get("frontend_semantic_owner") is not False:
        blockers.append("reload_history_frontend_semantic_owner")
    if after_history.get("long_term_memory_used") is not False:
        blockers.append("reload_history_long_term_memory_used")
    if after_history.get("proactive_or_rescue_used") is not False:
        blockers.append("reload_history_proactive_or_rescue_used")
    if after_history.get("mutation_authority") is not False:
        blockers.append("reload_history_claimed_mutation_authority")
    if report["cjk_message"] not in after_history.get("message_contents", []):
        blockers.append("cjk_user_message_missing_after_reload")
    if not any(report["cjk_message"] in content for content in after_history.get("message_contents", [])):
        blockers.append("cjk_text_not_preserved_after_reload")
    if after_history.get("runtime_turn_trace_present") is not True:
        blockers.append("reload_history_missing_runtime_turn_trace")
    if after_history.get("context_snapshot_present") is not True:
        blockers.append("reload_history_missing_context_snapshot")
    if after_history.get("trace_chain_complete") is not True:
        blockers.append("reload_history_trace_chain_incomplete")
    if after_history.get("message_local_dates") != [report.get("backend_local_date")]:
        blockers.append("reload_history_date_scope_mismatch")
    if after_debug.get("read_only") is not True:
        blockers.append("debug_surface_not_read_only_after_reload")
    if after_debug.get("same_truth_status") != "pass":
        blockers.append("same_truth_not_pass_after_reload")
    if before_budget.get("consumed_kcal", 0) <= 0:
        blockers.append("before_reload_budget_not_updated")
    if after_budget.get("consumed_kcal") != before_budget.get("consumed_kcal"):
        blockers.append("reload_budget_consumed_changed")
    if report.get("reload_manager_provider_call_count") != 0:
        blockers.append("reload_read_invoked_manager_provider")
    return ("pass" if not blockers else "fail"), blockers


def build_chat_history_reload_gate_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    user_external_id: str = "chat-history-reload-user",
    cjk_message: str = DEFAULT_CJK_MESSAGE,
    reset_db: bool = True,
) -> dict[str, Any]:
    if reset_db and db_path.exists():
        db_path.unlink()

    initial_engine, InitialSession = _session_factory(db_path)
    initial_provider = DeterministicSelfUseManagerProvider()
    initial_db = InitialSession()
    initial_client = _build_test_client(initial_db, initial_provider)
    try:
        initial_budget_response = initial_client.get("/today/current-budget", params={"user_id": user_external_id})
        initial_budget = _json(initial_budget_response)
        backend_local_date = str(initial_budget.get("local_date") or "")
        if backend_local_date:
            _seed_body_plan(initial_db, user_external_id=user_external_id, local_date=backend_local_date)
        static_response = initial_client.get("/static/accurate-intake-local-shell.html")
        estimate_response = initial_client.post(
            "/estimate",
            json={"text": cjk_message, "user_id": user_external_id, "allow_search": False},
            headers={"X-Canary-Page-Version": "accurate-intake-local-shell.v1"},
        )
        before_budget_response = initial_client.get("/today/current-budget", params={"user_id": user_external_id})
        before_history_response = initial_client.get(
            "/accurate-intake/chat-history",
            params={"user_id": user_external_id, "local_date": backend_local_date},
        )
        before_budget = _json(before_budget_response)
        before_history = _json(before_history_response)
    finally:
        _close_test_client(initial_client)
        initial_db.close()
        initial_engine.dispose()

    reload_engine, ReloadSession = _session_factory(db_path)
    reload_provider = DeterministicSelfUseManagerProvider()
    reload_db = ReloadSession()
    reload_client = _build_test_client(reload_db, reload_provider)
    try:
        after_budget_response = reload_client.get("/today/current-budget", params={"user_id": user_external_id})
        after_debug_response = reload_client.get(
            "/accurate-intake/debug",
            params={"user_id": user_external_id, "local_date": backend_local_date},
        )
        after_history_response = reload_client.get(
            "/accurate-intake/chat-history",
            params={"user_id": user_external_id, "local_date": backend_local_date},
        )
        after_budget = _json(after_budget_response)
        after_debug = _json(after_debug_response)
        after_history = _json(after_history_response)
    finally:
        _close_test_client(reload_client)
        reload_db.close()
        reload_engine.dispose()

    report: dict[str, Any] = {
        "artifact_schema_version": "1.0",
        "gate_id": "accurate_intake_chat_history_reload_gate_v1",
        "claim_scope": "local_deterministic_chat_history_reload_gate",
        "evidence_scope": "sqlite_reload_read_model_and_trace_linkage",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "db_path": str(db_path),
        "user_external_id": user_external_id,
        "cjk_message": cjk_message,
        "backend_local_date": backend_local_date,
        "browser_executed": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "product_readiness_claimed": False,
        "static_shell": {
            **_status(static_response),
            "contains_chat_history_endpoint": 'data-chat-history-endpoint="/accurate-intake/chat-history"'
            in static_response.text,
            "contains_frontend_non_owner_marker": 'data-frontend-semantic-owner="false"' in static_response.text,
        },
        "estimate": {
            **_status(estimate_response),
            "has_payload": bool(_json(estimate_response).get("payload")),
        },
        "before_reload": {
            "today_budget": {
                **_status(before_budget_response),
                "local_date": before_budget.get("local_date"),
                "consumed_kcal": before_budget.get("consumed_kcal"),
                "remaining_kcal": before_budget.get("remaining_kcal"),
            },
            "chat_history": _history_summary(before_history),
        },
        "after_reload": {
            "today_budget": {
                **_status(after_budget_response),
                "local_date": after_budget.get("local_date"),
                "consumed_kcal": after_budget.get("consumed_kcal"),
                "remaining_kcal": after_budget.get("remaining_kcal"),
            },
            "debug": _debug_summary(after_debug),
            "chat_history": _history_summary(after_history),
        },
        "initial_manager_provider_call_count": len(initial_provider.calls),
        "reload_manager_provider_call_count": len(reload_provider.calls),
    }
    status, blockers = _validate(report)
    report["status"] = status
    report["blockers"] = blockers
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake chat history reload gate.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default="chat-history-reload-user")
    parser.add_argument("--cjk-message", default=DEFAULT_CJK_MESSAGE)
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args(argv)

    report = build_chat_history_reload_gate_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        cjk_message=args.cjk_message,
        reset_db=not args.keep_db,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
