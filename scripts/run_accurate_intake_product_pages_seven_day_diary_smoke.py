from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.canonical_persistence import commit_meal_payload_to_canonical  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.runtime.interface.local_debug_auth import LOCAL_DEBUG_API_TOKEN_ENV  # noqa: E402
from app.schemas import CommitRequestCandidate, MealItemPayload  # noqa: E402
from scripts.run_accurate_intake_product_pages_browser_smoke import (  # noqa: E402
    BrowserSmokeDependencyMissing,
    DeterministicSelfUseManagerProvider,
    _build_app,
    _capture_fetches,
    _free_port,
    _is_visible_product_text_clean,
    _load_sync_playwright,
    _nav_session_query_preserved,
    _open_page,
    _overflow_state,
    _page_url,
    _restore_runtime,
    _run_uvicorn_in_thread,
    _session_factory,
    _storage_state,
    _wait_for_http,
)


DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_seven_day_diary_smoke.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_product_pages_seven_day_diary_smoke.json"
DEFAULT_USER_ID = "product-pages-seven-day-user"
DEFAULT_START_DATE = "2026-05-01"
DEFAULT_DAY_COUNT = 7
DEFAULT_BUDGET_KCAL = 1500
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
    "private_self_use_approved",
]


def _iso_days(start_date: str, day_count: int) -> list[str]:
    start = date.fromisoformat(start_date)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(day_count)]


def _day_fixture(local_date: str, index: int, *, budget_kcal: int) -> dict[str, Any]:
    consumed_kcal = 300 + (index * 35)
    return {
        "local_date": local_date,
        "meal_title": f"fixture diary meal {index + 1} {local_date}",
        "raw_input": f"fixture diary meal day {index + 1}",
        "consumed_kcal": consumed_kcal,
        "remaining_kcal": budget_kcal - consumed_kcal,
        "budget_kcal": budget_kcal,
    }


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    browser_execution_required: bool,
    start_date: str,
    day_count: int,
    budget_kcal: int,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
        "claim_scope": "local_product_pages_seven_day_diary_browser_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "browser_execution_required": browser_execution_required,
        "start_date": start_date,
        "day_count_expected": day_count,
        "budget_kcal": budget_kcal,
        "browser_executed": False,
        "seven_day_window_checked": False,
        "day_count_checked": 0,
        "per_day_diary_isolated": False,
        "per_day_budget_values_checked": False,
        "today_date_strip_checked": False,
        "today_nav_date_preserved": False,
        "today_chat_link_date_preserved": False,
        "desktop_no_overflow": False,
        "mobile_no_overflow": False,
        "forbidden_storage_used": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "checked_days": [],
        "fetch_sequence": [],
    }


def _seed_seven_day_diary(
    db: Any,
    *,
    user_external_id: str,
    start_date: str,
    day_count: int,
    budget_kcal: int,
) -> list[dict[str, Any]]:
    user = get_or_create_user(db, user_external_id)
    fixtures = [
        _day_fixture(local_date, index, budget_kcal=budget_kcal)
        for index, local_date in enumerate(_iso_days(start_date, day_count))
    ]
    for index, fixture in enumerate(fixtures):
        commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=CommitRequestCandidate(
                request_id=f"seven-day-diary-{fixture['local_date']}",
                manager_intent="food_estimation",
                version_reason="new_intake",
                meal_title=str(fixture["meal_title"]),
                raw_input=str(fixture["raw_input"]),
                estimated_kcal=int(fixture["consumed_kcal"]),
                protein_g=20 + index,
                carb_g=40 + index,
                fat_g=10 + index,
                resolution_status="completed_meal",
                local_date=str(fixture["local_date"]),
                items=[
                    MealItemPayload(
                        name=str(fixture["meal_title"]),
                        source="llm",
                        evidence_role="unknown",
                        estimate_basis="llm_only",
                        confidence_tier="low",
                        estimated_kcal=int(fixture["consumed_kcal"]),
                    )
                ],
            ),
            budget_kcal=budget_kcal,
        )
    db.commit()
    return fixtures


def _chat_link_preserves_date(page: Any, *, user_external_id: str, local_date: str) -> bool:
    return bool(
        page.evaluate(
            """({ userExternalId, localDate }) => {
              const link = document.querySelector("#chat-link");
              if (!link) {
                return false;
              }
              const url = new URL(link.href, window.location.href);
              return url.pathname.endsWith("/static/accurate-intake-chat.html")
                && url.searchParams.get("user_id") === userExternalId
                && url.searchParams.get("local_date") === localDate
                && !url.searchParams.has("local_debug_token");
            }""",
            {"userExternalId": user_external_id, "localDate": local_date},
        )
    )


def _date_strip_marks_current(page: Any, *, local_date: str) -> bool:
    return bool(
        page.evaluate(
            """(localDate) => {
              const current = document.querySelector('#day-strip [aria-current="date"]');
              if (!current || current.getAttribute("aria-label") !== `Open ${localDate}`) {
                return false;
              }
              return document.querySelectorAll("#day-strip button").length === 7;
            }""",
            local_date,
        )
    )


def _today_metrics(page: Any, *, timeout_ms: int) -> dict[str, int]:
    return {
        "observed_budget_kcal": int(page.locator("#budget-kcal").inner_text(timeout=timeout_ms).strip()),
        "observed_consumed_kcal": int(page.locator("#consumed-kcal").inner_text(timeout=timeout_ms).strip()),
        "observed_remaining_kcal": int(page.locator("#remaining-kcal").inner_text(timeout=timeout_ms).strip()),
    }


def _run_browser_sequence(
    *,
    base_url: str,
    user_external_id: str,
    fixtures: list[dict[str, Any]],
    timeout_ms: int,
    headless: bool,
    local_debug_token: str,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    result: dict[str, Any] = {
        "current_step": "not_started",
        "checked_days": [],
        "fetch_sequence": [],
        "desktop_overflow": [],
        "mobile_overflow": [],
        "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            desktop_viewport = {"width": 1440, "height": 1000}
            mobile_viewport = {"width": 390, "height": 844}
            today = _open_page(
                browser,
                viewport=desktop_viewport,
                url=_page_url(
                    base_url,
                    "today",
                    user_external_id=user_external_id,
                    local_date=str(fixtures[0]["local_date"]),
                ),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            today.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
            desktop_overflows: list[dict[str, Any]] = []
            mobile_overflows: list[dict[str, Any]] = []
            nav_checks: list[bool] = []
            chat_link_checks: list[bool] = []
            date_strip_checks: list[bool] = []
            budget_checks: list[bool] = []
            isolation_checks: list[bool] = []

            for fixture in fixtures:
                local_date = str(fixture["local_date"])
                result["current_step"] = f"check_today_{local_date}"
                today.evaluate(
                    """(localDate) => {
                      const input = document.querySelector("#selected-date");
                      input.value = localDate;
                      input.dispatchEvent(new Event("change", { bubbles: true }));
                    }""",
                    local_date,
                )
                today.wait_for_function(
                    """(localDate) => document.querySelector("#selected-date")?.value === localDate""",
                    arg=local_date,
                    timeout=timeout_ms,
                )
                today.wait_for_function(
                    """(mealTitle) => (document.querySelector("#meal-list")?.textContent || "").includes(mealTitle)""",
                    arg=str(fixture["meal_title"]),
                    timeout=timeout_ms,
                )
                metrics = _today_metrics(today, timeout_ms=timeout_ms)
                meal_list_text = today.locator("#meal-list").inner_text(timeout=timeout_ms)
                other_titles = [
                    str(other["meal_title"])
                    for other in fixtures
                    if str(other["local_date"]) != local_date
                ]
                other_day_meal_leaked = any(title in meal_list_text for title in other_titles)
                budget_ok = (
                    metrics["observed_budget_kcal"] == int(fixture["budget_kcal"])
                    and metrics["observed_consumed_kcal"] == int(fixture["consumed_kcal"])
                    and metrics["observed_remaining_kcal"] == int(fixture["remaining_kcal"])
                )
                nav_ok = _nav_session_query_preserved(
                    today,
                    user_external_id=user_external_id,
                    local_date=local_date,
                )
                chat_link_ok = _chat_link_preserves_date(
                    today,
                    user_external_id=user_external_id,
                    local_date=local_date,
                )
                date_strip_ok = _date_strip_marks_current(today, local_date=local_date)

                checked = {
                    "local_date": local_date,
                    "expected_meal_title": str(fixture["meal_title"]),
                    "expected_budget_kcal": int(fixture["budget_kcal"]),
                    "expected_consumed_kcal": int(fixture["consumed_kcal"]),
                    "expected_remaining_kcal": int(fixture["remaining_kcal"]),
                    **metrics,
                    "other_day_meal_leaked": other_day_meal_leaked,
                    "nav_date_preserved": nav_ok,
                    "chat_link_date_preserved": chat_link_ok,
                    "date_strip_current": date_strip_ok,
                }
                result["checked_days"].append(checked)
                budget_checks.append(budget_ok)
                isolation_checks.append(not other_day_meal_leaked)
                nav_checks.append(nav_ok)
                chat_link_checks.append(chat_link_ok)
                date_strip_checks.append(date_strip_ok)

            today_text = today.locator("body").inner_text(timeout=timeout_ms)
            result["today_no_debug_trace"] = _is_visible_product_text_clean(today_text)
            result["fetch_sequence"].extend(_capture_fetches(today))
            desktop_overflows.append(_overflow_state(today))
            storage = _storage_state(today)
            result["storage"]["localStorageKeys"].extend(storage.get("localStorageKeys", []))
            result["storage"]["sessionStorageKeys"].extend(storage.get("sessionStorageKeys", []))
            today.close()

            for fixture in (fixtures[0], fixtures[-1]):
                mobile = _open_page(
                    browser,
                    viewport=mobile_viewport,
                    url=_page_url(
                        base_url,
                        "today",
                        user_external_id=user_external_id,
                        local_date=str(fixture["local_date"]),
                    ),
                    timeout_ms=timeout_ms,
                    local_debug_token=local_debug_token,
                )
                mobile.wait_for_function(
                    """(mealTitle) => (document.querySelector("#meal-list")?.textContent || "").includes(mealTitle)""",
                    arg=str(fixture["meal_title"]),
                    timeout=timeout_ms,
                )
                mobile_overflows.append(_overflow_state(mobile))
                result["fetch_sequence"].extend(_capture_fetches(mobile))
                mobile.close()

            result["day_count_checked"] = len(result["checked_days"])
            result["seven_day_window_checked"] = len(result["checked_days"]) == len(fixtures)
            result["per_day_diary_isolated"] = bool(isolation_checks) and all(isolation_checks)
            result["per_day_budget_values_checked"] = bool(budget_checks) and all(budget_checks)
            result["today_date_strip_checked"] = bool(date_strip_checks) and all(date_strip_checks)
            result["today_nav_date_preserved"] = bool(nav_checks) and all(nav_checks)
            result["today_chat_link_date_preserved"] = bool(chat_link_checks) and all(chat_link_checks)
            result["desktop_overflow"] = desktop_overflows
            result["mobile_overflow"] = mobile_overflows
            result["desktop_no_overflow"] = all(
                state.get("documentScrollWidth") == state.get("viewport")
                and not state.get("overflowingElements")
                for state in desktop_overflows
            )
            result["mobile_no_overflow"] = all(
                state.get("documentScrollWidth") == state.get("viewport")
                and not state.get("overflowingElements")
                for state in mobile_overflows
            )
            result["forbidden_storage_used"] = bool(
                result["storage"]["localStorageKeys"] or result["storage"]["sessionStorageKeys"]
            )
            result["current_step"] = "complete"
            return result
        except Exception as exc:
            result["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
            return result
        finally:
            browser.close()


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []

    def require_true(key: str, blocker: str) -> None:
        if report.get(key) is not True:
            blockers.append(blocker)

    require_true("browser_executed", "browser_not_executed")
    require_true("seven_day_window_checked", "seven_day_window_not_checked")
    require_true("per_day_diary_isolated", "per_day_diary_not_isolated")
    require_true("per_day_budget_values_checked", "per_day_budget_values_not_checked")
    require_true("today_date_strip_checked", "today_date_strip_not_checked")
    require_true("today_nav_date_preserved", "today_nav_date_not_preserved")
    require_true("today_chat_link_date_preserved", "today_chat_link_date_not_preserved")
    require_true("desktop_no_overflow", "desktop_overflow_detected")
    require_true("mobile_no_overflow", "mobile_overflow_detected")

    checked_days = list(report.get("checked_days") or [])
    if int(report.get("day_count_checked") or 0) != 7 or len(checked_days) != 7:
        blockers.append("seven_day_window_incomplete")
    for day in checked_days:
        if not isinstance(day, dict):
            blockers.append("checked_day_not_object")
            continue
        if day.get("other_day_meal_leaked") is True:
            blockers.append(f"other_day_meal_leaked:{day.get('local_date')}")
        if int(day.get("observed_consumed_kcal") or -1) != int(day.get("expected_consumed_kcal") or -2):
            blockers.append(f"consumed_mismatch:{day.get('local_date')}")
        if int(day.get("observed_remaining_kcal") or -1) != int(day.get("expected_remaining_kcal") or -2):
            blockers.append(f"remaining_mismatch:{day.get('local_date')}")

    for key in (
        "frontend_semantic_owner",
        "live_llm_invoked",
        "web_tavily_used",
        "production_db_used",
        "web_readiness_claimed",
        "product_readiness_claimed",
        "private_self_use_approved",
        "forbidden_storage_used",
    ):
        if report.get(key) is True:
            blockers.append(key)

    fetches = list(report.get("fetch_sequence") or [])
    fetch_urls = [str(item.get("url") or "") for item in fetches if isinstance(item, dict)]
    if int(report.get("manager_provider_call_count") or 0) != 0:
        blockers.append("manager_provider_called")
    if any("/estimate" in url for url in fetch_urls):
        blockers.append("estimate_fetch_unexpected")
    for day in checked_days:
        local_date = str(day.get("local_date") or "")
        if local_date and not any("/today/current-budget" in url and f"local_date={local_date}" in url for url in fetch_urls):
            blockers.append(f"today_fetch_missing:{local_date}")

    sequence_error = str(report.get("browser_sequence_error") or "")
    if sequence_error:
        blockers.append(f"browser_sequence_error:{sequence_error.split(':', 1)[0]}")
    return ("pass" if not blockers else "fail"), blockers


def build_seven_day_diary_smoke_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    user_external_id: str = DEFAULT_USER_ID,
    start_date: str = DEFAULT_START_DATE,
    day_count: int = DEFAULT_DAY_COUNT,
    budget_kcal: int = DEFAULT_BUDGET_KCAL,
    reset_db: bool = True,
    require_browser_execution: bool = False,
    timeout_ms: int = 15000,
    headless: bool = True,
) -> dict[str, Any]:
    report = _base_report(
        user_external_id=user_external_id,
        db_path=db_path,
        browser_execution_required=require_browser_execution,
        start_date=start_date,
        day_count=day_count,
        budget_kcal=budget_kcal,
    )
    try:
        _load_sync_playwright()
    except BrowserSmokeDependencyMissing:
        report["status"] = "blocked" if not require_browser_execution else "fail"
        report["blockers"] = ["playwright_not_installed"]
        report["operator_action"] = "Install Playwright locally and rerun; this artifact must not claim web readiness."
        return report

    if reset_db and db_path.exists():
        db_path.unlink()
    engine, SessionLocal = _session_factory(db_path)
    provider = DeterministicSelfUseManagerProvider()
    db = SessionLocal()
    app = _build_app(SessionLocal, provider)
    port = _free_port()
    previous_debug_token = os.environ.get(LOCAL_DEBUG_API_TOKEN_ENV)
    local_debug_token = secrets.token_urlsafe(24)
    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = local_debug_token
    server, thread = _run_uvicorn_in_thread(app, port=port)
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-today.html")
        fixtures = _seed_seven_day_diary(
            db,
            user_external_id=user_external_id,
            start_date=start_date,
            day_count=day_count,
            budget_kcal=budget_kcal,
        )
        browser_result = _run_browser_sequence(
            base_url=base_url,
            user_external_id=user_external_id,
            fixtures=fixtures,
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
    parser = argparse.ArgumentParser(description="Run seven-day browser smoke for the Accurate Intake Today page.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--day-count", type=int, default=DEFAULT_DAY_COUNT)
    parser.add_argument("--budget-kcal", type=int, default=DEFAULT_BUDGET_KCAL)
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args(argv)

    report = build_seven_day_diary_smoke_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        start_date=args.start_date,
        day_count=args.day_count,
        budget_kcal=args.budget_kcal,
        reset_db=not args.keep_db,
        require_browser_execution=args.require_browser_execution,
        timeout_ms=args.timeout_ms,
        headless=not args.headed,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if report["status"] == "pass":
        return 0
    if report["status"] == "blocked" and not args.require_browser_execution:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
