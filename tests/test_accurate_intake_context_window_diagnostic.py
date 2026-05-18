from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_window_diagnostic import (
    build_context_window_diagnostic_artifact,
)


def test_context_window_diagnostic_reports_limits_pins_and_exclusions() -> None:
    artifact = build_context_window_diagnostic_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_window_diagnostic"
    assert artifact["status"] == "generated"
    assert artifact["diagnostic_only"] is True
    assert artifact["context_policy_version"] == "accurate_intake_mvp_context_policy_v1"
    assert artifact["recent_window_policy"]["mode"] == "token_budgeted"
    assert artifact["recent_window_policy"]["last_messages"] == 20
    assert artifact["recent_window_policy"]["max_chars"] == 6000
    assert artifact["recent_window_policy"]["token_budget"] == 2000
    assert artifact["recent_chat_messages_loaded"] <= 20
    assert artifact["recent_chat_messages_omitted"] > 0
    assert artifact["loaded_estimated_tokens"] <= artifact["token_budget"]
    assert artifact["char_limit_applied"] is True
    assert artifact["pending_followup_hard_pinned"] is True
    assert artifact["pending_draft_hard_pinned"] is True
    assert "long_term_memory" in artifact["forbidden_context_excluded"]
    assert "raw_trace_dump" in artifact["forbidden_context_excluded"]
    assert artifact["long_term_memory_used"] is False
    assert artifact["proactive_or_rescue_used"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["manager_context_packet_schema_changed"] is False


def test_context_window_diagnostic_builder_script_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "context_window.json"

    from scripts.run_accurate_intake_context_window_diagnostic import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "generated"
    assert artifact["pending_followup_hard_pinned"] is True
