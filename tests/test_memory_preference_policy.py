from __future__ import annotations


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
    }


def _record(
    record_id: str,
    *,
    polarity: str,
    strength: str,
    subject_keys: list[str],
) -> dict[str, object]:
    record_type = "negative_preference" if polarity == "negative" else "confirmed_preference"
    return {
        "id": record_id,
        "record_type": record_type,
        "family": "diet_product",
        "status": "confirmed",
        "summary": f"{record_id} preference",
        "polarity": polarity,
        "strength": strength,
        "scope_keys": _scope(),
        "source_refs": [f"memory:{record_id}"],
        "consumers": ["recommendation_shadow"],
        "history": [f"review:{record_id}"],
        "subject_keys": subject_keys,
    }


def _candidate(candidate_id: str, subject_keys: list[str]) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "subject_keys": subject_keys,
        "source_refs": [f"candidate:{candidate_id}"],
    }


def test_negative_preference_blocks_before_positive_boosts() -> None:
    from app.memory.application.memory_preference_policy import (
        evaluate_preference_memory_policy,
    )

    artifact = evaluate_preference_memory_policy(
        memory_records=[
            _record("no-spicy", polarity="negative", strength="block", subject_keys=["spicy_food"]),
            _record("likes-ramen", polarity="positive", strength="boost", subject_keys=["ramen"]),
        ],
        candidates=[
            _candidate("spicy-ramen", ["ramen", "spicy_food"]),
            _candidate("plain-ramen", ["ramen"]),
        ],
    )

    by_id = {item["candidate_id"]: item for item in artifact["candidate_evaluations"]}

    assert artifact["status"] == "pass"
    assert by_id["spicy-ramen"]["blocked"] is True
    assert by_id["spicy-ramen"]["blocked_by"] == ["no-spicy"]
    assert by_id["spicy-ramen"]["boost_suppressed_by_negative"] is True
    assert by_id["plain-ramen"]["blocked"] is False
    assert by_id["plain-ramen"]["boosted_by"] == ["likes-ramen"]


def test_downrank_preference_reduces_score_without_blocking() -> None:
    from app.memory.application.memory_preference_policy import (
        evaluate_preference_memory_policy,
    )

    artifact = evaluate_preference_memory_policy(
        memory_records=[
            _record(
                "vegetarian-downrank",
                polarity="negative",
                strength="downrank",
                subject_keys=["vegetarian_meal_type"],
            )
        ],
        candidates=[
            _candidate("vegetarian-bento", ["vegetarian_meal_type"]),
        ],
    )

    evaluation = artifact["candidate_evaluations"][0]

    assert evaluation["blocked"] is False
    assert evaluation["downranked_by"] == ["vegetarian-downrank"]
    assert evaluation["score_adjustment"] < 0
    assert evaluation["allowed_after_memory_policy"] is True


def test_founder_negative_five_case_subjects_are_structured_policy_inputs() -> None:
    from app.memory.application.memory_preference_policy import (
        evaluate_preference_memory_policy,
    )

    artifact = evaluate_preference_memory_policy(
        memory_records=[
            _record("no-bitter-melon", polarity="negative", strength="block", subject_keys=["bitter_melon"]),
            _record("no-spicy", polarity="negative", strength="block", subject_keys=["spicy_food"]),
            _record("vegetarian-downrank", polarity="negative", strength="downrank", subject_keys=["vegetarian_meal_type"]),
            _record("bland-downrank", polarity="negative", strength="downrank", subject_keys=["bland_food"]),
            _record("eggplant-block", polarity="negative", strength="block", subject_keys=["eggplant"]),
        ],
        candidates=[
            _candidate("bitter-melon-stir-fry", ["bitter_melon"]),
            _candidate("spicy-hotpot", ["spicy_food", "hotpot"]),
            _candidate("vegetarian-bowl", ["vegetarian_meal_type", "bland_food"]),
            _candidate("eggplant-side", ["eggplant"]),
        ],
    )

    by_id = {item["candidate_id"]: item for item in artifact["candidate_evaluations"]}

    assert by_id["bitter-melon-stir-fry"]["blocked"] is True
    assert by_id["spicy-hotpot"]["blocked"] is True
    assert by_id["vegetarian-bowl"]["downranked_by"] == [
        "vegetarian-downrank",
        "bland-downrank",
    ]
    assert by_id["eggplant-side"]["blocked"] is True
    assert by_id["eggplant-side"]["blocked_by"] == ["eggplant-block"]


def test_policy_rejects_invalid_records_and_unstructured_candidates() -> None:
    from app.memory.application.memory_preference_policy import (
        evaluate_preference_memory_policy,
    )

    artifact = evaluate_preference_memory_policy(
        memory_records=[
            _record("bad-record", polarity="negative", strength="block", subject_keys=[]),
        ],
        candidates=[
            {"candidate_id": "missing-subjects", "source_refs": ["candidate:missing-subjects"]}
        ],
    )

    assert artifact["status"] == "blocked"
    assert "bad-record.subject_keys.missing" in artifact["blockers"]
    assert "missing-subjects.subject_keys.missing" in artifact["blockers"]
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
