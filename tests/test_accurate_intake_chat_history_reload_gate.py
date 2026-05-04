from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_chat_history_reload_gate import (
    build_chat_history_reload_gate_report,
    main,
)


def test_chat_history_reload_gate_reads_messages_from_reopened_sqlite(tmp_path: Path) -> None:
    report = build_chat_history_reload_gate_report(db_path=tmp_path / "reload.sqlite3")

    assert report["gate_id"] == "accurate_intake_chat_history_reload_gate_v1"
    assert report["status"] == "pass"
    assert report["claim_scope"] == "local_deterministic_chat_history_reload_gate"
    assert report["evidence_scope"] == "sqlite_reload_read_model_and_trace_linkage"
    assert report["static_shell"]["contains_chat_history_endpoint"] is True
    assert report["static_shell"]["contains_frontend_non_owner_marker"] is True
    assert report["estimate"]["has_payload"] is True
    assert report["browser_executed"] is False
    assert report["frontend_semantic_owner"] is False
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_used"] is False
    assert report["production_db_used"] is False
    assert report["product_readiness_claimed"] is False

    before_history = report["before_reload"]["chat_history"]
    after_history = report["after_reload"]["chat_history"]
    assert before_history["message_count"] >= 2
    assert after_history["message_count"] == before_history["message_count"]
    assert after_history["source"] == "sqlite_message_buffer"
    assert after_history["frontend_semantic_owner"] is False
    assert after_history["long_term_memory_used"] is False
    assert after_history["proactive_or_rescue_used"] is False
    assert after_history["mutation_authority"] is False
    assert report["cjk_message"] in after_history["message_contents"]
    assert after_history["runtime_turn_trace_present"] is True
    assert after_history["context_snapshot_present"] is True
    assert after_history["trace_chain_complete"] is True
    assert after_history["context_policy_version"]
    assert after_history["loaded_context_summary_present"] is True
    assert after_history["omitted_context_summary_present"] is True
    assert after_history["pending_pins_present"] in {True, False}
    assert isinstance(after_history["target_candidate_count"], int)
    assert after_history["message_local_dates"] == [report["backend_local_date"]]


def test_chat_history_reload_gate_preserves_budget_and_debug_same_truth(tmp_path: Path) -> None:
    report = build_chat_history_reload_gate_report(db_path=tmp_path / "reload.sqlite3")

    before_budget = report["before_reload"]["today_budget"]
    after_budget = report["after_reload"]["today_budget"]
    after_debug = report["after_reload"]["debug"]

    assert before_budget["consumed_kcal"] > 0
    assert after_budget["consumed_kcal"] == before_budget["consumed_kcal"]
    assert after_budget["local_date"] == before_budget["local_date"] == report["backend_local_date"]
    assert after_debug["read_only"] is True
    assert after_debug["same_truth_status"] == "pass"
    assert after_debug["consumed_kcal"] == after_budget["consumed_kcal"]
    assert report["initial_manager_provider_call_count"] > 0
    assert report["reload_manager_provider_call_count"] == 0


def test_chat_history_reload_gate_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "reload-gate.json"
    db_path = tmp_path / "reload.sqlite3"

    exit_code = main(["--db-path", str(db_path), "--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "pass"
    assert artifact["after_reload"]["chat_history"]["source"] == "sqlite_message_buffer"
