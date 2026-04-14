from __future__ import annotations

import json
from pathlib import Path

from scripts import run_turn2_hybrid_replay as replay


ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "intake" / "multi_turn" / "turn2_hybrid_replay_pack_v1.json"


def test_turn2_hybrid_replay_pack_has_required_cases() -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]

    assert len(cases) >= 9
    case_ids = {case["case_id"] for case in cases}
    assert "turn2_hybrid_replay_ask_completion_001" in case_ids
    assert "turn2_hybrid_replay_ask_completion_002" in case_ids
    assert "turn2_hybrid_replay_ask_completion_003" in case_ids
    assert "turn2_hybrid_replay_ask_completion_004" in case_ids
    assert "turn2_hybrid_replay_estimate_refinement_001" in case_ids
    assert "turn2_hybrid_replay_estimate_refinement_002" in case_ids
    assert "turn2_hybrid_replay_estimate_refinement_003" in case_ids
    assert "turn2_hybrid_replay_estimate_refinement_004" in case_ids
    assert "turn2_hybrid_replay_estimate_refinement_005" in case_ids

    for case in cases:
        assert case["title"]
        assert case["turn1_input"]
        assert case["turn2_input"]
        assert case["lane_family"] in {"ask_followup_only_to_completion", "estimate_ok_to_refinement"}
        assert case["expected_turn1_lane"] in {"ask_followup_only", "estimate_with_followup"}
        assert case["expected_turn2_outcome"] in {"completion", "refinement"}
        assert case["expected_attachment"] == "same_intake_thread"
        assert case["expected_persistence"]["turn1_status"] == "draft_unresolved"
        assert case["expected_persistence"]["turn2_status"] == "completed_meal"
        assert case["expected_persistence"]["canonical_commit_required"] is True
        assert "new_meal_thread" in case["forbidden_outcomes"]
        assert case["origin"] in {"accepted_golden_v1", "founder_authored"}


def test_turn2_hybrid_replay_summary_tracks_attachment_and_expectations(tmp_path: Path) -> None:
    case = {
        "case_id": "turn2_hybrid_replay_estimate_refinement_001",
        "lane": "estimate_with_followup_to_refinement",
        "expected_turn1_lane": "estimate_with_followup",
        "expected_turn2_outcome": "refinement",
        "expected_attachment": "same_intake_thread",
    }
    turn1_path = tmp_path / "turn1.json"
    turn2_path = tmp_path / "turn2.json"
    turn1 = {
        "persistence_decision": {
            "status": "draft_saved",
            "persisted_log_id": "log_123",
        }
    }
    turn2 = {
        "persistence_decision": {
            "status": "committed",
            "parent_log_id": "log_123",
            "canonical_commit": {"meal_thread_id": "thread_1"},
        }
    }

    summary = replay._build_summary(
        case,
        user_id="turn2-hybrid-test",
        turn1_path=turn1_path,
        turn2_path=turn2_path,
        turn1=turn1,
        turn2=turn2,
    )

    assert summary["same_intake_attached"] is True
    assert summary["canonical_commit_present_on_turn2"] is True
    assert summary["expected_turn1_lane"] == "estimate_with_followup"
    assert summary["expected_turn2_outcome"] == "refinement"
    assert summary["matched_expected_attachment"] is True
    assert summary["matched_expected_turn2_status"] is None
    assert summary["matched_expected_commit_presence"] is None
    assert summary["forbidden_outcome_hits"] == []
