from __future__ import annotations

from scripts import select_product_pages_browser_e2e_mode as selector


def test_shadow_memory_and_docs_changes_fast_pass_browser_e2e() -> None:
    decision = selector.select_mode(
        changed_files=[
            "app/memory/application/runtime_lab_consumer_summary_pack.py",
            "tests/test_runtime_lab_memory_consumer_summary_pack.py",
            "docs/quality/ADVANCED_MEMORY_SHADOW_LAB.md",
        ],
        diff_text="",
        event_name="pull_request",
    )

    assert decision["mode"] == "fast_pass"
    assert decision["reason"] == "changed files are browser-unrelated"


def test_rescue_shadow_context_change_fast_passes_browser_e2e() -> None:
    decision = selector.select_mode(
        changed_files=[
            "app/rescue/application/shadow_summary_context.py",
            "tests/test_rescue_shadow_summary_context.py",
        ],
        diff_text="",
        event_name="merge_group",
    )

    assert decision["mode"] == "fast_pass"


def test_proactive_no_send_summary_consumer_fast_passes_browser_e2e() -> None:
    decision = selector.select_mode(
        changed_files=[
            "app/runtime/application/proactive_summary_consumer.py",
            "tests/test_proactive_no_send_summary_consumer.py",
            "tests/test_sidecar_offline_activation_guard.py",
        ],
        diff_text="",
        event_name="merge_group",
    )

    assert decision["mode"] == "fast_pass"


def test_advanced_shadow_lab_sidecar_change_fast_passes_browser_e2e() -> None:
    decision = selector.select_mode(
        changed_files=[
            "app/advanced_shadow_lab/chat_ux_copy_alignment.py",
            "app/advanced_shadow_lab/chat_ux_packet.py",
            "app/advanced_shadow_lab/shadow_comparison.py",
            "app/advanced_shadow_lab/shadow_comparison_live_rows.py",
            "scripts/run_advanced_shadow_lab_live_bundle.py",
            "tests/test_advanced_shadow_lab_chat_ux_packet.py",
            "tests/test_advanced_shadow_lab_comparison_runner.py",
            "tests/test_advanced_shadow_lab_live_bundle_runner.py",
            "tests/test_advanced_shadow_lab_shadow_comparison.py",
            "tests/test_sidecar_offline_activation_guard.py",
        ],
        diff_text="",
        event_name="pull_request",
    )

    assert decision["mode"] == "fast_pass"
    assert decision["reason"] == "changed files are browser-unrelated"


def test_product_page_static_change_requires_full_browser_e2e() -> None:
    decision = selector.select_mode(
        changed_files=["static/accurate-intake-today.html"],
        diff_text="",
        event_name="pull_request",
    )

    assert decision["mode"] == "full"
    assert decision["matched_paths"] == ["static/accurate-intake-today.html"]


def test_runtime_consumed_payload_token_requires_full_browser_e2e() -> None:
    decision = selector.select_mode(
        changed_files=["app/runtime/application/request_trace_artifacts.py"],
        diff_text="+    payload['coach_message'] = coach_message",
        event_name="pull_request",
    )

    assert decision["mode"] == "full"
    assert decision["matched_diff_tokens"] == ["coach_message"]


def test_unknown_active_app_change_defaults_to_full_browser_e2e() -> None:
    decision = selector.select_mode(
        changed_files=["app/composition/intake_routes.py"],
        diff_text="",
        event_name="pull_request",
    )

    assert decision["mode"] == "full"
    assert decision["reason"] == "unknown active code change defaults to full browser run"


def test_main_push_defaults_to_full_browser_e2e_even_without_changed_files() -> None:
    decision = selector.select_mode(
        changed_files=[],
        diff_text="",
        event_name="push",
    )

    assert decision["mode"] == "full"
    assert decision["reason"] == "main push keeps full browser guard"


def test_ci_workflow_keeps_required_check_but_gates_playwright_install() -> None:
    workflow = selector.ROOT.joinpath(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e:" in workflow
    assert "Select product pages browser E2E mode" in workflow
    assert "id: browser_mode" in workflow
    assert "if: steps.browser_mode.outputs.mode == 'full'" in workflow
    assert "if: steps.browser_mode.outputs.mode == 'fast_pass'" in workflow
    assert "python -m playwright install --with-deps chromium" in workflow
