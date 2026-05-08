from __future__ import annotations

from typing import Any


def build_calibration_proposal_read_models() -> list[dict[str, Any]]:
    return [
        {
            "name": "calibration_proposal_inbox",
            "aliases": [],
            "canonical_name_required_for_current_shell": True,
            "backend_route": "/calibration/proposals/open",
            "read_function": "app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox",
            "truth_owner": ["calibration_proposal_artifacts"],
            "stable_fields": [
                "proposal_container_id",
                "proposal_type",
                "proposal_status",
                "top_option_id",
                "local_date",
                "proposal_family",
                "created_at",
                "accepted_at",
                "options[].proposal_option_id",
                "options[].option_type",
                "options[].option_label",
                "options[].option_summary",
                "options[].rank_order",
                "options[].is_primary",
                "options[].effect_payload",
            ],
            "current_shell_allowed_use": "render_inbox_mirror_preserving_backend_order",
            "current_shell_forbidden": [
                "create_proposals",
                "rank_proposals",
                "rewrite_options",
                "expose_full_diagnostic_metadata",
                "accept_defer_reject_outside_stored_action",
            ],
        },
        {
            "name": "calibration_proposal_history",
            "aliases": [],
            "canonical_name_required_for_current_shell": True,
            "backend_route": "/calibration/proposals/history",
            "read_function": "app.composition.calibration_proposal_inbox.load_calibration_proposal_history",
            "truth_owner": ["calibration_proposal_artifacts"],
            "stable_fields": [
                "proposal_container_id",
                "proposal_type",
                "proposal_status",
                "top_option_id",
                "local_date",
                "proposal_family",
                "created_at",
                "accepted_at",
                "expired_at",
                "expiry_reason",
                "primary_option_type",
                "primary_option_label",
                "primary_option_summary",
            ],
            "current_shell_allowed_use": "render_read_only_calibration_proposal_audit_history",
            "current_shell_forbidden": [
                "create_proposals",
                "rank_proposals",
                "rewrite_options",
                "accept_defer_reject_from_history",
                "expose_full_diagnostic_metadata",
                "effect_payload",
                "options",
                "proposal_policy_packet",
                "trace_envelope",
            ],
        },
    ]


__all__ = ["build_calibration_proposal_read_models"]
