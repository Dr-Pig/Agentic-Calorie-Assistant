from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


HOLDOUT_RECORD_IDS = [
    "negative-bitter-melon",
    "negative-spicy",
    "negative-vegetarian",
    "negative-bland",
    "negative-eggplant",
]
IGNORED_SIGNAL_IDS = ["negative-dessert-ignored"]


def build_memory_record_holdout_turns() -> list[dict[str, Any]]:
    return [
        {
            "turn_id": "t6-negative-preference-holdout",
            "lab_now_minute": 110,
            "post_turn_memory_signal_events": [
                _negative("negative-bitter-melon", "bitter_melon", "block"),
                _negative("negative-spicy", "spicy", "block"),
                _negative("negative-vegetarian", "vegetarian", "downrank"),
                _negative("negative-bland", "bland", "downrank"),
                _negative("negative-eggplant", "eggplant", "downrank"),
                _negative("negative-dessert-ignored", "dessert", "downrank"),
            ],
            "post_turn_memory_review_decisions": [
                {
                    "candidate_id": record_id,
                    "decision": "promote",
                    "confirmed": True,
                    "reviewer": "lab-human",
                    "reason": "holdout_negative_preference_calibration",
                }
                for record_id in HOLDOUT_RECORD_IDS
            ]
            + [
                {
                    "candidate_id": "negative-dessert-ignored",
                    "decision": "reject",
                    "confirmed": False,
                    "reviewer": "lab-human",
                    "reason": "user_marked_do_not_remember",
                }
            ],
        }
    ]


def build_memory_record_holdout_candidates() -> list[dict[str, Any]]:
    return [
        _candidate("candidate-bitter-melon", "bitter_melon"),
        _candidate("candidate-spicy-ramen", "spicy"),
        _candidate("candidate-vegetarian-bowl", "vegetarian"),
        _candidate("candidate-bland-soup", "bland"),
        _candidate("candidate-eggplant-rice", "eggplant"),
        _candidate("candidate-dessert", "dessert"),
    ]


def build_memory_record_holdout_report(session_artifact: Mapping[str, Any]) -> dict[str, Any]:
    written = _written_ids(session_artifact)
    ignored = _ignored_ids(session_artifact)
    blockers: list[str] = []
    missing = [record_id for record_id in HOLDOUT_RECORD_IDS if record_id not in written]
    if missing:
        blockers.extend(f"missing_record:{record_id}" for record_id in missing)
    missing_ignored = [
        signal_id for signal_id in IGNORED_SIGNAL_IDS if signal_id not in ignored
    ]
    if missing_ignored:
        blockers.extend(f"missing_ignored_signal:{signal_id}" for signal_id in missing_ignored)
    return {
        "artifact_type": "advanced_product_lab_memory_record_holdout_report",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_holdout.py",
        "consumer": "advanced_product_lab_memory_record_regression_suite",
        "retirement_trigger": "approved_live_dogfood_trace_replacement",
        "session_id": str(session_artifact.get("session_id") or ""),
        "session_artifact_path": str(session_artifact.get("session_artifact_path") or ""),
        "holdout_case_count": 6,
        "confirmed_negative_record_ids": [
            record_id for record_id in HOLDOUT_RECORD_IDS if record_id in written
        ],
        "ignored_signal_ids": [
            signal_id for signal_id in IGNORED_SIGNAL_IDS if signal_id in ignored
        ],
        "blockers": blockers,
        "mainline_activation_enabled": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        **dict(FALSE_FLAGS),
    }


def _negative(signal_id: str, subject: str, strength: str) -> dict[str, Any]:
    return {
        "signal_id": signal_id,
        "signal_type": "negative_preference",
        "summary": f"Negative preference holdout for {subject}.",
        "strength": strength,
        "source_object_refs": [f"turn:t6:{signal_id}"],
        "blocked_item_patterns": [subject],
        "intended_consumers": ["recommendation"],
    }


def _candidate(candidate_id: str, subject: str) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "subject_keys": [subject],
        "source_refs": [f"holdout:{candidate_id}"],
    }


def _written_ids(session_artifact: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for write in session_artifact.get("memory_record_write_artifacts") or []:
        if isinstance(write, Mapping):
            ids.update(str(item) for item in write.get("written_record_ids") or [])
    return ids


def _ignored_ids(session_artifact: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for write in session_artifact.get("memory_record_write_artifacts") or []:
        if isinstance(write, Mapping):
            ids.update(
                str(item) for item in write.get("pending_or_rejected_signal_ids") or []
            )
    return ids


__all__ = [
    "build_memory_record_holdout_candidates",
    "build_memory_record_holdout_report",
    "build_memory_record_holdout_turns",
]
