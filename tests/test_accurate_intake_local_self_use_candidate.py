from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_local_self_use_candidate import (
    build_local_self_use_candidate_packet,
    main,
)


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK_PATH = ROOT / "docs" / "quality" / "ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md"
_REMOVED_FIXED_FALSE_FIELDS = (
    "private_self_use_approved",
    "live_manager_required",
    "production_selected",
    "product_readiness_claimed",
    "mutation_rollout_approved",
    "live_llm_invoked",
    "web_tavily_invoked",
    "production_db_used",
)


def _valid_shell_artifact() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "shell_id": "accurate_intake_local_self_use_shell_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass",
        "blockers": [],
        "scenario": "one_day_v1",
        "manager_mode": "fixture",
        "runner_inferred_semantics": False,
        "raw_text_routing_used": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "scenario_artifact": {
            "status": "pass",
            "scenario_id": "one_day_self_use_v1",
            "turn_count": 9,
            "final_summary": {
                "consumed_kcal": 1670,
                "remaining_kcal": 130,
            },
        },
        "operator_surface": {
            "read_only": True,
            "truth_source": "canonical_debug_read_model",
            "today_summary": {
                "consumed_kcal": 1670,
                "remaining_kcal": 130,
            },
            "meal_thread_count": 4,
            "pending_draft_count": 1,
            "same_truth": {"status": "pass"},
            "correction_history": [
                {
                    "action": "correction_applied",
                    "removed_item_names": [],
                },
                {
                    "action": "remove_item",
                    "removed_item_names": ["soup"],
                },
            ],
            "chat_style_transcript": [
                {"turn_id": "breakfast_tea_egg_latte"},
                {"turn_id": "lunch_chicken_bento"},
                {"turn_id": "lunch_rice_less_correction"},
                {"turn_id": "bubble_tea_first_value"},
                {"turn_id": "bubble_tea_half_sugar_large_refinement"},
                {"turn_id": "dinner_luwei_bare_draft"},
                {"turn_id": "dinner_luwei_listed_commit"},
                {"turn_id": "dinner_remove_gongwan"},
                {"turn_id": "today_consumed_remaining_query"},
            ],
        },
    }


def _write_artifact(path: Path, artifact: dict[str, object]) -> None:
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _assert_removed_fixed_false_fields(packet: dict[str, object]) -> None:
    for field in _REMOVED_FIXED_FALSE_FIELDS:
        assert field not in packet


def test_candidate_packet_prepares_human_review_only_packet_from_valid_shell_artifact(tmp_path: Path) -> None:
    shell_path = tmp_path / "shell.json"
    _write_artifact(shell_path, _valid_shell_artifact())

    packet = build_local_self_use_candidate_packet(shell_artifact_path=shell_path)

    assert packet["candidate_id"] == "accurate_intake_local_self_use_candidate_v1"
    assert packet["status"] == "prepared"
    assert packet["claim_scope"] == "local_deterministic_self_use_candidate"
    assert packet["local_self_use_candidate_prepared"] is True
    assert packet["human_review_required_before_activation"] is True
    assert packet["evidence"]["shell_artifact"]["status"] == "pass"
    assert packet["evidence"]["operator_surface"]["today_summary"]["consumed_kcal"] == 1670
    assert packet["evidence"]["operator_surface"]["same_truth_status"] == "pass"
    _assert_removed_fixed_false_fields(packet)


def test_candidate_packet_blocks_when_shell_artifact_did_not_pass(tmp_path: Path) -> None:
    shell_path = tmp_path / "shell.json"
    artifact = _valid_shell_artifact()
    artifact["status"] = "blocked"
    artifact["blockers"] = ["manager_fixture_missing_for_scenario"]
    _write_artifact(shell_path, artifact)

    packet = build_local_self_use_candidate_packet(shell_artifact_path=shell_path)

    assert packet["status"] == "blocked"
    assert packet["local_self_use_candidate_prepared"] is False
    assert "shell_artifact_not_passed" in packet["blockers"]
    _assert_removed_fixed_false_fields(packet)


def test_candidate_packet_blocks_raw_text_routing_or_readiness_overclaim_artifacts(tmp_path: Path) -> None:
    shell_path = tmp_path / "shell.json"
    artifact = _valid_shell_artifact()
    artifact["raw_text_routing_used"] = True
    artifact["product_readiness_claimed"] = True
    _write_artifact(shell_path, artifact)

    packet = build_local_self_use_candidate_packet(shell_artifact_path=shell_path)

    assert packet["status"] == "blocked"
    assert packet["local_self_use_candidate_prepared"] is False
    assert "raw_text_routing_used" in packet["blockers"]
    assert "shell_artifact_claimed_product_readiness" in packet["blockers"]
    _assert_removed_fixed_false_fields(packet)


def test_candidate_packet_cli_writes_local_artifact(tmp_path: Path, capsys) -> None:
    shell_path = tmp_path / "shell.json"
    output_path = tmp_path / "candidate.json"
    _write_artifact(shell_path, _valid_shell_artifact())

    exit_code = main(
        [
            "--shell-artifact",
            str(shell_path),
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["local_self_use_candidate_prepared"] is True
    _assert_removed_fixed_false_fields(artifact)


def test_self_use_runbook_documents_candidate_packet_and_artifact_hygiene() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8-sig")

    assert "Local Self-Use Shell And Candidate Packet" in runbook
    assert "python scripts/run_accurate_intake_local_self_use_shell.py --scenario one_day_v1" in runbook
    assert "python scripts/build_accurate_intake_local_self_use_candidate.py" in runbook
    assert "--reset-db" in runbook
    assert "--keep-db" in runbook
    assert "Windows" in runbook
    assert "Docker" in runbook
    assert "generated artifacts remain local-only" in runbook
    assert "must not claim private self-use approval, product readiness, production selection, or live-manager escalation" in runbook
