from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.database import get_db, get_or_create_user  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.budget.interface.today_surface import resolve_today_local_date  # noqa: E402
from scripts.run_accurate_intake_browser_shell_smoke import (  # noqa: E402
    BrowserSmokeDependencyMissing,
    _install_fetch_recorder,
    _load_sync_playwright,
    _parse_json_object,
)

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_browser_realistic_web_dogfood_v2.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_browser_realistic_web_dogfood_v2.json"
USER_EXTERNAL_ID = "browser-realistic-v2"
LOCAL_DATE = resolve_today_local_date(None)
DIAGNOSTIC_STATUS_WITH_FIXTURE_GAP = "browser_diagnostic_pass_with_fixture_evidence_gap"
DIAGNOSTIC_STATUS_WITH_EVIDENCE_GAP = "browser_diagnostic_pass_with_evidence_gap"
FORBIDDEN_SUCCESS_STATUSES = {"pass", "dogfood_pass", "realistic_pass", "fooddb_pass"}
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
    "real_fooddb_dogfood_pass",
]
REQUIRED_FETCH_METHODS = {
    "/today/current-budget": "GET",
    "/body-plan/active": "GET",
    "/body-plan/manual-daily-target": "POST",
    "/accurate-intake/debug": "GET",
    "/accurate-intake/chat-history": "GET",
    "/estimate": "POST",
}
FIRST_PASS_READ_TOOL_MARKERS = {
    "budget.get_today_summary",
    "body.get_active_plan",
    "read_day_budget",
    "read_body_plan",
}
TURN_FIXTURES = [
    {
        "turn_id": "breakfast_001",
        "raw_user_input": "\u65e9\u9910\u5403\u8336\u8449\u86cb\u548c\u62ff\u9435",
        "intent_type": "log_meal",
        "workflow_effect": "route_to_intake",
        "final_action": "commit",
        "mutation_intent_candidate": "canonical_write",
        "target_attachment": {"mode": "new_meal"},
    },
    {
        "turn_id": "lunch_001",
        "raw_user_input": "\u5348\u9910\u5403\u96de\u8089\u4fbf\u7576\u98ef\u5c11\u4e00\u9ede",
        "intent_type": "log_meal",
        "workflow_effect": "route_to_intake",
        "final_action": "commit",
        "mutation_intent_candidate": "canonical_write",
        "target_attachment": {"mode": "new_meal"},
    },
    {
        "turn_id": "dinner_draft_001",
        "raw_user_input": "\u665a\u9910\u5403\u6ef7\u5473",
        "intent_type": "log_meal",
        "workflow_effect": "draft_clarify_no_mutation",
        "final_action": "ask_items",
        "mutation_intent_candidate": "no_mutation",
        "target_attachment": {"mode": "pending_draft", "canonical_name": "\u6ef7\u5473"},
    },
    {
        "turn_id": "dinner_basket_001",
        "raw_user_input": "\u6709\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",
        "intent_type": "log_meal",
        "workflow_effect": "listed_basket_commit",
        "final_action": "commit",
        "mutation_intent_candidate": "canonical_write",
        "target_attachment": {"mode": "draft_followup", "canonical_name": "\u6ef7\u5473"},
    },
    {
        "turn_id": "dinner_remove_001",
        "raw_user_input": "\u628a\u8ca2\u4e38\u62ff\u6389",
        "intent_type": "log_meal",
        "workflow_effect": "correction_remove_item",
        "final_action": "correction_applied",
        "mutation_intent_candidate": "correction_write",
        "target_attachment": {"mode": "explicit_item_target", "canonical_name": "\u8ca2\u4e38"},
    },
    {
        "turn_id": "query_001",
        "raw_user_input": "\u4eca\u5929\u5403\u4e86\u591a\u5c11\uff1f\u9084\u5269\u591a\u5c11\uff1f",
        "intent_type": "answer_remaining_budget",
        "workflow_effect": "answer_only",
        "final_action": "answer_only",
        "mutation_intent_candidate": "no_mutation",
        "target_attachment": {"mode": "none"},
    },
]
EXPECTED_TURN_DECISIONS = {
    str(turn["turn_id"]): {
        "intent_type": turn["intent_type"],
        "workflow_effect": turn["workflow_effect"],
        "final_action": turn["final_action"],
        "mutation_intent_candidate": turn["mutation_intent_candidate"],
        "target_attachment": turn["target_attachment"],
    }
    for turn in TURN_FIXTURES
}
REQUIRED_TURN_IDS = tuple(str(turn["turn_id"]) for turn in TURN_FIXTURES)
REQUIRED_RELOAD_SURFACE_FLAGS = (
    "today_summary_rendered",
    "debug_surface_rendered",
    "runtime_status_surface_rendered",
    "meal_threads_rendered",
    "backend_local_date_rendered",
)


def _session_factory(db_path: Path) -> tuple[Any, sessionmaker[Session]]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _seed_body_plan(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
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


class _BrowserRealisticManagerProvider:
    def __init__(self) -> None:
        self.turn_index = 0
        self.active_turn: dict[str, Any] = {}
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "browser_realistic_manager_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        available_tools = {str(item) for item in list(user_payload.get("available_tools") or [])}
        round_index = int(user_payload.get("round_index") or 0)
        raw_user_input = str(user_payload.get("raw_user_input") or "")
        if FIRST_PASS_READ_TOOL_MARKERS.intersection(available_tools):
            self.active_turn = dict(TURN_FIXTURES[min(self.turn_index, len(TURN_FIXTURES) - 1)])
            self.turn_index += 1
        turn = dict(self.active_turn or TURN_FIXTURES[min(self.turn_index, len(TURN_FIXTURES) - 1)])
        self.calls.append(
            {
                "turn_id": turn["turn_id"],
                "raw_user_input_recorded_only": raw_user_input,
                "available_tools": sorted(available_tools),
                "round_index": round_index,
            }
        )
        if turn["intent_type"] == "log_meal" and "estimate_nutrition" in available_tools and round_index == 0:
            return {"manager_action": "call_tools", "tool_calls": [{"name": "estimate_nutrition"}]}, self._trace(turn)
        return self._final(turn), self._trace(turn)

    def _trace(self, turn: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "browser_realistic_manager_fixture",
            "turn_id": turn["turn_id"],
            "live_llm_invoked": False,
            "raw_user_input_used_for_fixture_selection": False,
        }

    def _final(self, turn: dict[str, Any]) -> dict[str, Any]:
        target_attachment = dict(turn["target_attachment"])
        return {
            "manager_action": "final",
            "intent": turn["intent_type"],
            "intent_type": turn["intent_type"],
            "workflow_effect": turn["workflow_effect"],
            "final_action": turn["final_action"],
            "target_attachment": target_attachment,
            "exactness": "deterministic_fixture",
            "confidence": "medium",
            "evidence_posture": "fixture_only",
            "repair_ack": False,
            "answer_contract": {"reply_text": turn["workflow_effect"]},
            "response_summary": turn["workflow_effect"],
            "semantic_decision": {
                "semantic_authority": "deterministic_fake_provider",
                "current_turn_intent": turn["intent_type"],
                "target_attachment": target_attachment,
                "workflow_effect": turn["workflow_effect"],
                "final_action_candidate": turn["final_action"],
                "mutation_intent_candidate": turn["mutation_intent_candidate"],
                "uncertainty_posture": "bounded",
                "source": "browser_realistic_manager_fixture",
                "semantic_owner": "manager",
                "deterministic_role": "fixture_simulates_manager_output_only",
            },
        }


def _build_app(db: Session, provider: _BrowserRealisticManagerProvider) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    previous = (intake_routes.manager_provider, intake_routes.search_provider, intake_routes.extract_provider)
    intake_routes.manager_provider = provider
    intake_routes.search_provider = None
    intake_routes.extract_provider = None
    app.state.accurate_intake_restore_runtime = previous
    return app


def _restore_runtime(app: FastAPI) -> None:
    previous = getattr(app.state, "accurate_intake_restore_runtime", None)
    if previous is not None:
        intake_routes.manager_provider, intake_routes.search_provider, intake_routes.extract_provider = previous


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - depends on server startup timing
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"server_not_ready: {last_error}")


def _run_uvicorn_in_thread(app: FastAPI, *, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def _base_report(*, db_path: Path, browser_execution_required: bool) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
        "claim_scope": "local_browser_executed_fixture_diagnostic",
        "evidence_scope": "browser_diagnostic_fixture_evidence_not_real_fooddb_pass",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "db_path": str(db_path),
        "user_external_id": USER_EXTERNAL_ID,
        "local_date": LOCAL_DATE,
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "fixture_manager_used": True,
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "web_readiness_claimed": False,
        "fixture_policy": {
            "fixture_manager_can_provide_structured_decisions": True,
            "fixture_evidence_can_simulate_packet_ready_evidence": True,
            "fixture_must_not_become_fooddb_truth": True,
            "fixture_must_not_update_app_knowledge": True,
        },
        "browser": {},
    }


def _estimate_fetch_count(page: Any) -> int:
    return int(
        page.evaluate(
            """() => (window.__accurateIntakeFetches || []).filter((item) => String(item.url || "").includes("/estimate")).length"""
        )
    )


def _send_message(page: Any, *, message: str, timeout_ms: int) -> dict[str, Any]:
    before_count = _estimate_fetch_count(page)
    page.fill("#message-input", message)
    page.click("#send-button")
    page.wait_for_function(
        """(count) => {
          const fetches = window.__accurateIntakeFetches || [];
          const estimateCount = fetches.filter((item) => String(item.url || "").includes("/estimate")).length;
          return estimateCount > count && !document.querySelector("#send-button")?.disabled;
        }""",
        arg=before_count,
        timeout=timeout_ms,
    )
    payload_text = page.locator("#last-payload").inner_text(timeout=timeout_ms)
    payload, parseable = _parse_json_object(payload_text)
    return {"last_payload_parseable": parseable, "last_payload": payload}


def _surface_state(page: Any, *, local_date: str) -> dict[str, Any]:
    return page.evaluate(
        f"""() => {{
          const text = (selector) => document.querySelector(selector)?.textContent?.trim() || "";
          const value = (selector) => document.querySelector(selector)?.value?.trim() || "";
          const listRendered = (selector) => {{
            const contents = text(selector);
            return Boolean(contents) && !contents.includes("No ");
          }};
          return {{
            today_summary_rendered: text("#budget-kcal") !== "unavailable" && text("#remaining-kcal") !== "unavailable",
            target_update_rendered: text("#budget-kcal") === "1600",
            debug_surface_rendered: listRendered("#same-truth-list"),
            runtime_status_surface_rendered: listRendered("#runtime-status-list"),
            pending_followup_surface_rendered: listRendered("#pending-followup-list"),
            failure_signal_surface_rendered: listRendered("#failure-signal-list"),
            meal_threads_rendered: listRendered("#meal-thread-list"),
            backend_local_date_rendered: value("#local-date-display") === {json.dumps(local_date)},
            observed_today_summary: {{
              budget_kcal: text("#budget-kcal"),
              consumed_kcal: text("#consumed-kcal"),
              remaining_kcal: text("#remaining-kcal")
            }}
          }};
        }}"""
    )


def _combined_fetch_sequence(*, before_reload: list[dict[str, Any]], after_reload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(item) for item in before_reload if isinstance(item, dict)] + [
        dict(item) for item in after_reload if isinstance(item, dict)
    ]


def _run_browser_sequence(*, base_url: str, local_debug_token: str, timeout_ms: int, headless: bool) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        page.add_init_script(
            f"""
            (() => {{
              const fixtureUserId = {json.dumps(USER_EXTERNAL_ID)};
              const localDebugToken = {json.dumps(local_debug_token)};
              const primeFields = () => {{
                const userInput = document.querySelector("#user-id");
                if (userInput && userInput.value !== fixtureUserId) {{
                  userInput.value = fixtureUserId;
                }}
                const tokenInput = document.querySelector("#local-debug-token");
                if (tokenInput && tokenInput.value !== localDebugToken) {{
                  tokenInput.value = localDebugToken;
                }}
              }};
              const observer = new MutationObserver(primeFields);
              observer.observe(document, {{ childList: true, subtree: true }});
              primeFields();
            }})();
            """
        )
        _install_fetch_recorder(page)
        try:
            page.goto(f"{base_url}/static/accurate-intake-local-shell.html", wait_until="networkidle", timeout=timeout_ms)
            page.fill("#user-id", USER_EXTERNAL_ID)
            page.fill("#local-debug-token", local_debug_token)
            page.wait_for_function(
                """(token) => document.querySelector("#local-debug-token")?.value === token""",
                arg=local_debug_token,
                timeout=timeout_ms,
            )
            page.evaluate("""async () => { await syncSurfaces(); }""")
            page.wait_for_selector("#message-input", timeout=timeout_ms)
            page.fill("#daily-target", "1600")
            page.click("#set-target")
            page.wait_for_function(
                """() => document.querySelector("#budget-kcal")?.textContent?.trim() === "1600" """,
                timeout=timeout_ms,
            )
            turn_results = []
            surfaces_after_turn = []
            for turn in TURN_FIXTURES:
                result = _send_message(page, message=str(turn["raw_user_input"]), timeout_ms=timeout_ms)
                page.evaluate("""async () => { await syncSurfaces(); }""")
                surfaces_after_turn.append(
                    {
                        "turn_id": turn["turn_id"],
                        "surface": _surface_state(page, local_date=LOCAL_DATE),
                    }
                )
                turn_results.append(
                    {
                        "turn_id": turn["turn_id"],
                        "raw_user_input": turn["raw_user_input"],
                        "expected_manager_decision": {
                            "intent_type": turn["intent_type"],
                            "workflow_effect": turn["workflow_effect"],
                            "final_action": turn["final_action"],
                            "mutation_intent_candidate": turn["mutation_intent_candidate"],
                            "target_attachment": turn["target_attachment"],
                        },
                        "last_payload_parseable": result["last_payload_parseable"],
                        "runtime_error_present": bool(dict(result["last_payload"]).get("error")),
                    }
                )
            before_reload = _surface_state(page, local_date=LOCAL_DATE)
            before_reload_fetch_sequence = page.evaluate("window.__accurateIntakeFetches || []")
            chat_text = page.locator("#chat-log").inner_text(timeout=timeout_ms)
            page.reload(wait_until="networkidle", timeout=timeout_ms)
            page.fill("#user-id", USER_EXTERNAL_ID)
            page.evaluate("""async () => { await syncSurfaces(); }""")
            first_message = str(TURN_FIXTURES[0]["raw_user_input"])
            page.wait_for_function(
                """(message) => {
                  const chat = document.querySelector("#chat-log")?.textContent || "";
                  return chat.includes(message);
                }""",
                arg=first_message,
                timeout=timeout_ms,
            )
            reload_chat_text = page.locator("#chat-log").inner_text(timeout=timeout_ms)
            after_reload = _surface_state(page, local_date=LOCAL_DATE)
            after_reload_fetch_sequence = page.evaluate("window.__accurateIntakeFetches || []")
            storage = page.evaluate(
                """() => ({
                  localStorageKeys: Object.keys(window.localStorage || {}),
                  sessionStorageKeys: Object.keys(window.sessionStorage || {})
                })"""
            )
            return {
                "browser_name": "chromium",
                "page_url": page.url,
                **before_reload,
                "browser_reload_checked": True,
                "chat_history_reloaded": first_message in reload_chat_text,
                "cjk_messages_rendered": all(str(turn["raw_user_input"]) in chat_text for turn in TURN_FIXTURES[:2]),
                "assistant_bubbles_rendered": "Runtime processing" not in chat_text and "Request failed:" not in chat_text,
                "manager_context_status": "missing_context_snapshot"
                if "context_snapshot_present: false" in chat_text
                else "not_available",
                "evidence_gap_observed": True,
                "turn_results": turn_results,
                "surfaces_after_turn": surfaces_after_turn,
                "after_reload_surface": after_reload,
                "fetch_sequence": _combined_fetch_sequence(
                    before_reload=before_reload_fetch_sequence,
                    after_reload=after_reload_fetch_sequence,
                ),
                "before_reload_fetch_sequence": before_reload_fetch_sequence,
                "after_reload_fetch_sequence": after_reload_fetch_sequence,
                "storage": storage,
                "forbidden_storage_used": bool(storage["localStorageKeys"] or storage["sessionStorageKeys"]),
            }
        finally:
            browser.close()


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    browser = dict(report.get("browser") or {})
    existing_status = str(report.get("status") or "")
    if existing_status in FORBIDDEN_SUCCESS_STATUSES:
        blockers.append(f"forbidden_success_status:{existing_status}")
    if report.get("browser_executed") is not True:
        blockers.append("browser_not_executed")
    for key, blocker in (
        ("target_update_rendered", "target_update_not_rendered"),
        ("today_summary_rendered", "today_summary_not_rendered"),
        ("debug_surface_rendered", "debug_surface_not_rendered"),
        ("runtime_status_surface_rendered", "runtime_status_surface_not_rendered"),
        ("meal_threads_rendered", "meal_threads_not_rendered"),
        ("backend_local_date_rendered", "backend_local_date_not_rendered"),
        ("browser_reload_checked", "browser_reload_not_checked"),
        ("chat_history_reloaded", "chat_history_not_reloaded"),
        ("cjk_messages_rendered", "cjk_messages_not_rendered"),
        ("assistant_bubbles_rendered", "assistant_bubbles_not_rendered"),
    ):
        if browser.get(key) is not True:
            blockers.append(blocker)
    after_reload_surface = dict(browser.get("after_reload_surface") or {})
    for key in REQUIRED_RELOAD_SURFACE_FLAGS:
        if after_reload_surface.get(key) is not True:
            blockers.append(f"after_reload_surface.{key.removesuffix('_rendered')}_not_rendered")
    if after_reload_surface.get("observed_today_summary") != browser.get("observed_today_summary"):
        blockers.append("after_reload_surface.today_summary_mismatch")
    turn_results = {
        str(item.get("turn_id") or ""): dict(item)
        for item in list(browser.get("turn_results") or [])
        if isinstance(item, dict)
    }
    for turn_id in REQUIRED_TURN_IDS:
        turn_result = turn_results.get(turn_id)
        if not turn_result:
            blockers.append(f"turn_result_missing:{turn_id}")
            continue
        if turn_result.get("last_payload_parseable") is not True:
            blockers.append(f"turn_result_unparseable:{turn_id}")
        if turn_result.get("runtime_error_present") is True:
            blockers.append(f"turn_result_runtime_error:{turn_id}")
        expected_decision = EXPECTED_TURN_DECISIONS[turn_id]
        observed_decision = dict(turn_result.get("expected_manager_decision") or {})
        for field, expected_value in expected_decision.items():
            if observed_decision.get(field) != expected_value:
                blockers.append(f"turn_result_decision_mismatch:{turn_id}.{field}")
    surfaces_after_turn = {
        str(item.get("turn_id") or ""): dict(item.get("surface") or {})
        for item in list(browser.get("surfaces_after_turn") or [])
        if isinstance(item, dict)
    }
    dinner_draft_surface = surfaces_after_turn.get("dinner_draft_001")
    if not dinner_draft_surface:
        blockers.append("surface_after_turn_missing:dinner_draft_001")
    elif dinner_draft_surface.get("pending_followup_surface_rendered") is not True:
        blockers.append("surface_after_turn.pending_followup_not_rendered:dinner_draft_001")
    for turn_id in ("dinner_basket_001", "dinner_remove_001"):
        surface = surfaces_after_turn.get(turn_id)
        if not surface:
            blockers.append(f"surface_after_turn_missing:{turn_id}")
            continue
        if surface.get("meal_threads_rendered") is not True:
            blockers.append(f"surface_after_turn.meal_threads_not_rendered:{turn_id}")
        if surface.get("backend_local_date_rendered") is not True:
            blockers.append(f"surface_after_turn.backend_local_date_not_rendered:{turn_id}")
    first_pass_calls = []
    for item in list(report.get("manager_provider_calls") or []):
        if not isinstance(item, dict):
            continue
        available_tools = {str(tool) for tool in list(item.get("available_tools") or [])}
        round_index = int(item.get("round_index") or 0)
        if round_index == 0 and FIRST_PASS_READ_TOOL_MARKERS.intersection(available_tools):
            first_pass_calls.append(dict(item))
    if [str(item.get("turn_id") or "") for item in first_pass_calls] != list(REQUIRED_TURN_IDS):
        blockers.append("fixture_manager_turn_sequence_mismatch")
    manager_context_status = str(browser.get("manager_context_status") or "")
    if manager_context_status not in {"not_available", "not_checked", "missing_context_snapshot"}:
        blockers.append("manager_context_status_overclaim")
    for expected, method in REQUIRED_FETCH_METHODS.items():
        if not any(
            expected in str(item.get("url") or "") and str(item.get("method") or "GET").upper() == method
            for item in list(browser.get("fetch_sequence") or [])
            if isinstance(item, dict)
        ):
            blockers.append(f"fetch_missing:{method} {expected}")
    storage = dict(browser.get("storage") or {})
    storage_evidence_present = isinstance(storage.get("localStorageKeys"), list) and isinstance(
        storage.get("sessionStorageKeys"), list
    )
    if report.get("browser_executed") is True and not storage_evidence_present:
        blockers.append("storage_evidence_missing")
    if browser.get("forbidden_storage_used") is True:
        blockers.append("forbidden_storage_used")
    if report.get("fixture_manager_used") is not True or report.get("fixture_evidence_used") is not True:
        blockers.append("fixture_scope_not_declared")
    if report.get("real_fooddb_pass_claimed") is not False or report.get("dogfood_pass") is not False:
        blockers.append("real_dogfood_pass_overclaim")
    if report.get("fooddb_evidence_used") is not False:
        blockers.append("fooddb_evidence_used_in_fixture_diagnostic")
    if blockers:
        return "fail", blockers
    if report.get("fixture_evidence_used") is True:
        return DIAGNOSTIC_STATUS_WITH_FIXTURE_GAP, []
    return DIAGNOSTIC_STATUS_WITH_EVIDENCE_GAP, []


def build_browser_realistic_web_dogfood_v2_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    reset_db: bool = True,
    require_browser_execution: bool = False,
    timeout_ms: int = 15000,
    headless: bool = True,
) -> dict[str, Any]:
    report = _base_report(db_path=db_path, browser_execution_required=require_browser_execution)
    try:
        _load_sync_playwright()
    except BrowserSmokeDependencyMissing:
        report["status"] = "fail" if require_browser_execution else "blocked"
        report["blockers"] = ["playwright_not_installed"]
        return report
    if reset_db and db_path.exists():
        db_path.unlink()
    engine, SessionLocal = _session_factory(db_path)
    db = SessionLocal()
    provider = _BrowserRealisticManagerProvider()
    _seed_body_plan(db, user_external_id=USER_EXTERNAL_ID, local_date=LOCAL_DATE)
    local_debug_token = secrets.token_urlsafe(24)
    previous_debug_token = os.environ.get("LOCAL_DEBUG_API_TOKEN")
    os.environ["LOCAL_DEBUG_API_TOKEN"] = local_debug_token
    app: FastAPI | None = None
    server: uvicorn.Server | None = None
    thread: threading.Thread | None = None
    try:
        app = _build_app(db, provider)
        port = _free_port()
        server, thread = _run_uvicorn_in_thread(app, port=port)
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-local-shell.html")
        try:
            report["browser"] = _run_browser_sequence(
                base_url=base_url,
                local_debug_token=local_debug_token,
                timeout_ms=timeout_ms,
                headless=headless,
            )
        except Exception as exc:
            report["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
            report["status"] = "fail"
            report["blockers"] = [f"browser_sequence_error:{type(exc).__name__}"]
            return report
        report["browser_executed"] = True
        report["manager_provider"] = provider.readiness()
        report["manager_provider_calls"] = list(provider.calls)
        status, blockers = _validate(report)
        report["status"] = status
        report["blockers"] = blockers
        return report
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=5)
        if app is not None:
            _restore_runtime(app)
        db.close()
        engine.dispose()
        if previous_debug_token is None:
            os.environ.pop("LOCAL_DEBUG_API_TOKEN", None)
        else:
            os.environ["LOCAL_DEBUG_API_TOKEN"] = previous_debug_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run browser realistic local dogfood diagnostic v2.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args(argv)

    report = build_browser_realistic_web_dogfood_v2_report(
        db_path=Path(args.db_path),
        reset_db=not args.keep_db,
        require_browser_execution=args.require_browser_execution,
        timeout_ms=args.timeout_ms,
        headless=not args.headed,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] in {DIAGNOSTIC_STATUS_WITH_FIXTURE_GAP, DIAGNOSTIC_STATUS_WITH_EVIDENCE_GAP}:
        return 0
    if report["status"] == "blocked" and not args.require_browser_execution:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
