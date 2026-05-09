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

from app.database import get_db  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.budget.interface.today_surface import resolve_today_local_date  # noqa: E402
from scripts.run_accurate_intake_browser_shell_smoke import (  # noqa: E402
    BrowserSmokeDependencyMissing,
    _install_fetch_recorder,
    _load_sync_playwright,
)
from scripts.run_accurate_intake_one_day_realistic_web_dogfood import (  # noqa: E402
    DOGFOOD_USER_EXTERNAL_ID,
    build_report as build_realistic_manager_dogfood_report,
)

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_browser_one_day_fixture.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_browser_one_day_fixture_dogfood.json"
USER_EXTERNAL_ID = DOGFOOD_USER_EXTERNAL_ID
LOCAL_DATE = resolve_today_local_date(None)
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
    "/accurate-intake/debug": "GET",
    "/accurate-intake/chat-history": "GET",
}


def _session_factory(db_path: Path) -> tuple[Any, sessionmaker[Session]]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _build_app(db: Session) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return app


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
        "artifact_type": "accurate_intake_browser_one_day_fixture_dogfood",
        "claim_scope": "local_browser_executed_fixture_diagnostic",
        "evidence_scope": "browser_fixture_render_reload_not_real_fooddb_dogfood_pass",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "db_path": str(db_path),
        "user_external_id": USER_EXTERNAL_ID,
        "local_date": LOCAL_DATE,
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
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
        "browser": {},
    }


def _run_browser_sequence(
    *,
    base_url: str,
    local_debug_token: str,
    expected_today_summary: dict[str, str],
    timeout_ms: int,
    headless: bool,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        page.add_init_script(
            f"""
            (() => {{
              const fixtureUserId = {json.dumps(USER_EXTERNAL_ID)};
              const localDebugToken = {json.dumps(local_debug_token)};
              const primeUserId = () => {{
                const input = document.querySelector("#user-id");
                if (input && input.value !== fixtureUserId) {{
                  input.value = fixtureUserId;
                }}
              }};
              const primeLocalDebugToken = () => {{
                const input = document.querySelector("#local-debug-token");
                if (input && input.value !== localDebugToken) {{
                  input.value = localDebugToken;
                }}
              }};
              const observer = new MutationObserver(() => {{
                primeUserId();
                primeLocalDebugToken();
              }});
              observer.observe(document, {{ childList: true, subtree: true }});
              primeUserId();
              primeLocalDebugToken();
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
            page.wait_for_function(
                """(expected) => {
                  const consumed = document.querySelector("#consumed-kcal")?.textContent?.trim();
                  const remaining = document.querySelector("#remaining-kcal")?.textContent?.trim();
                  return consumed === expected.consumed_kcal && remaining === expected.remaining_kcal;
                }""",
                arg=expected_today_summary,
                timeout=timeout_ms,
            )
            before_reload = _surface_state(
                page,
                local_date=LOCAL_DATE,
                expected_today_summary=expected_today_summary,
            )
            page.reload(wait_until="networkidle", timeout=timeout_ms)
            page.fill("#user-id", USER_EXTERNAL_ID)
            page.evaluate("""async () => { await syncSurfaces(); }""")
            page.wait_for_function(
                """(expected) => document.querySelector("#consumed-kcal")?.textContent?.trim() === expected.consumed_kcal """,
                arg=expected_today_summary,
                timeout=timeout_ms,
            )
            after_reload = _surface_state(
                page,
                local_date=LOCAL_DATE,
                expected_today_summary=expected_today_summary,
            )
            fetch_sequence = page.evaluate("window.__accurateIntakeFetches || []")
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
                "reload_state_rehydrated": bool(
                    after_reload.get("today_summary_rendered")
                    and after_reload.get("meal_threads_rendered")
                    and after_reload.get("same_truth_rendered")
                ),
                "after_reload_surface": after_reload,
                "fetch_sequence": fetch_sequence,
                "storage": storage,
                "forbidden_storage_used": bool(storage["localStorageKeys"] or storage["sessionStorageKeys"]),
            }
        finally:
            browser.close()


def _surface_state(
    page: Any,
    *,
    local_date: str,
    expected_today_summary: dict[str, str],
) -> dict[str, Any]:
    return page.evaluate(
        f"""(expected) => {{
          const text = (selector) => document.querySelector(selector)?.textContent?.trim() || "";
          const value = (selector) => document.querySelector(selector)?.value?.trim() || "";
          const mealThreads = text("#meal-thread-list");
          const corrections = text("#draft-correction-list");
          const sameTruth = text("#same-truth-list");
          return {{
            today_summary_rendered: (
              text("#budget-kcal") === expected.budget_kcal &&
              text("#consumed-kcal") === expected.consumed_kcal &&
              text("#remaining-kcal") === expected.remaining_kcal
            ),
            meal_threads_rendered: mealThreads.length > 0 && !mealThreads.includes("No meal threads"),
            correction_history_rendered: corrections.length > 0 && !corrections.includes("No pending drafts"),
            removed_item_rendered: corrections.includes("removed:"),
            remaining_items_rendered: mealThreads.includes("items:") || corrections.includes("kept:"),
            same_truth_rendered: sameTruth.includes("status: pass"),
            backend_local_date_rendered: value("#local-date-display") === {json.dumps(local_date)},
            meal_thread_text: mealThreads,
            correction_history_text: corrections,
            observed_today_summary: {{
              budget_kcal: text("#budget-kcal"),
              consumed_kcal: text("#consumed-kcal"),
              remaining_kcal: text("#remaining-kcal")
            }}
          }};
        }}""",
        expected_today_summary,
    )


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    browser = dict(report.get("browser") or {})
    if report.get("browser_executed") is not True:
        blockers.append("browser_not_executed")
    for key, blocker in (
        ("today_summary_rendered", "today_summary_not_rendered"),
        ("meal_threads_rendered", "meal_threads_not_rendered"),
        ("correction_history_rendered", "correction_history_not_rendered"),
        ("removed_item_rendered", "removed_item_not_rendered"),
        ("remaining_items_rendered", "remaining_items_not_rendered"),
        ("same_truth_rendered", "same_truth_not_rendered"),
        ("browser_reload_checked", "browser_reload_not_checked"),
        ("reload_state_rehydrated", "reload_state_not_rehydrated"),
    ):
        if browser.get(key) is not True:
            blockers.append(blocker)
    expected_today_summary = dict(report.get("expected_today_summary") or {})
    if expected_today_summary and dict(browser.get("observed_today_summary") or {}) != expected_today_summary:
        blockers.append("observed_today_summary_mismatch")
    for expected, method in REQUIRED_FETCH_METHODS.items():
        if not any(
            expected in str(item.get("url") or "") and str(item.get("method") or "GET").upper() == method
            for item in list(browser.get("fetch_sequence") or [])
            if isinstance(item, dict)
        ):
            blockers.append(f"fetch_missing:{method} {expected}")
    storage = dict(browser.get("storage") or {})
    if not isinstance(storage.get("localStorageKeys"), list) or not isinstance(storage.get("sessionStorageKeys"), list):
        blockers.append("storage_evidence_missing")
    if browser.get("forbidden_storage_used") is True:
        blockers.append("forbidden_storage_used")
    if report.get("fixture_evidence_used") is not True:
        blockers.append("fixture_evidence_not_declared")
    if report.get("real_fooddb_pass_claimed") is not False or report.get("dogfood_pass") is not False:
        blockers.append("real_dogfood_pass_overclaim")
    return ("browser_fixture_pass" if not blockers else "fail"), blockers


def _manager_final_today_summary(manager_report: dict[str, Any]) -> dict[str, str]:
    turns = list(manager_report.get("turns") or [])
    for turn in reversed(turns):
        state_after = dict(turn.get("state_after") or {})
        if {
            "budget_kcal",
            "consumed_kcal",
            "remaining_kcal",
        }.issubset(state_after):
            return {
                "budget_kcal": str(state_after["budget_kcal"]),
                "consumed_kcal": str(state_after["consumed_kcal"]),
                "remaining_kcal": str(state_after["remaining_kcal"]),
            }
    raise RuntimeError("manager_dogfood_final_today_summary_missing")


def _manager_summary(manager_report: dict[str, Any]) -> dict[str, Any]:
    evidence = dict(manager_report.get("evidence") or {})
    return {
        "status": manager_report.get("status"),
        "final_today_summary": _manager_final_today_summary(manager_report),
        "turn_count": len(list(manager_report.get("turns") or [])),
        "approved_fooddb_evidence_fixture_used": bool(evidence.get("approved_fooddb_evidence_fixture_used")),
        "macro_present_evidence_seen": bool(evidence.get("macro_present_evidence_seen")),
        "macro_missing_evidence_seen": bool(evidence.get("macro_missing_evidence_seen")),
    }


def build_browser_one_day_fixture_dogfood_report(
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

    manager_wrapper = build_realistic_manager_dogfood_report(
        db_path=db_path,
        local_date=LOCAL_DATE,
        reset_db=reset_db,
    )
    manager_dogfood = dict(manager_wrapper.get("one_day_realistic_web_dogfood") or {})
    report["manager_runtime_source"] = "one_day_realistic_web_dogfood"
    report["manager_dogfood_status"] = manager_dogfood.get("status")
    if not manager_dogfood:
        report["status"] = "fail"
        report["blockers"] = ["manager_dogfood_report_missing"]
        return report
    if manager_dogfood.get("status") != "pass":
        report["scenario_wall_status"] = manager_dogfood.get("status")
        report["scenario_wall_id"] = "one_day_realistic_web_dogfood"
        report["status"] = "fail"
        report["blockers"] = ["manager_dogfood_not_pass"]
        return report
    manager_evidence = dict(manager_dogfood.get("evidence") or {})
    manager_summary = _manager_summary(manager_dogfood)
    expected_today_summary = manager_summary["final_today_summary"]
    report["manager_dogfood_summary"] = manager_summary
    report["expected_today_summary"] = expected_today_summary
    report["fooddb_evidence_used"] = bool(
        manager_evidence.get("fooddb_evidence_used")
        or manager_evidence.get("approved_fooddb_evidence_fixture_used")
    )
    report["scenario_wall_status"] = manager_dogfood.get("status")
    report["scenario_wall_summary"] = manager_summary
    report["scenario_wall_id"] = "one_day_realistic_web_dogfood"
    engine, SessionLocal = _session_factory(db_path)
    db = SessionLocal()
    local_debug_token = secrets.token_urlsafe(24)
    previous_debug_token = os.environ.get("LOCAL_DEBUG_API_TOKEN")
    os.environ["LOCAL_DEBUG_API_TOKEN"] = local_debug_token
    server: uvicorn.Server | None = None
    thread: threading.Thread | None = None
    try:
        app = _build_app(db)
        port = _free_port()
        server, thread = _run_uvicorn_in_thread(app, port=port)
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-local-shell.html")
        try:
            report["browser"] = _run_browser_sequence(
                base_url=base_url,
                local_debug_token=local_debug_token,
                expected_today_summary=expected_today_summary,
                timeout_ms=timeout_ms,
                headless=headless,
            )
        except Exception as exc:
            report["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
            report["status"] = "fail"
            report["blockers"] = [f"browser_sequence_error:{type(exc).__name__}"]
            return report
        report["browser_executed"] = True
        status, blockers = _validate(report)
        report["status"] = status
        report["blockers"] = blockers
        return report
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=5)
        db.close()
        engine.dispose()
        if previous_debug_token is None:
            os.environ.pop("LOCAL_DEBUG_API_TOKEN", None)
        else:
            os.environ["LOCAL_DEBUG_API_TOKEN"] = previous_debug_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run browser one-day fixture dogfood diagnostic.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args(argv)

    report = build_browser_one_day_fixture_dogfood_report(
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
    if report["status"] == "browser_fixture_pass":
        return 0
    if report["status"] == "blocked" and not args.require_browser_execution:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
