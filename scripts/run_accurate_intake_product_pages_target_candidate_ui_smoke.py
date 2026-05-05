from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.budget.interface.today_surface import resolve_today_local_date  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.runtime.interface.local_debug_auth import LOCAL_DEBUG_API_TOKEN_ENV  # noqa: E402
from app.shared.infra.models import MessageBuffer  # noqa: E402
from scripts.run_accurate_intake_browser_shell_smoke import (  # noqa: E402
    BrowserSmokeDependencyMissing,
    _build_app,
    _free_port,
    _load_sync_playwright,
    _restore_runtime,
    _run_uvicorn_in_thread,
    _session_factory,
    _wait_for_http,
)
from scripts.run_accurate_intake_product_pages_browser_smoke import (  # noqa: E402
    _capture_fetches,
    _is_visible_product_text_clean,
    _open_page,
    _page_url,
)


DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_target_candidate_ui_smoke.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_product_pages_target_candidate_ui_smoke.json"
DEFAULT_USER_ID = "product-pages-target-candidate-ui-user"
DEFAULT_LOCAL_DATE = resolve_today_local_date(None)
EXPECTED_TARGET_NAMES = ["luwei", "milk tea"]
NOT_CLAIMING = [
    "web_ready",
    "product_ready",
    "private_self_use_approved",
    "real_fooddb_pass",
    "dogfood_pass",
    "live_llm_ready",
]


class _NoCallManagerProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "target_candidate_ui_no_call_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append(dict(kwargs))
        return {}, {"unexpected_provider_call": True}


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    local_date: str,
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
        "claim_scope": "local_product_pages_target_candidate_ui_browser_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "local_date": local_date,
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "browser_reload_checked": False,
        "chat_page_loaded": False,
        "chat_history_reloaded": False,
        "target_candidate_surface_checked": False,
        "target_candidate_count_rendered": 0,
        "target_candidate_names_rendered": [],
        "target_candidate_list_read_only": False,
        "context_strip_read_only": False,
        "product_pages_no_debug_trace": False,
        "manager_provider_call_count": 0,
        "frontend_semantic_owner": False,
        "frontend_selected_target": False,
        "deterministic_selected_target": False,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "fetch_sequence": [],
    }


def _runtime_trace(local_date: str) -> dict[str, Any]:
    target_candidates = [
        {
            "target_object_type": "meal_thread",
            "target_object_id": "meal-thread-luwei",
            "meal_thread_id": "meal-thread-luwei",
            "display_name": "luwei",
            "uniqueness_status": "candidate",
            "read_only": True,
            "mutation_authority": False,
            "removable": True,
            "eligible": True,
        },
        {
            "target_object_type": "meal_thread",
            "target_object_id": "meal-thread-milk-tea",
            "meal_thread_id": "meal-thread-milk-tea",
            "display_name": "milk tea",
            "uniqueness_status": "candidate",
            "read_only": True,
            "mutation_authority": False,
            "removable": True,
            "eligible": True,
        },
    ]
    return {
        "local_date": local_date,
        "context_policy_version": "accurate_intake_mvp_context_policy_v1",
        "loaded_context_summary": {
            "source": "seeded_browser_ui_smoke",
            "target_candidate_count": len(target_candidates),
            "read_only": True,
            "mutation_authority": False,
        },
        "omitted_context_summary": {
            "policy_excluded_context_ids": [
                "debug_artifacts",
                "dogfood_review_artifacts",
                "food_gap_candidates_as_truth",
                "long_term_memory",
                "proactive_context",
                "rescue_context",
                "recommendation_context",
            ],
            "read_only": True,
            "mutation_authority": False,
        },
        "manager_context_packet_v1": {
            "hard_pins": {
                "pending_followup": {},
                "pending_draft": {},
            },
            "target_candidates": {
                "for_correction_or_removal": target_candidates,
            },
            "read_only": True,
            "mutation_authority": False,
        },
    }


def _seed_chat_history(db: Any, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    trace_json = {"runtime_turn_trace": _runtime_trace(local_date)}
    db.add(
        MessageBuffer(
            user_id=user.id,
            role="user",
            content="Please show target candidates from backend context.",
            trace_id="target-candidate-ui-user",
            trace_json=trace_json,
        )
    )
    db.add(
        MessageBuffer(
            user_id=user.id,
            role="assistant",
            content="Target candidates are available for review.",
            trace_id="target-candidate-ui-assistant",
            trace_json=trace_json,
        )
    )
    db.commit()


def _storage_keys(page: Any) -> dict[str, list[str]]:
    return page.evaluate(
        """() => ({
          localStorageKeys: Object.keys(window.localStorage || {}),
          sessionStorageKeys: Object.keys(window.sessionStorage || {})
        })"""
    )


def _run_browser_sequence(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    timeout_ms: int,
    headless: bool,
    local_debug_token: str,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    result: dict[str, Any] = {
        "current_step": "not_started",
        "fetch_sequence": [],
        "target_candidate_names_rendered": [],
        "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            viewport = {"width": 1440, "height": 1100}
            result["current_step"] = "open_chat"
            chat = _open_page(
                browser,
                viewport=viewport,
                url=_page_url(base_url, "chat", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            chat.wait_for_selector('[data-surface-role="chat"]', timeout=timeout_ms)
            result["chat_page_loaded"] = True
            chat.wait_for_function(
                """() => (document.querySelector("#chat-context-targets")?.textContent || "").trim() === "2" """,
                timeout=timeout_ms,
            )
            chat.wait_for_function(
                """(names) => {
                  const text = document.querySelector("#chat-target-candidate-list")?.textContent || "";
                  return names.every((name) => text.includes(name));
                }""",
                arg=EXPECTED_TARGET_NAMES,
                timeout=timeout_ms,
            )
            result["chat_history_reloaded"] = True
            rendered_names = chat.locator("#chat-target-candidate-list li").all_inner_texts()
            result["target_candidate_names_rendered"] = [str(item).strip() for item in rendered_names if str(item).strip()]
            result["target_candidate_count_rendered"] = len(result["target_candidate_names_rendered"])
            result["target_candidate_surface_checked"] = result["target_candidate_names_rendered"] == EXPECTED_TARGET_NAMES
            result["target_candidate_list_read_only"] = bool(
                chat.evaluate(
                    """() => {
                      const list = document.querySelector("#chat-target-candidate-list");
                      if (!list || list.getAttribute("aria-readonly") !== "true") return false;
                      return !list.querySelector("button, input, select, textarea, a[href]");
                    }"""
                )
            )
            result["context_strip_read_only"] = bool(
                chat.evaluate(
                    """() => {
                      const strip = document.querySelector("#chat-context-strip");
                      return Boolean(strip) && !strip.querySelector("button, input, select, textarea, a[href]");
                    }"""
                )
            )
            body_text = chat.locator("body").inner_text(timeout=timeout_ms)
            result["product_pages_no_debug_trace"] = _is_visible_product_text_clean(body_text)
            result["fetch_sequence"].extend(_capture_fetches(chat))

            result["current_step"] = "reload"
            chat.reload(wait_until="networkidle", timeout=timeout_ms)
            chat.wait_for_function(
                """(names) => {
                  const text = document.querySelector("#chat-target-candidate-list")?.textContent || "";
                  return (document.querySelector("#chat-context-targets")?.textContent || "").trim() === "2"
                    && names.every((name) => text.includes(name));
                }""",
                arg=EXPECTED_TARGET_NAMES,
                timeout=timeout_ms,
            )
            result["browser_reload_checked"] = True
            result["fetch_sequence"].extend(_capture_fetches(chat))
            result["storage"] = _storage_keys(chat)
            result["current_step"] = "complete"
            chat.close()
            return result
        except Exception as exc:
            result["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
            return result
        finally:
            browser.close()


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []

    def require_true(key: str, blocker: str) -> None:
        if report.get(key) is not True:
            blockers.append(blocker)

    for key, blocker in (
        ("browser_executed", "browser_not_executed"),
        ("browser_reload_checked", "browser_reload_not_checked"),
        ("chat_page_loaded", "chat_page_not_loaded"),
        ("chat_history_reloaded", "chat_history_not_reloaded"),
        ("target_candidate_surface_checked", "target_candidate_surface_not_checked"),
        ("target_candidate_list_read_only", "target_candidate_list_not_read_only"),
        ("context_strip_read_only", "context_strip_not_read_only"),
        ("product_pages_no_debug_trace", "product_pages_debug_trace_leaked"),
    ):
        require_true(key, blocker)
    if int(report.get("target_candidate_count_rendered") or 0) != 2:
        blockers.append("target_candidate_count_rendered_mismatch")
    if _list_value(report.get("target_candidate_names_rendered")) != EXPECTED_TARGET_NAMES:
        blockers.append("target_candidate_names_rendered_mismatch")
    if int(report.get("manager_provider_call_count") or 0) != 0:
        blockers.append("manager_provider_called")
    storage = _dict_value(report.get("browser")).get("storage") or report.get("storage") or {}
    if _list_value(_dict_value(storage).get("localStorageKeys")) or _list_value(_dict_value(storage).get("sessionStorageKeys")):
        blockers.append("forbidden_storage_used")
    fetch_urls = [
        str(item.get("url") or "")
        for item in _list_value(_dict_value(report.get("browser")).get("fetch_sequence"))
        if isinstance(item, dict)
    ]
    if not any("/accurate-intake/chat-history" in url for url in fetch_urls):
        blockers.append("required_fetch_missing:/accurate-intake/chat-history")
    if any("/estimate" in url for url in fetch_urls):
        blockers.append("estimate_endpoint_called")

    false_flags = {
        "frontend_semantic_owner": "frontend_semantic_owner_claimed",
        "frontend_selected_target": "frontend_selected_target",
        "deterministic_selected_target": "deterministic_selected_target",
        "deterministic_semantic_inference_used": "deterministic_semantic_inference_used",
        "raw_text_intent_router_used": "raw_text_intent_router_used",
        "mutation_authority": "mutation_authority_claimed",
        "live_llm_invoked": "live_llm_invoked",
        "web_tavily_used": "web_tavily_used",
        "fooddb_evidence_used": "fooddb_evidence_used",
        "real_fooddb_pass_claimed": "real_fooddb_pass_claimed",
        "dogfood_pass": "dogfood_pass_claimed",
        "web_readiness_claimed": "web_readiness_claimed",
        "product_readiness_claimed": "product_readiness_claimed",
        "private_self_use_approved": "private_self_use_approved",
    }
    for key, blocker in false_flags.items():
        if report.get(key) is True:
            blockers.append(blocker)
    sequence_error = str(_dict_value(report.get("browser")).get("browser_sequence_error") or "")
    if sequence_error:
        blockers.append(f"browser_sequence_error:{sequence_error.split(':', 1)[0]}")
    return ("pass" if not blockers else "fail"), blockers


def build_product_pages_target_candidate_ui_smoke_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    user_external_id: str = DEFAULT_USER_ID,
    local_date: str = DEFAULT_LOCAL_DATE,
    reset_db: bool = True,
    require_browser_execution: bool = False,
    timeout_ms: int = 15000,
    headless: bool = True,
) -> dict[str, Any]:
    report = _base_report(
        user_external_id=user_external_id,
        db_path=db_path,
        local_date=local_date,
        browser_execution_required=require_browser_execution,
    )
    try:
        _load_sync_playwright()
    except BrowserSmokeDependencyMissing:
        report["status"] = "blocked" if not require_browser_execution else "fail"
        report["blockers"] = ["playwright_not_installed"]
        report["operator_action"] = "Install Playwright locally and rerun; this artifact must not claim readiness."
        return report

    if reset_db and db_path.exists():
        db_path.unlink()
    engine, SessionLocal = _session_factory(db_path)
    provider = _NoCallManagerProvider()
    db = SessionLocal()
    app = _build_app(db, provider)  # type: ignore[arg-type]
    port = _free_port()
    previous_debug_token = os.environ.get(LOCAL_DEBUG_API_TOKEN_ENV)
    local_debug_token = secrets.token_urlsafe(24)
    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = local_debug_token
    server, thread = _run_uvicorn_in_thread(app, port=port)
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-chat.html")
        _seed_chat_history(db, user_external_id=user_external_id, local_date=local_date)
        browser_result = _run_browser_sequence(
            base_url=base_url,
            user_external_id=user_external_id,
            local_date=local_date,
            timeout_ms=timeout_ms,
            headless=headless,
            local_debug_token=local_debug_token,
        )
        report["browser_executed"] = True
        report["browser"] = browser_result
        for key, value in browser_result.items():
            if key in report:
                report[key] = value
        report["fetch_sequence"] = browser_result.get("fetch_sequence", [])
        report["manager_provider_call_count"] = len(provider.calls)
        status, blockers = _validate(report)
        report["status"] = status
        report["blockers"] = blockers
        return report
    except Exception as exc:
        report["status"] = "fail"
        report["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
        report["blockers"] = [f"browser_sequence_error:{type(exc).__name__}"]
        return report
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        _restore_runtime(app)
        if previous_debug_token is None:
            os.environ.pop(LOCAL_DEBUG_API_TOKEN_ENV, None)
        else:
            os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = previous_debug_token
        db.close()
        engine.dispose()
        time.sleep(0.1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run product-pages browser smoke for read-only target candidate rendering."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args(argv)

    report = build_product_pages_target_candidate_ui_smoke_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        local_date=args.local_date,
        reset_db=not args.keep_db,
        require_browser_execution=args.require_browser_execution,
        timeout_ms=args.timeout_ms,
        headless=not args.show_browser,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report.get("status"), "output": str(output_path)}, ensure_ascii=False))
    return 0 if report.get("status") in {"pass", "blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
