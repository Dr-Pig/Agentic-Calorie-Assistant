from __future__ import annotations

import json


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
    status: str = "confirmed",
    record_type: str = "confirmed_preference",
    summary: str = "User prefers strong flavored meals.",
    polarity: str = "positive",
    strength: str = "boost",
    source_refs: list[str] | None = None,
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "id": record_id,
        "record_type": record_type,
        "family": "diet_product",
        "status": status,
        "summary": summary,
        "polarity": polarity,
        "strength": strength,
        "scope_keys": _scope(),
        "source_refs": source_refs or [f"message:{record_id}"],
        "consumers": ["recommendation_shadow"],
        "history": [f"feedback:{record_id}"],
    }
    record.update(extra)
    return record


def test_surface_projection_writes_confirmed_profile_and_review_queue() -> None:
    from app.memory.application.memory_surface_projection import (
        build_memory_surface_projection,
    )

    artifact = build_memory_surface_projection(
        memory_records=[
            _record("likes-ramen", summary="User likes ramen."),
            _record(
                "no-spicy",
                record_type="negative_preference",
                summary="User does not eat spicy food.",
                polarity="negative",
                strength="block",
            ),
            _record(
                "candidate-hotpot",
                status="pending_review",
                summary="Candidate: user recently likes hotpot.",
            ),
        ]
    )

    assert artifact["status"] == "pass"
    assert "User likes ramen." in artifact["surfaces"]["user_md"]
    assert "User does not eat spicy food." in artifact["surfaces"]["user_md"]
    assert "candidate-hotpot" not in artifact["surfaces"]["user_md"]
    assert "candidate-hotpot" in artifact["surfaces"]["review_md"]
    assert artifact["surface_paths_declared"] == [
        "user.md",
        "memory.md",
        "source.md",
        "sources.jsonl",
        "review.md",
    ]
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False


def test_sources_jsonl_is_metadata_first_and_has_no_raw_transcript_dump() -> None:
    from app.memory.application.memory_surface_projection import (
        build_memory_surface_projection,
    )

    artifact = build_memory_surface_projection(
        memory_records=[
            _record(
                "no-spicy",
                record_type="negative_preference",
                summary="User does not eat spicy food.",
                polarity="negative",
                strength="block",
                source_refs=["source:message-founder-profile-negative-002"],
                raw_transcript="I do not eat spicy food. Keep every raw word.",
                evidence_text="Source evidence should not be copied into JSONL.",
            )
        ]
    )

    rows = [
        json.loads(line)
        for line in artifact["surfaces"]["sources_jsonl"].splitlines()
        if line.strip()
    ]

    assert rows == [
        {
            "source_ref": "source:message-founder-profile-negative-002",
            "record_id": "no-spicy",
            "record_type": "negative_preference",
            "scope_keys": _scope(),
            "metadata": {
                "family": "diet_product",
                "status": "confirmed",
                "polarity": "negative",
                "strength": "block",
                "validity": None,
            },
        }
    ]
    serialized = artifact["surfaces"]["sources_jsonl"]
    assert "raw_transcript" not in serialized
    assert "Keep every raw word" not in serialized
    assert "Source evidence should not be copied" not in serialized
    assert artifact["raw_source_dump_included"] is False


def test_surface_projection_blocks_invalid_memory_record_scope() -> None:
    from app.memory.application.memory_surface_projection import (
        build_memory_surface_projection,
    )

    bad_record = _record("bad-scope", scope_keys={"user_id": "user-a"})

    artifact = build_memory_surface_projection(memory_records=[bad_record])

    assert artifact["status"] == "blocked"
    assert (
        "bad-scope.scope_keys.missing:workspace_id,project_id,surface"
        in artifact["blockers"]
    )
    assert artifact["surfaces"] == {}


def test_surface_projection_keeps_memory_md_reporting_separate_from_user_md() -> None:
    from app.memory.application.memory_surface_projection import (
        build_memory_surface_projection,
    )

    artifact = build_memory_surface_projection(
        memory_records=[
            _record("confirmed-1", summary="Confirmed stable preference."),
            _record(
                "rejected-1",
                status="rejected",
                summary="Rejected memory should only appear in review reporting.",
            ),
        ]
    )

    assert "confirmed-1" in artifact["surfaces"]["memory_md"]
    assert "rejected-1" in artifact["surfaces"]["memory_md"]
    assert "Rejected memory" not in artifact["surfaces"]["user_md"]
    assert "rejected-1" in artifact["surfaces"]["review_md"]
    assert artifact["memory_md_is_runtime_truth"] is False
