from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _candidate(candidate_type: str, **payload: object) -> dict:
    return {
        "candidate_id": f"{candidate_type}-001",
        "case_id": f"{candidate_type}-case",
        "candidate_type": candidate_type,
        "scope_keys": {
            "user_id": "user-a",
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "validator-run-001",
        },
        "source_object_refs": ["message:source-001"],
        "payload": payload,
        "review_status": "pending",
        "runtime_effect_allowed": False,
        "promotion_allowed_now": False,
        "human_review_required": True,
    }


def _candidate_trace() -> dict:
    return {
        "request_id": "rt-lab-validator-001",
        "trace_meta": {
            "request_id": "rt-lab-validator-001",
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "validator-run-001",
        },
        "request": {"user_id": "user-a", "text": "structured candidate signal"},
        "manager_final_decision": {"workflow_effect": "commit_meal_log"},
        "memory_lab_candidate_signal": {
            "candidate_type": "pattern",
            "manager_decision_field": "deterministic_pattern_candidate",
            "source_refs": [f"meal:pattern-{index}" for index in range(5)],
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
            "reason_codes": ["deterministic_pattern_candidate"],
            "reinforcement_count": 5,
        },
    }


def test_pattern_threshold_boundaries_do_not_auto_promote() -> None:
    from app.memory.application.runtime_lab_lifecycle_validator import (
        build_lifecycle_decision_artifact,
    )

    artifact = build_lifecycle_decision_artifact(
        [
            _candidate("pattern", reinforcement_count=4),
            _candidate("pattern", reinforcement_count=5),
        ],
        as_of="2026-05-09T00:00:00+08:00",
    )

    decisions = {item["candidate_id"]: item for item in artifact["decisions"]}
    assert decisions["pattern-001"]["decision"] == "promotion_review_candidate"
    assert decisions["pattern-001"]["promotion_allowed_now"] is False
    assert decisions["pattern-001"]["runtime_effect_allowed"] is False
    assert artifact["durable_product_memory_written"] is False

    below = artifact["decisions"][0]
    above = artifact["decisions"][1]
    assert below["decision"] == "hold_for_more_evidence"
    assert above["decision"] == "promotion_review_candidate"
    assert above["thresholds"]["pattern_min_count"] == 5


def test_temporary_preference_expiry_creates_expire_review_decision() -> None:
    from app.memory.application.runtime_lab_lifecycle_validator import (
        validate_candidate_lifecycle,
    )

    decision = validate_candidate_lifecycle(
        _candidate(
            "temporary_preference",
            created_at="2026-04-01T00:00:00+08:00",
            default_max_days=14,
        ),
        as_of="2026-05-09T00:00:00+08:00",
    )

    assert decision["decision"] == "expire_review_candidate"
    assert decision["review_status_after"] == "expired"
    assert decision["promotion_allowed_now"] is False


def test_confirmed_negative_blocks_auto_demote_of_conflicting_pattern() -> None:
    from app.memory.application.runtime_lab_lifecycle_validator import (
        validate_candidate_lifecycle,
    )

    decision = validate_candidate_lifecycle(
        _candidate(
            "negative_preference",
            confirmed=True,
            conflicts_with=["pattern-sweet-drink"],
        ),
        as_of="2026-05-09T00:00:00+08:00",
    )

    assert decision["decision"] == "contradiction_review_candidate"
    assert decision["auto_demote_allowed"] is False
    assert decision["reason_codes"] == ["confirmed_negative_requires_review"]


def test_stale_patterns_get_archive_or_delete_review_only() -> None:
    from app.memory.application.runtime_lab_lifecycle_validator import (
        build_lifecycle_decision_artifact,
    )

    archive_candidate = _candidate(
        "pattern",
        reinforcement_count=5,
        last_seen_at="2026-01-01T00:00:00+08:00",
    )
    archive_candidate["candidate_id"] = "pattern-archive"
    delete_candidate = _candidate(
        "pattern",
        reinforcement_count=5,
        last_seen_at="2025-10-01T00:00:00+08:00",
    )
    delete_candidate["candidate_id"] = "pattern-delete"

    artifact = build_lifecycle_decision_artifact(
        [archive_candidate, delete_candidate],
        as_of="2026-05-09T00:00:00+08:00",
    )

    decisions = {item["candidate_id"]: item for item in artifact["decisions"]}
    assert decisions["pattern-archive"]["decision"] == "archive_review_candidate"
    assert decisions["pattern-delete"]["decision"] == "delete_review_candidate"
    assert decisions["pattern-delete"]["canonical_mutation_changed"] is False


def test_llm_auto_promotion_signal_is_blocked() -> None:
    from app.memory.application.runtime_lab_lifecycle_validator import (
        validate_candidate_lifecycle,
    )

    decision = validate_candidate_lifecycle(
        _candidate(
            "preference",
            llm_recommended_promotion=True,
            promotion_allowed_now=True,
        ),
        as_of="2026-05-09T00:00:00+08:00",
    )

    assert decision["promotion_allowed_now"] is False
    assert "llm_auto_promotion_blocked" in decision["reason_codes"]
    assert decision["decision"] == "human_confirmation_required"


def test_lifecycle_runner_outputs_review_decisions_only(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "lifecycle.json"
    trace_path.write_text(json.dumps(_candidate_trace()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_runtime_lab_memory_lifecycle_validator.py"),
            "--trace-json",
            str(trace_path),
            "--output",
            str(output_path),
            "--as-of",
            "2026-05-09T00:00:00+08:00",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["artifact_type"] == "runtime_lab_memory_lifecycle_decisions"
    assert artifact["decision_count"] == 1
    assert artifact["runtime_connected"] is True
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["decisions"][0]["decision"] == "promotion_review_candidate"
