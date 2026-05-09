from __future__ import annotations


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
        "run_id": "review-run-001",
    }


def _candidate(candidate_id: str = "candidate-001", **overrides: object) -> dict:
    candidate = {
        "candidate_id": candidate_id,
        "candidate_type": "preference",
        "scope_keys": _scope(),
        "source_trace_ids": ["trace-001"],
        "source_object_refs": [f"message:{candidate_id}"],
        "review_status": "pending",
        "human_review_required": True,
        "promotion_allowed_now": False,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "payload": {"summary": "prefers lighter lunch suggestions"},
    }
    candidate.update(overrides)
    return candidate


def _action(action_type: str, candidate_id: str = "candidate-001") -> dict:
    return {
        "action_id": f"review-{action_type}",
        "action_type": action_type,
        "target_candidate_id": candidate_id,
        "actor": "fixture-human-reviewer",
        "reason_codes": ["human_reviewed"],
        "source_refs": ["review:memory-review-001"],
    }


def test_review_contract_accepts_shadow_candidate_without_promotion_or_write() -> None:
    from app.memory.application.runtime_lab_review_contract import (
        build_memory_candidate_review_contract,
    )
    from app.memory.application.runtime_lab_lifecycle_validator import (
        build_lifecycle_decision_artifact,
    )

    artifact = build_memory_candidate_review_contract(
        [_candidate()],
        [_action("accept_shadow_candidate")],
    )

    assert artifact["artifact_type"] == "runtime_lab_memory_candidate_review_contract"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/memory"
    assert artifact["consumer"] == "runtime_lab_memory_lifecycle_validator"
    assert artifact["retirement_trigger"] == "approved_memory_runtime_activation_plan"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["runtime_lab_store_written"] is False

    result = artifact["review_results"][0]
    assert result["review_status_after"] == "accepted_shadow"
    assert result["promotion_allowed_now"] is False
    assert result["candidate_patch"]["review_status"] == "accepted_shadow"
    assert result["candidate_patch"]["runtime_lab_store_write_required"] is False

    lifecycle = build_lifecycle_decision_artifact(
        artifact["reviewed_shadow_candidates"],
        as_of="2026-05-09T00:00:00+08:00",
        runtime_connected=True,
    )
    assert lifecycle["decisions"][0]["promotion_allowed_now"] is False
    assert lifecycle["decisions"][0]["human_review_required"] is True


def test_review_contract_supports_do_not_save_and_forget_without_deleting_store() -> None:
    from app.memory.application.runtime_lab_review_contract import (
        build_memory_candidate_review_contract,
    )

    artifact = build_memory_candidate_review_contract(
        [_candidate("candidate-a"), _candidate("candidate-b")],
        [
        _action("mark_do_not_save", "candidate-a"),
        _action("forget_shadow_candidate", "candidate-b"),
        ],
    )

    results = {item["candidate_id"]: item for item in artifact["review_results"]}
    assert results["candidate-a"]["review_status_after"] == "rejected"
    assert results["candidate-a"]["memory_use_blocked"] is True
    assert results["candidate-a"]["do_not_save_requested"] is True
    assert results["candidate-a"]["forget_tombstone_requested"] is False
    assert results["candidate-b"]["review_status_after"] == "deleted"
    assert results["candidate-b"]["forget_tombstone_requested"] is True
    assert results["candidate-b"]["candidate_patch"]["source_object_refs"] == []
    assert artifact["durable_product_memory_written"] is False
    assert artifact["canonical_mutation_changed"] is False


def test_review_contract_blocks_missing_actor_missing_scope_and_bad_target() -> None:
    from app.memory.application.runtime_lab_review_contract import (
        build_memory_candidate_review_contract,
    )

    bad_scope = _candidate("candidate-missing-scope")
    bad_scope["scope_keys"] = dict(_scope())
    bad_scope["scope_keys"].pop("project_id")
    missing_actor = _action("accept_shadow_candidate", "candidate-001")
    missing_actor.pop("actor")
    missing_target = _action("reject_candidate", "unknown-candidate")

    artifact = build_memory_candidate_review_contract(
        [_candidate(), bad_scope],
        [missing_actor, missing_target],
    )

    assert artifact["status"] == "blocked"
    assert artifact["review_results"] == []
    assert artifact["blockers"] == [
        "candidate-missing-scope.missing_scope_keys:project_id",
        "review-accept_shadow_candidate.missing_actor",
        "review-reject_candidate.unknown_target_candidate:unknown-candidate",
    ]
    assert artifact["durable_product_memory_written"] is False


def test_review_contract_blocks_unsupported_actions_and_candidate_truth_leak() -> None:
    from app.memory.application.runtime_lab_review_contract import (
        build_memory_candidate_review_contract,
    )

    truth_leak = _candidate(runtime_effect_allowed=True)
    unsupported = _action("promote_to_product_memory")

    artifact = build_memory_candidate_review_contract([truth_leak], [unsupported])

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "candidate-001.runtime_effect_allowed",
        "review-promote_to_product_memory.unsupported_action_type",
    ]
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["manager_context_packet_changed"] is False


def test_review_contract_blocks_durable_sounding_confirm_action() -> None:
    from app.memory.application.runtime_lab_review_contract import (
        build_memory_candidate_review_contract,
    )

    artifact = build_memory_candidate_review_contract(
        [_candidate()],
        [_action("confirm_candidate")],
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["review-confirm_candidate.unsupported_action_type"]
