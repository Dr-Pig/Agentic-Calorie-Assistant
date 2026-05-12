from __future__ import annotations


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
    }


def _record(record_id: str, *, consumers: list[str] | None = None) -> dict[str, object]:
    return {
        "id": record_id,
        "record_type": "confirmed_preference",
        "family": "diet_product",
        "status": "confirmed",
        "summary": f"{record_id} summary",
        "polarity": "positive",
        "strength": "boost",
        "scope_keys": _scope(),
        "source_refs": [f"source:{record_id}"],
        "consumers": consumers or ["recommendation_shadow"],
        "history": [f"feedback:{record_id}"],
        "raw_transcript": "should not be returned",
    }


def test_memory_search_and_get_are_scoped_read_only_tools() -> None:
    from app.memory.application.memory_tool_facade import execute_memory_tool_call

    records = [
        _record("likes-ramen"),
        _record("proactive-only", consumers=["proactive_shadow"]),
    ]
    search = execute_memory_tool_call(
        tool_name="memory.search",
        arguments={
            "scope_keys": _scope(),
            "consumer": "recommendation_shadow",
            "limit": 5,
        },
        memory_records=records,
    )
    get = execute_memory_tool_call(
        tool_name="memory.get",
        arguments={"scope_keys": _scope(), "memory_id": "likes-ramen"},
        memory_records=records,
    )

    assert search["status"] == "pass"
    assert search["selected_record_ids"] == ["likes-ramen"]
    assert search["raw_transcript_included"] is False
    assert get["status"] == "pass"
    assert get["record"]["id"] == "likes-ramen"
    assert "raw_transcript" not in get["record"]
    assert get["durable_product_memory_written"] is False
    assert get["manager_context_packet_changed"] is False


def test_memory_source_lookup_tool_delegates_bounded_lookup_policy() -> None:
    from app.memory.application.memory_tool_facade import execute_memory_tool_call

    artifact = execute_memory_tool_call(
        tool_name="memory.source_lookup",
        arguments={
            "scope_keys": {**_scope(), "run_id": "run-1"},
            "source_refs": ["source:likes-ramen"],
            "tool_path": "why_memory",
            "max_evidence_chars": 20,
        },
        memory_records=[],
        source_entries=[
            {
                "source_ref": "source:likes-ramen",
                "record_id": "likes-ramen",
                "source_kind": "message_event",
                "scope_keys": {**_scope(), "run_id": "run-1"},
                "metadata": {"freshness": "current"},
                "evidence_text": "User likes ramen because it is filling.",
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["tool_result"]["bounded_evidence_read"] is True
    assert len(
        artifact["tool_result"]["results"][0]["bounded_evidence_span"]["text"]
    ) <= 20
    assert artifact["tool_result"]["general_rag_pool_used"] is False


def test_memory_propose_returns_candidate_without_durable_write() -> None:
    from app.memory.application.memory_tool_facade import execute_memory_tool_call

    candidate = {
        **_record("pending-hotpot"),
        "status": "candidate",
        "summary": "Candidate: user likes hotpot recently.",
    }

    artifact = execute_memory_tool_call(
        tool_name="memory.propose",
        arguments={"memory_record": candidate},
        memory_records=[],
    )

    assert artifact["status"] == "pass"
    assert artifact["candidate"]["id"] == "pending-hotpot"
    assert artifact["candidate"]["status"] == "candidate"
    assert artifact["candidate_review_required"] is True
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["durable_product_memory_written"] is False


def test_memory_review_delegates_feedback_projection_without_promotion() -> None:
    from app.memory.application.memory_tool_facade import execute_memory_tool_call

    artifact = execute_memory_tool_call(
        tool_name="memory.review",
        arguments={
            "feedback_event": {
                "target_type": "memory_candidate",
                "target_id": "pending-hotpot",
                "action": "confirm",
                "source_turn_id": "turn-1",
                "scope_keys": _scope(),
            }
        },
        memory_records=[],
        feedback_targets=[
            {
                "target_type": "memory_candidate",
                "target_id": "pending-hotpot",
                "scope_keys": _scope(),
                "source_turn_ids": ["turn-1"],
                "source_refs": ["message:pending-hotpot"],
                "candidate_type": "confirmed_preference",
            }
        ],
    )

    projection = artifact["tool_result"]["consumer_projections"][0]
    assert artifact["status"] == "pass"
    assert projection["projection_type"] == "memory_confirmation_validator_input"
    assert artifact["tool_result"]["confirmed_memory_promoted"] is False
    assert artifact["durable_product_memory_written"] is False


def test_memory_tool_facade_blocks_unsupported_tool_and_missing_scope() -> None:
    from app.memory.application.memory_tool_facade import execute_memory_tool_call

    unsupported = execute_memory_tool_call(
        tool_name="memory.delete_everything",
        arguments={"scope_keys": _scope()},
        memory_records=[],
    )
    missing_scope = execute_memory_tool_call(
        tool_name="memory.search",
        arguments={"scope_keys": {"user_id": "user-a"}},
        memory_records=[],
    )

    assert unsupported["status"] == "blocked"
    assert "tool.unsupported:memory.delete_everything" in unsupported["blockers"]
    assert missing_scope["status"] == "blocked"
    assert "scope_keys.missing:workspace_id,project_id,surface" in missing_scope[
        "blockers"
    ]
