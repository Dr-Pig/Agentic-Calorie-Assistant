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
from app.runtime.interface.local_debug_auth import LOCAL_DEBUG_API_TOKEN_ENV  # noqa: E402
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


DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_body_noplan_degraded.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_product_pages_body_noplan_degraded_smoke.json"
DEFAULT_USER_ID = "product-pages-body-noplan-user"
DEFAULT_LOCAL_DATE = resolve_today_local_date(None)
REQUIRED_FETCH_PREFIXES = (
    "/body-plan/active",
    "/today/deficit-summary",
    "/today/effective-budget",
    "/today/weekly-progress",
    "/today/current-budget",
)
FORBIDDEN_MUTATION_ENDPOINTS = (
    "/onboarding/bootstrap",
    "/weight/observation",
    "/body-plan/manual-daily-target",
)


class _NoCallManagerProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "body_noplan_degraded_no_call_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append(dict(kwargs))
        return {}, {"unexpected_provider_call": True}


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    local_date: str,
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_product_pages_body_noplan_degraded_smoke_v1",
        "claim_scope": "local_product_pages_body_noplan_degraded_browser_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "local_date": local_date,
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "body_page_loaded": False,
        "today_page_loaded": False,
        "no_plan_body_status_rendered": False,
        "body_targets_hidden_for_no_plan": False,
        "body_budget_degraded_rendered": False,
        "today_no_plan_budget_rendered": False,
        "no_bootstrap_or_mutation_post": False,
        "product_pages_no_debug_trace": False,
        "manager_provider_call_count": 0,
        "body_values": {},
        "today_values": {},
        "fetch_sequence": [],
    }


def _text(page: Any, selector: str, *, timeout_ms: int) -> str:
    return page.locator(selector).inner_text(timeout=timeout_ms).strip()


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
        "body_values": {},
        "today_values": {},
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            viewport = {"width": 1440, "height": 1000}
            result["current_step"] = "open_body_no_plan"
            body = _open_page(
                browser,
                viewport=viewport,
                url=_page_url(base_url, "body", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            body.wait_for_selector('[data-surface-role="body-plan"]', timeout=timeout_ms)
            body.wait_for_function(
                """() => (document.querySelector("#body-status")?.textContent || "").includes("Set up")""",
                timeout=timeout_ms,
            )
            body_values = {
                "status": _text(body, "#body-status", timeout_ms=timeout_ms),
                "daily_target": _text(body, "#plan-daily-target", timeout_ms=timeout_ms),
                "tdee": _text(body, "#plan-tdee", timeout_ms=timeout_ms),
                "active_target": _text(body, "#body-active-target", timeout_ms=timeout_ms),
                "remaining": _text(body, "#body-remaining-kcal", timeout_ms=timeout_ms),
                "effective_budget": _text(body, "#body-effective-budget", timeout_ms=timeout_ms),
            }
            body_text = body.locator("body").inner_text(timeout=timeout_ms)
            result["body_page_loaded"] = True
            result["body_values"] = body_values
            result["no_plan_body_status_rendered"] = "Set up your body plan" in body_values["status"]
            result["body_targets_hidden_for_no_plan"] = (
                body_values["daily_target"] == "--"
                and body_values["tdee"] == "--"
                and body_values["active_target"] == "--"
            )
            result["body_budget_degraded_rendered"] = (
                body_values["remaining"] == "--" and body_values["effective_budget"] == "0 kcal"
            )
            result["product_pages_no_debug_trace"] = _is_visible_product_text_clean(body_text)
            result["fetch_sequence"].extend(_capture_fetches(body))
            body.close()

            result["current_step"] = "open_today_no_plan"
            today = _open_page(
                browser,
                viewport=viewport,
                url=_page_url(base_url, "today", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            today.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
            today.wait_for_function(
                """() => document.querySelector("#budget-kcal")?.textContent?.trim() === "0" """,
                timeout=timeout_ms,
            )
            today_values = {
                "budget": _text(today, "#budget-kcal", timeout_ms=timeout_ms),
                "consumed": _text(today, "#consumed-kcal", timeout_ms=timeout_ms),
                "remaining": _text(today, "#remaining-kcal", timeout_ms=timeout_ms),
            }
            today_text = today.locator("body").inner_text(timeout=timeout_ms)
            result["today_page_loaded"] = True
            result["today_values"] = today_values
            result["today_no_plan_budget_rendered"] = today_values == {
                "budget": "0",
                "consumed": "0",
                "remaining": "0",
            }
            result["product_pages_no_debug_trace"] = (
                result["product_pages_no_debug_trace"] and _is_visible_product_text_clean(today_text)
            )
            result["fetch_sequence"].extend(_capture_fetches(today))
            today.close()
            result["current_step"] = "complete"
            return result
        except Exception as exc:
            result["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
            return result
        finally:
            browser.close()


def _fetch_sequence(report: dict[str, Any]) -> list[dict[str, Any]]:
    browser = _dict(report.get("browser"))
    sequence = _list(browser.get("fetch_sequence")) or _list(report.get("fetch_sequence"))
    return [item for item in sequence if isinstance(item, dict)]


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []

    def require_true(key: str, blocker: str) -> None:
        if report.get(key) is not True:
            blockers.append(blocker)

    require_true("browser_executed", "browser_not_executed")
    require_true("body_page_loaded", "body_page_not_loaded")
    require_true("today_page_loaded", "today_page_not_loaded")
    require_true("no_plan_body_status_rendered", "no_plan_body_status_not_rendered")
    require_true("body_targets_hidden_for_no_plan", "body_targets_not_hidden_for_no_plan")
    require_true("body_budget_degraded_rendered", "body_budget_degraded_not_rendered")
    require_true("today_no_plan_budget_rendered", "today_no_plan_budget_not_rendered")
    require_true("product_pages_no_debug_trace", "product_pages_debug_trace_leaked")

    body_values = _dict(report.get("body_values"))
    if body_values.get("daily_target") != "--":
        blockers.append("body_no_plan_daily_target_not_hidden")
    if body_values.get("tdee") != "--":
        blockers.append("body_no_plan_tdee_not_hidden")
    if body_values.get("active_target") != "--":
        blockers.append("body_no_plan_active_target_not_hidden")
    if body_values.get("remaining") != "--":
        blockers.append("body_no_plan_remaining_not_degraded")

    today_values = _dict(report.get("today_values"))
    if today_values and today_values != {"budget": "0", "consumed": "0", "remaining": "0"}:
        blockers.append("today_no_plan_budget_values_changed")

    fetches = _fetch_sequence(report)
    fetch_urls = [str(item.get("url") or "") for item in fetches]
    for prefix in REQUIRED_FETCH_PREFIXES:
        if not any(prefix in url for url in fetch_urls):
            blockers.append(f"required_fetch_missing:{prefix}")
    mutation_posts = [
        url
        for item in fetches
        for url in [str(item.get("url") or "")]
        if str(item.get("method") or "GET").upper() == "POST"
        and any(endpoint in url for endpoint in FORBIDDEN_MUTATION_ENDPOINTS)
    ]
    for url in mutation_posts:
        matched = next(endpoint for endpoint in FORBIDDEN_MUTATION_ENDPOINTS if endpoint in url)
        blockers.append(f"unexpected_no_plan_mutation_post:{matched}")
    if not mutation_posts:
        report["no_bootstrap_or_mutation_post"] = True
    else:
        report["no_bootstrap_or_mutation_post"] = False
    if int(report.get("manager_provider_call_count") or 0) != 0:
        blockers.append("manager_provider_called")
    sequence_error = str(_dict(report.get("browser")).get("browser_sequence_error") or report.get("browser_sequence_error") or "")
    if sequence_error:
        blockers.append(f"browser_sequence_error:{sequence_error.split(':', 1)[0]}")
    return ("pass" if not blockers else "fail"), blockers


def build_body_noplan_degraded_smoke_report(
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
        return report

    if reset_db and db_path.exists():
        db_path.unlink()
    engine, SessionLocal = _session_factory(db_path)
    provider = _NoCallManagerProvider()
    db = SessionLocal()
    app = _build_app(SessionLocal, provider)  # type: ignore[arg-type]
    port = _free_port()
    previous_debug_token = os.environ.get(LOCAL_DEBUG_API_TOKEN_ENV)
    local_debug_token = secrets.token_urlsafe(24)
    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = local_debug_token
    server, thread = _run_uvicorn_in_thread(app, port=port)
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-body.html")
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
        description="Run Body/Today no-plan degraded product-pages browser smoke."
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

    report = build_body_noplan_degraded_smoke_report(
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
