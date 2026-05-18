from __future__ import annotations

import json

from app.runtime.agent.manager_context_payload import manager_context_packet_v1_prompt_payload


def test_post_tool_context_reference_compacts_active_day_state_and_hard_pins() -> None:
    packet = {
        "metadata": {
            "local_date": "2026-05-09",
            "context_policy_version": "accurate_intake_mvp_context_policy_v1",
            "claim_scope": "current_session_current_day_manager_input_evidence",
        },
        "context_loading_artifact": {
            "loaded_message_count": 3,
            "omitted_count": 1,
            "char_truncated": False,
            "token_budget_status": "within_budget",
        },
        "context_lineage": {
            "lineage_version": "manager_context_lineage_v1",
            "context_generation": "manager_context_packet_v1",
            "context_packet_hash": "a" * 64,
            "active_workflow_id": "pending_followup:turn-1",
            "context_reinjected_after_compaction_or_history_trim": False,
            "source_role": "runtime_context_state_packet",
            "semantic_owner": "manager_llm",
            "read_only": True,
            "mutation_authority": False,
        },
        "context_layers": {
            "current_turn": {
                "raw_user_input_present": True,
                "semantic_owner": "manager_llm",
                "read_only": True,
                "mutation_authority": False,
            },
            "active_workflow": {
                "pending_followup_present": True,
                "active_workflow_id": "pending_followup:turn-1",
                "semantic_owner": "manager_llm",
                "read_only": True,
                "mutation_authority": False,
            },
            "evidence_state": {
                "target_candidate_count": 1,
                "semantic_owner": "manager_llm",
                "read_only": True,
                "mutation_authority": False,
            },
        },
        "current_turn": {
            "user_utterance": "half sugar, no ice",
            "raw_user_input": "half sugar, no ice",
            "channel": "web_shell",
            "manager_mode": "live_diagnostic",
            "current_turn_first": True,
            "interaction_event": {
                "event_type": "chat_message",
                "raw_text": "半糖中杯",
                "target_object_type": "meal_thread",
                "target_object_id": "thread-77",
            },
        },
        "recent_chat_window": {"messages": [{"role": "user", "content": "x" * 5000}]},
        "hard_pins": {
            "pending_followup": {
                "runtime_turn_id": "turn-1",
                "meal_thread_id": 77,
                "meal_item_id": 501,
                "expected_answer_type": "drink_size_sugar",
                "question": "多大杯、甜度多少？",
                "full_prompt_debug_blob": "x" * 5000,
            },
            "pending_draft": {
                "draft_id": "draft-1",
                "meal_thread_id": 77,
                "items": [{"debug_blob": "x" * 5000}],
            },
            "last_assistant_question": "多大杯、甜度多少？",
        },
        "active_day_state": {
            "budget_summary": {
                "status": "ready",
                "daily_target_kcal": 1800,
                "consumed_kcal": 520,
                "remaining_kcal": 1280,
                "show_macro": False,
                "macro_guard_reason": "missing_source",
                "debug_blob": "x" * 5000,
            },
            "active_meal_thread_ref": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_item_id": 501,
                "canonical_name": "bubble_milk_tea",
                "items": [{"debug_blob": "x" * 5000}],
            },
            "recent_correction_removal_summary": [{"debug_blob": "x" * 5000}],
            "read_only": True,
            "mutation_authority": False,
        },
        "read_model_summary": {
            "budget": {
                "status": "ready",
                "daily_target_kcal": 1800,
                "consumed_kcal": 520,
                "remaining_kcal": 1280,
                "debug_blob": "x" * 5000,
            },
            "body_plan": {
                "status": "ready",
                "daily_target_kcal": 1800,
                "tdee_kcal": 2300,
                "current_weight_kg": 84,
                "debug_blob": "x" * 5000,
            },
            "current_day": {"open_workflow_type": "optional_refinement"},
            "recent_committed_meals": [{"debug_blob": "x" * 5000}],
        },
        "evidence_state": {
            "fooddb": {"status": "generic_anchor_available", "debug_blob": "x" * 5000},
            "websearch": {"availability": "available_not_called", "debug_blob": "x" * 5000},
            "macro": {
                "macro_evidence_status": "hidden_missing_source",
                "macro_guard_reason": "no_macro_data",
                "debug_blob": "x" * 5000,
            },
            "selected_extracts": [
                {
                    "packet_id": "fdb-1",
                    "source_type": "fooddb",
                    "match_posture": "generic_anchor",
                    "commit_posture": "candidate_only",
                    "debug_blob": "x" * 5000,
                }
            ],
            "rejected_candidates": [{"debug_blob": "x" * 5000}],
        },
        "target_candidates": {
            "for_correction_or_removal": [
                {"meal_thread_id": 77, "meal_item_id": 501, "debug_blob": "x" * 5000}
            ]
        },
        "constraints": ["frontend_cannot_infer_semantics"],
    }

    initial_payload = manager_context_packet_v1_prompt_payload(packet)
    assert initial_payload["current_turn"]["raw_user_input"] == "half sugar, no ice"
    assert initial_payload["current_turn"]["current_turn_first"] is True
    assert initial_payload["read_model_summary"]["budget"]["remaining_kcal"] == 1280
    assert initial_payload["evidence_state"]["fooddb"] == {"status": "generic_anchor_available"}
    initial_read_evidence = {
        "read_model_summary": initial_payload["read_model_summary"],
        "evidence_state": initial_payload["evidence_state"],
    }
    assert "debug_blob" not in json.dumps(initial_read_evidence, ensure_ascii=False)

    payload = manager_context_packet_v1_prompt_payload(
        packet,
        tool_results=[{"tool_name": "estimate_nutrition"}],
    )

    assert payload is not None
    assert payload["current_turn"]["raw_user_input"] == "half sugar, no ice"
    assert payload["current_turn"]["current_turn_first"] is True
    rendered = json.dumps(payload, ensure_ascii=False)
    assert len(rendered) < len(json.dumps(packet, ensure_ascii=False))
    assert "debug_blob" not in rendered
    assert "full_prompt_debug_blob" not in rendered
    assert "messages" not in payload["recent_chat_window"]
    assert payload["target_candidates"]["for_correction_or_removal"] == [
        {"meal_thread_id": 77, "meal_item_id": 501}
    ]
    assert payload["context_lineage"]["active_workflow_id"] == "pending_followup:turn-1"
    assert payload["context_layers"]["active_workflow"]["pending_followup_present"] is True

    hard_pins = payload["hard_pins"]
    assert hard_pins["hard_pins_compacted_after_tool_evidence"] is True
    assert hard_pins["pending_followup"] == {
        "runtime_turn_id": "turn-1",
        "meal_thread_id": 77,
        "meal_item_id": 501,
        "expected_answer_type": "drink_size_sugar",
        "question": "多大杯、甜度多少？",
    }
    assert hard_pins["pending_draft"] == {"draft_id": "draft-1", "meal_thread_id": 77}
    assert hard_pins["read_only"] is True
    assert hard_pins["mutation_authority"] is False

    active_day_state = payload["active_day_state"]
    assert active_day_state["active_day_state_compacted_after_tool_evidence"] is True
    assert active_day_state["budget_summary"] == {
        "status": "ready",
        "daily_target_kcal": 1800,
        "consumed_kcal": 520,
        "remaining_kcal": 1280,
        "show_macro": False,
        "macro_guard_reason": "missing_source",
    }
    assert active_day_state["active_meal_thread_ref"] == {
        "meal_thread_id": 77,
        "meal_version_id": 88,
        "meal_item_id": 501,
        "canonical_name": "bubble_milk_tea",
        "item_count": 1,
    }
    assert active_day_state["recent_correction_removal_count"] == 1
    assert active_day_state["read_only"] is True
    assert active_day_state["mutation_authority"] is False

    read_model_summary = payload["read_model_summary"]
    assert read_model_summary["read_model_summary_compact"] is True
    assert read_model_summary["budget"] == {
        "status": "ready",
        "daily_target_kcal": 1800,
        "consumed_kcal": 520,
        "remaining_kcal": 1280,
    }
    assert read_model_summary["body_plan"] == {
        "status": "ready",
        "daily_target_kcal": 1800,
        "tdee_kcal": 2300,
        "current_weight_kg": 84,
    }
    assert read_model_summary["recent_committed_meal_count"] == 1

    evidence_state = payload["evidence_state"]
    assert evidence_state["evidence_state_compact"] is True
    assert evidence_state["selection_owner"] == "manager"
    assert evidence_state["fooddb"] == {"status": "generic_anchor_available"}
    assert evidence_state["websearch"] == {"availability": "available_not_called"}
    assert evidence_state["macro"] == {
        "macro_evidence_status": "hidden_missing_source",
        "macro_guard_reason": "no_macro_data",
    }
    assert evidence_state["selected_extracts"] == [
        {
            "packet_id": "fdb-1",
            "source_type": "fooddb",
            "match_posture": "generic_anchor",
            "commit_posture": "candidate_only",
        }
    ]
    assert evidence_state["selected_extract_count"] == 1
    assert evidence_state["rejected_candidate_count"] == 1

    target_candidates = payload["target_candidates"]
    assert target_candidates["target_candidates_compacted_after_tool_evidence"] is True
    assert target_candidates["for_correction_or_removal"] == [
        {"meal_thread_id": 77, "meal_item_id": 501}
    ]
    assert target_candidates["read_only"] is True
    assert target_candidates["mutation_authority"] is False
