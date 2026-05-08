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
from app.composition.non_fooddb_read_only_turn import NON_FOODDB_READ_ONLY_MANAGER_TOOLS  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.runtime.interface.local_debug_auth import LOCAL_DEBUG_API_TOKEN_ENV  # noqa: E402
from scripts.run_accurate_intake_browser_shell_smoke import (  # noqa: E402
    BrowserSmokeDependencyMissing,
    _build_app,
    _free_port,
    _load_sync_playwright,
    _restore_runtime,
    _run_uvicorn_in_thread,
    _seed_body_plan,
    _session_factory,
    _wait_for_http,
)
from scripts.run_accurate_intake_product_pages_browser_smoke import (  # noqa: E402
    _capture_fetches,
    _is_visible_product_text_clean,
    _open_page,
    _page_url,
)


DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_short_term_context_smoke.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_product_pages_short_term_context_smoke.json"
DEFAULT_USER_ID = "product-pages-short-term-context-user"
DEFAULT_LOCAL_DATE = resolve_today_local_date(None)
BARE_BASKET_MESSAGE = "晚餐吃滷味"
FOLLOWUP_ANSWER_MESSAGE = "有豆干、海帶、貢丸"
FOLLOWUP_QUESTION = "請列出滷味裡有哪些品項和大概份量。"
REQUIRED_FETCH_PREFIXES = (
    "/accurate-intake/chat-history",
    "/estimate",
    "/accurate-intake/debug",
    "/today/current-budget",
)
def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _context_input_summary(user_payload: dict[str, Any], *, stage: str, round_index: int) -> dict[str, Any]:
    packet = _dict(user_payload.get("manager_context_packet_v1"))
    prompt_kind = str(packet.get("prompt_payload_kind") or "")
    metadata = _dict(packet.get("metadata"))
    loading = _dict(packet.get("context_loading_artifact"))
    loaded = _dict(loading.get("loaded_context_summary"))
    omitted = _dict(loading.get("omitted_context_summary"))
    recent_chat_window = _dict(packet.get("recent_chat_window"))
    hard_pins = _dict(packet.get("hard_pins"))
    target_candidates = _dict(packet.get("target_candidates"))
    correction_targets = _list(target_candidates.get("for_correction_or_removal"))
    compact_loaded_present = prompt_kind == "manager_context_packet_v1_prompt_compact" and (
        bool(_list(recent_chat_window.get("messages")))
        or recent_chat_window.get("loaded_message_count") is not None
    )
    compact_omitted_present = prompt_kind == "manager_context_packet_v1_prompt_compact" and (
        recent_chat_window.get("omitted_count") is not None
        or recent_chat_window.get("char_truncated") is not None
        or bool(recent_chat_window.get("token_budget_status"))
    )
    compact_forbidden_context_excluded = prompt_kind == "manager_context_packet_v1_prompt_compact" and all(
        marker not in json.dumps(packet, ensure_ascii=False)
        for marker in ("debug_artifacts", "dogfood_review_artifacts", "food_gap_candidates")
    )
    return {
        "stage": stage,
        "round_index": round_index,
        "prompt_payload_kind": prompt_kind,
        "available_tools": sorted(str(item) for item in _list(user_payload.get("available_tools"))),
        "context_policy_version_present": bool(metadata.get("context_policy_version")),
        "loaded_context_summary_present": bool(loaded) or compact_loaded_present,
        "omitted_context_summary_present": bool(omitted) or compact_omitted_present,
        "pending_followup_pin_present": bool(_dict(hard_pins.get("pending_followup"))),
        "pending_draft_pin_present": bool(_dict(hard_pins.get("pending_draft"))),
        "target_candidate_count": len(correction_targets),
        "forbidden_context_excluded": all(
            item in omitted.get("policy_excluded_context_ids", [])
            for item in ("debug_artifacts", "dogfood_review_artifacts", "food_gap_candidates")
        )
        or compact_forbidden_context_excluded,
        "raw_user_input_recorded_only": str(user_payload.get("raw_user_input") or ""),
        "raw_user_input_used_for_fixture_selection": False,
    }


class _ShortTermContextManagerProvider:
    """Fake Manager fixture. It chooses the next scripted turn by call order, never raw text."""

    def __init__(self) -> None:
        self.turn_index = -1
        self.active_turn = "bare_basket_followup"
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "short_term_context_fake_manager_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = _dict(kwargs.get("user_payload"))
        available_tools = {str(item) for item in _list(user_payload.get("available_tools"))}
        round_index = int(user_payload.get("round_index") or 0)
        is_entry = bool(set(NON_FOODDB_READ_ONLY_MANAGER_TOOLS).intersection(available_tools))
        if is_entry:
            self.turn_index += 1
            self.active_turn = "bare_basket_followup" if self.turn_index == 0 else "followup_answer_commit"
        stage = "entry" if is_entry else self.active_turn
        if self.active_turn == "followup_answer_commit" and not is_entry:
            stage = "execution_after_followup"
        self.calls.append(_context_input_summary(user_payload, stage=stage, round_index=round_index))

        if is_entry:
            return self._entry_decision(), self._trace(stage)
        if self.active_turn == "bare_basket_followup":
            return self._ask_followup(), self._trace(stage)
        if round_index == 0 and "estimate_nutrition" in available_tools:
            calls = [{"name": "estimate_nutrition"}]
            if "compare_against_budget" in available_tools:
                calls.append({"name": "compare_against_budget"})
            return {"manager_action": "call_tools", "response_mode": "tool_call", "tool_calls": calls}, self._trace(stage)
        return self._commit_final(), self._trace(stage)

    def _trace(self, stage: str) -> dict[str, Any]:
        return {
            "source": "short_term_context_fake_manager_fixture",
            "stage": stage,
            "fixture_manager_used": True,
            "live_llm_invoked": False,
            "raw_user_input_used_for_fixture_selection": False,
        }

    def _entry_decision(self) -> dict[str, Any]:
        return self._final(
            current_turn_intent="log_meal",
            final_action="route_to_intake",
            workflow_effect="route_to_intake",
            mutation_intent_candidate="canonical_write",
            target_attachment={"mode": "new_meal"},
            estimation_posture="needs_manager_execution",
            evidence_posture="needs_tool_evidence",
            reply_text="route_to_intake",
        )

    def _ask_followup(self) -> dict[str, Any]:
        return self._final(
            current_turn_intent="log_meal",
            final_action="ask_followup",
            workflow_effect="ask_followup",
            mutation_intent_candidate="no_mutation",
            target_attachment={"mode": "new_meal"},
            estimation_posture="insufficient_details",
            evidence_posture="composition_unknown",
            reply_text=FOLLOWUP_QUESTION,
            followup_question=FOLLOWUP_QUESTION,
            meal_title="滷味",
        )

    def _commit_final(self) -> dict[str, Any]:
        return self._final(
            current_turn_intent="log_meal",
            final_action="commit",
            workflow_effect="commit",
            mutation_intent_candidate="canonical_write",
            target_attachment={"mode": "pending_draft"},
            estimation_posture="estimable",
            evidence_posture="tool_evidence_present",
            reply_text="已記錄這份滷味。",
            meal_title="滷味：豆干、海帶、貢丸",
        )

    def _final(
        self,
        *,
        current_turn_intent: str,
        final_action: str,
        workflow_effect: str,
        mutation_intent_candidate: str,
        target_attachment: dict[str, Any],
        estimation_posture: str,
        evidence_posture: str,
        reply_text: str,
        followup_question: str | None = None,
        meal_title: str | None = None,
    ) -> dict[str, Any]:
        semantic_decision = {
            "semantic_authority": "deterministic_fake_provider",
            "current_turn_intent": current_turn_intent,
            "target_attachment": dict(target_attachment),
            "workflow_effect": workflow_effect,
            "final_action_candidate": final_action,
            "estimation_posture": estimation_posture,
            "followup_posture": "ask_required" if followup_question else "none",
            "mutation_intent_candidate": mutation_intent_candidate,
            "uncertainty_posture": "high" if followup_question else "bounded",
            "source": "short_term_context_fake_manager_fixture",
            "semantic_owner": "manager_fixture",
            "deterministic_role": "fixture_sequence_only",
        }
        if followup_question:
            semantic_decision["followup_question"] = followup_question
        if meal_title:
            semantic_decision["meal_title"] = meal_title
        answer_contract = {"reply_text": reply_text}
        if followup_question:
            answer_contract["followup_question"] = followup_question
        if meal_title:
            answer_contract["meal_title"] = meal_title
        return {
            "manager_action": "final",
            "intent": "log_meal",
            "intent_type": "log_meal",
            "final_action": final_action,
            "workflow_effect": workflow_effect,
            "target_attachment": dict(target_attachment),
            "exactness": "fake_provider_fixture",
            "confidence": "medium",
            "evidence_posture": evidence_posture,
            "repair_ack": False,
            "answer_contract": answer_contract,
            "response_summary": reply_text,
            "uncertainty_posture": semantic_decision["uncertainty_posture"],
            "evidence_honesty_posture": evidence_posture,
            "semantic_decision": semantic_decision,
        }


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    local_date: str,
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_product_pages_short_term_context_smoke_v1",
        "claim_scope": "local_product_pages_short_term_context_browser_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "local_date": local_date,
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "browser_reload_checked": False,
        "fixture_manager_used": True,
        "pending_followup_created": False,
        "pending_followup_reloaded": False,
        "context_policy_version_present": False,
        "loaded_context_summary_present": False,
        "omitted_context_summary_present": False,
        "pending_pins_present_after_followup": False,
        "target_candidates_present_or_not_checked": "not_checked",
        "chat_history_context_fields_reloaded": False,
        "chat_context_status_ui_rendered": False,
        "chat_cjk_roundtrip_rendered": False,
        "assistant_followup_bubble_rendered": False,
        "assistant_commit_bubble_rendered": False,
        "today_same_day_meal_rendered": False,
        "today_summary_rendered": False,
        "product_pages_no_debug_trace": False,
        "fetch_sequence": [],
        "fake_provider_calls": [],
    }


def _fetch_json_with_debug_token(page: Any, path: str, *, user_external_id: str, local_date: str, token: str) -> dict[str, Any]:
    return _dict(
        page.evaluate(
            """async ({ path, userId, localDate, token }) => {
              const query = new URLSearchParams({ user_id: userId, local_date: localDate });
              const response = await fetch(`${path}?${query.toString()}`, {
                headers: { "X-Local-Debug-Token": token }
              });
              return await response.json();
            }""",
            {"path": path, "userId": user_external_id, "localDate": local_date, "token": token},
        )
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
        "product_page_text": "",
        "debug_payload": {},
        "chat_history_payload": {},
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

            result["current_step"] = "ask_bare_basket_followup"
            chat.fill("#message-input", BARE_BASKET_MESSAGE)
            chat.click("#send-button")
            chat.wait_for_function(
                """(question) => (document.querySelector("#chat-scroll")?.textContent || "").includes(question)""",
                arg=FOLLOWUP_QUESTION,
                timeout=timeout_ms,
            )
            chat_text_after_followup = chat.locator("#chat-scroll").inner_text(timeout=timeout_ms)
            result["assistant_followup_bubble_rendered"] = FOLLOWUP_QUESTION in chat_text_after_followup
            result["chat_cjk_roundtrip_rendered"] = BARE_BASKET_MESSAGE in chat_text_after_followup

            debug_after_followup = _fetch_json_with_debug_token(
                chat,
                "/accurate-intake/debug",
                user_external_id=user_external_id,
                local_date=local_date,
                token=local_debug_token,
            )
            result["fetch_sequence"].append(
                {
                    "url": f"/accurate-intake/debug?user_id={user_external_id}&local_date={local_date}",
                    "method": "GET",
                    "body": None,
                    "source": "script_debug_fetch",
                }
            )
            result["debug_payload"] = debug_after_followup
            pending_drafts = _list(_dict(debug_after_followup.get("model")).get("pending_drafts"))
            result["pending_followup_created"] = bool(pending_drafts)
            result["fetch_sequence"].extend(_capture_fetches(chat))

            result["current_step"] = "reload_pending_followup_chat"
            chat.reload(wait_until="networkidle", timeout=timeout_ms)
            chat.wait_for_function(
                """({ message, question }) => {
                  const text = document.querySelector("#chat-scroll")?.textContent || "";
                  return text.includes(message) && text.includes(question);
                }""",
                arg={"message": BARE_BASKET_MESSAGE, "question": FOLLOWUP_QUESTION},
                timeout=timeout_ms,
            )
            result["browser_reload_checked"] = True
            history_after_reload = _fetch_json_with_debug_token(
                chat,
                "/accurate-intake/chat-history",
                user_external_id=user_external_id,
                local_date=local_date,
                token=local_debug_token,
            )
            result["chat_history_payload"] = history_after_reload
            history_messages = _list(history_after_reload.get("messages"))
            result["pending_followup_reloaded"] = any(
                message.get("structured_followup_question") == FOLLOWUP_QUESTION
                or message.get("pending_followup_linkage_present") is True
                for message in history_messages
                if isinstance(message, dict)
            )
            result["pending_followup_created"] = (
                result["pending_followup_created"] or result["pending_followup_reloaded"]
            )
            result["context_policy_version_present"] = any(
                bool(_dict(message).get("context_policy_version")) for message in history_messages
            )
            result["loaded_context_summary_present"] = any(
                bool(_dict(_dict(message).get("loaded_context_summary"))) for message in history_messages
            )
            result["omitted_context_summary_present"] = any(
                bool(_dict(_dict(message).get("omitted_context_summary"))) for message in history_messages
            )
            result["chat_history_context_fields_reloaded"] = all(
                result.get(key) is True
                for key in (
                    "context_policy_version_present",
                    "loaded_context_summary_present",
                    "omitted_context_summary_present",
                )
            )
            ui_policy = chat.locator("#chat-context-policy").inner_text(timeout=timeout_ms).strip()
            ui_loaded = chat.locator("#chat-context-loaded").inner_text(timeout=timeout_ms).strip()
            ui_omitted = chat.locator("#chat-context-omitted").inner_text(timeout=timeout_ms).strip()
            ui_pins = chat.locator("#chat-context-pins").inner_text(timeout=timeout_ms).strip()
            ui_targets = chat.locator("#chat-context-targets").inner_text(timeout=timeout_ms).strip()
            result["chat_context_status_ui"] = {
                "policy": ui_policy,
                "loaded": ui_loaded,
                "omitted": ui_omitted,
                "pins": ui_pins,
                "targets": ui_targets,
            }
            result["chat_context_status_ui_rendered"] = (
                ui_policy not in {"", "not_checked"}
                and ui_loaded in {"present", "not_available"}
                and ui_omitted in {"present", "not_available"}
                and ui_pins in {"present", "not_available"}
                and ui_targets not in {"", "not_checked"}
            )

            result["current_step"] = "answer_pending_followup"
            chat.fill("#message-input", FOLLOWUP_ANSWER_MESSAGE)
            chat.click("#send-button")
            chat.wait_for_function(
                """(reply) => (document.querySelector("#chat-scroll")?.textContent || "").includes(reply)""",
                arg="Logged.",
                timeout=timeout_ms,
            )
            final_chat_text = chat.locator("body").inner_text(timeout=timeout_ms)
            result["assistant_commit_bubble_rendered"] = "Logged." in final_chat_text
            result["chat_cjk_roundtrip_rendered"] = (
                result["chat_cjk_roundtrip_rendered"] and FOLLOWUP_ANSWER_MESSAGE in final_chat_text
            )
            result["product_pages_no_debug_trace"] = _is_visible_product_text_clean(final_chat_text)
            result["fetch_sequence"].extend(_capture_fetches(chat))
            chat.close()

            result["current_step"] = "open_today"
            today = _open_page(
                browser,
                viewport=viewport,
                url=_page_url(base_url, "today", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            today.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
            today.wait_for_function(
                """() => document.querySelector("#budget-kcal")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )
            today.wait_for_function(
                """(message) => (document.querySelector("#meal-list")?.textContent || "").includes(message)""",
                arg=FOLLOWUP_ANSWER_MESSAGE,
                timeout=timeout_ms,
            )
            today_text = today.locator("body").inner_text(timeout=timeout_ms)
            result["today_summary_rendered"] = all(
                today.locator(selector).inner_text(timeout=timeout_ms).strip() != "--"
                for selector in ("#budget-kcal", "#consumed-kcal", "#remaining-kcal")
            )
            result["today_same_day_meal_rendered"] = FOLLOWUP_ANSWER_MESSAGE in today_text and "kcal" in today_text
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


def _fetch_urls(report: dict[str, Any]) -> list[str]:
    browser = _dict(report.get("browser"))
    sequence = _list(browser.get("fetch_sequence")) or _list(report.get("fetch_sequence"))
    return [str(item.get("url") or "") for item in sequence if isinstance(item, dict)]


def _estimate_post_bodies(report: dict[str, Any]) -> list[dict[str, Any]]:
    browser = _dict(report.get("browser"))
    sequence = _list(browser.get("fetch_sequence")) or _list(report.get("fetch_sequence"))
    bodies: list[dict[str, Any]] = []
    for item in sequence:
        if not isinstance(item, dict):
            continue
        if str(item.get("method") or "GET").upper() != "POST":
            continue
        if "/estimate" not in str(item.get("url") or ""):
            continue
        try:
            body = json.loads(str(item.get("body") or "{}"))
        except json.JSONDecodeError:
            body = {}
        if isinstance(body, dict):
            bodies.append(body)
    return bodies


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []

    def require_true(key: str, blocker: str) -> None:
        if report.get(key) is not True:
            blockers.append(blocker)

    require_true("browser_executed", "browser_not_executed")
    require_true("browser_reload_checked", "browser_reload_not_checked")
    require_true("fixture_manager_used", "fixture_manager_not_used")
    require_true("pending_followup_created", "pending_followup_not_created")
    require_true("pending_followup_reloaded", "pending_followup_not_reloaded")
    require_true("context_policy_version_present", "context_policy_version_missing")
    require_true("loaded_context_summary_present", "loaded_context_summary_missing")
    require_true("omitted_context_summary_present", "omitted_context_summary_missing")
    require_true("pending_pins_present_after_followup", "pending_pins_not_present_after_followup")
    require_true("chat_history_context_fields_reloaded", "chat_history_context_fields_not_reloaded")
    require_true("chat_context_status_ui_rendered", "chat_context_status_ui_not_rendered")
    require_true("chat_cjk_roundtrip_rendered", "chat_cjk_roundtrip_not_rendered")
    require_true("assistant_followup_bubble_rendered", "assistant_followup_bubble_not_rendered")
    require_true("assistant_commit_bubble_rendered", "assistant_commit_bubble_not_rendered")
    require_true("today_same_day_meal_rendered", "today_same_day_meal_not_rendered")
    require_true("today_summary_rendered", "today_summary_not_rendered")
    require_true("product_pages_no_debug_trace", "product_pages_debug_trace_leaked")

    provider_calls = [item for item in _list(report.get("fake_provider_calls")) if isinstance(item, dict)]
    if not any(
        call.get("context_policy_version_present") is True
        and call.get("loaded_context_summary_present") is True
        and call.get("omitted_context_summary_present") is True
        for call in provider_calls
    ):
        blockers.append("fake_provider_context_input_not_proven")
    if not any(
        call.get("pending_followup_pin_present") is True or call.get("pending_draft_pin_present") is True
        for call in provider_calls
    ):
        blockers.append("fake_provider_pending_pin_input_not_proven")
    if any(call.get("raw_user_input_used_for_fixture_selection") is True for call in provider_calls):
        blockers.append("fake_provider_used_raw_user_input_for_fixture_selection")

    fetch_urls = _fetch_urls(report)
    for prefix in REQUIRED_FETCH_PREFIXES:
        if not any(prefix in url for url in fetch_urls):
            blockers.append(f"required_fetch_missing:{prefix}")
    estimate_bodies = _estimate_post_bodies(report)
    local_date = str(report.get("local_date") or DEFAULT_LOCAL_DATE)
    if not any(body.get("text") == BARE_BASKET_MESSAGE for body in estimate_bodies):
        blockers.append("estimate_post_missing:bare_basket")
    if not any(body.get("text") == FOLLOWUP_ANSWER_MESSAGE for body in estimate_bodies):
        blockers.append("estimate_post_missing:followup_answer")
    if not estimate_bodies or any(body.get("local_date") != local_date for body in estimate_bodies):
        blockers.append("estimate_post_missing_selected_local_date")
    if any('"allow_search":true' in str(item).replace(" ", "").lower() for item in _list(_dict(report.get("browser")).get("fetch_sequence"))):
        blockers.append("allow_search_true_used")
    sequence_error = str(_dict(report.get("browser")).get("browser_sequence_error") or report.get("browser_sequence_error") or "")
    if sequence_error:
        blockers.append(f"browser_sequence_error:{sequence_error.split(':', 1)[0]}")
    return ("pass" if not blockers else "fail"), blockers


def build_product_pages_short_term_context_smoke_report(
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
    provider = _ShortTermContextManagerProvider()
    db = SessionLocal()
    app = _build_app(db, provider)
    port = _free_port()
    previous_debug_token = os.environ.get(LOCAL_DEBUG_API_TOKEN_ENV)
    local_debug_token = secrets.token_urlsafe(24)
    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = local_debug_token
    server, thread = _run_uvicorn_in_thread(app, port=port)
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-chat.html")
        get_or_create_user(db, user_external_id)
        _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
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
        report["fake_provider_calls"] = provider.calls
        report["manager_provider_call_count"] = len(provider.calls)
        report["pending_pins_present_after_followup"] = any(
            call.get("pending_followup_pin_present") is True or call.get("pending_draft_pin_present") is True
            for call in provider.calls
        )
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
        description="Run product-pages browser smoke for short-term Manager context support."
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

    report = build_product_pages_short_term_context_smoke_report(
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
