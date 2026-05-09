from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.build_proactive_no_send_simulation import write_proactive_no_send_simulation


ROOT = Path(__file__).resolve().parents[1]


def _by_type(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = artifact["trigger_evaluations"]
    assert isinstance(rows, list)
    return {str(row["trigger_type"]): row for row in rows}


def _rescue_projection(**overrides: object) -> dict[str, object]:
    projection: dict[str, object] = {
        "artifact_type": "rescue_shadow_summary_context_projection",
        "status": "pass",
        "memory_summary_projection_used": True,
        "memory_signal_summary": {
            "preference_candidate_count": 2,
            "negative_preference_blocker_count": 1,
            "suppression_blocker_count": 1,
        },
        "suppression_context": [
            {
                "candidate_id": "hidden-suppression-candidate",
                "trigger_type": "rescue_nudge",
                "summary": "do not send rescue nudge after dismissal",
                "review_context_only": True,
            }
        ],
        "rescue_history_context": {
            "summary": "prior rescue review helped",
            "proposal_id": "hidden-proposal-id",
        },
        "adherence_context": {"summary": "weekday adherence is stable"},
        "history_review_notes": [
            "rescue_history_present_for_future_viability_review",
            "adherence_summary_present_for_future_viability_review",
        ],
        "rescue_needed": None,
        "send_or_skip": None,
        "candidate_copy": None,
        "proposal_card": None,
        "primary_actions": [],
        "recommended_days": None,
        "daily_kcal_adjustment": None,
        "runtime_effect_allowed": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "proactive_sent": False,
        "recommendation_served": False,
    }
    projection.update(overrides)
    return projection


def test_bridge_maps_rescue_projection_to_later_only_review_context() -> None:
    from app.runtime.application.proactive_rescue_nudge_bridge import (
        build_rescue_nudge_no_send_review,
    )

    review = build_rescue_nudge_no_send_review(_rescue_projection())

    assert review["status"] == "context_available"
    assert review["prompt_posture"] == "later_only_review_context"
    assert review["source_projection_used"] is True
    assert review["rescue_history_context_available"] is True
    assert review["adherence_context_available"] is True
    assert review["suppression_context_count"] == 1
    assert review["history_review_notes"] == [
        "rescue_history_present_for_future_viability_review",
        "adherence_summary_present_for_future_viability_review",
    ]
    assert review["rescue_committed"] is False
    assert review["proposal_committed"] is False
    assert review["proactive_sent"] is False
    assert review["manager_context_injected"] is False


def test_bridge_blocks_overclaiming_rescue_projection() -> None:
    from app.runtime.application.proactive_rescue_nudge_bridge import (
        build_rescue_nudge_no_send_review,
    )

    review = build_rescue_nudge_no_send_review(
        _rescue_projection(
            rescue_committed=True,
            proposal_committed=True,
            day_budget_mutated=True,
            manager_context_injected=True,
            proactive_sent=True,
        )
    )

    assert review["status"] == "blocked"
    assert review["blockers"] == [
        "rescue_context_projection.rescue_committed",
        "rescue_context_projection.proposal_committed",
        "rescue_context_projection.day_budget_mutated",
        "rescue_context_projection.manager_context_injected",
        "rescue_context_projection.proactive_sent",
    ]
    assert review["rescue_committed"] is False
    assert review["proposal_committed"] is False
    assert review["day_budget_mutated"] is False
    assert review["manager_context_injected"] is False
    assert review["proactive_sent"] is False


def test_bridge_does_not_leak_rescue_proposal_or_copy_details() -> None:
    from app.runtime.application.proactive_rescue_nudge_bridge import (
        build_rescue_nudge_no_send_review,
    )

    review = build_rescue_nudge_no_send_review(
        _rescue_projection(
            proposal_card={"title": "Hidden proposal card"},
            candidate_copy="Hidden rescue copy",
            primary_actions=["hidden action"],
            recommended_days=3,
            daily_kcal_adjustment=-150,
            send_or_skip="send",
        )
    )
    serialized = json.dumps(review)

    assert review["status"] == "blocked"
    assert "Hidden proposal card" not in serialized
    assert "Hidden rescue copy" not in serialized
    assert "hidden action" not in serialized
    assert "hidden-proposal-id" not in serialized
    assert "hidden-suppression-candidate" not in serialized


def test_writer_can_thread_rescue_summary_context_into_later_only_nudge(tmp_path: Path) -> None:
    projection_path = tmp_path / "rescue_summary_context.json"
    output_path = tmp_path / "proactive_no_send_simulation.json"
    projection_path.write_text(
        json.dumps(
            _rescue_projection(debug_candidate_copy="Hidden rescue copy"),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    written = write_proactive_no_send_simulation(
        output_path=output_path,
        rescue_summary_context_projection_path=projection_path,
    )
    artifact = json.loads(written.read_text(encoding="utf-8"))
    rescue = _by_type(artifact)["rescue_nudge"]
    artifact_text = json.dumps(artifact)

    assert rescue["suppression_status"] == "deferred_later_only"
    assert rescue["rescue_nudge_review"]["status"] == "context_available"
    assert rescue["rescue_nudge_review"]["rescue_history_context_available"] is True
    assert rescue["rescue_nudge_review"]["suppression_context_count"] == 1
    assert rescue["rescue_committed"] is False
    assert rescue["proactive_sent"] is False
    assert "Hidden rescue copy" not in artifact_text
    assert "hidden-proposal-id" not in artifact_text
    assert "hidden-suppression-candidate" not in artifact_text


def test_writer_rejects_wrong_rescue_summary_context_projection_artifact(tmp_path: Path) -> None:
    projection_path = tmp_path / "wrong.json"
    projection_path.write_text(json.dumps({"artifact_type": "wrong"}), encoding="utf-8")

    try:
        write_proactive_no_send_simulation(
            output_path=tmp_path / "out.json",
            rescue_summary_context_projection_path=projection_path,
        )
    except ValueError as exc:
        assert "rescue_summary_context_projection.unsupported_artifact_type" in str(exc)
    else:
        raise AssertionError("expected invalid projection to raise ValueError")


def test_writer_rejects_blocked_rescue_summary_context_projection(tmp_path: Path) -> None:
    projection_path = tmp_path / "blocked.json"
    projection_path.write_text(
        json.dumps({"artifact_type": "rescue_shadow_summary_context_projection", "status": "blocked"}),
        encoding="utf-8",
    )

    try:
        write_proactive_no_send_simulation(
            output_path=tmp_path / "out.json",
            rescue_summary_context_projection_path=projection_path,
        )
    except ValueError as exc:
        assert "rescue_summary_context_projection.status_not_pass" in str(exc)
    else:
        raise AssertionError("expected blocked projection to raise ValueError")


def test_cli_threads_rescue_summary_context_into_default_artifact(tmp_path: Path) -> None:
    projection_path = tmp_path / "rescue_projection.json"
    output_path = tmp_path / "simulation.json"
    projection_path.write_text(json.dumps(_rescue_projection()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_proactive_no_send_simulation.py",
            "--rescue-summary-context-projection",
            str(projection_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    rows = _by_type(json.loads(output_path.read_text(encoding="utf-8")))
    assert rows["rescue_nudge"]["suppression_status"] == "deferred_later_only"
    assert rows["rescue_nudge"]["rescue_nudge_review"]["status"] == "context_available"
