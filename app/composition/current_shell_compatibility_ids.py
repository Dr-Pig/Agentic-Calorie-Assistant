from __future__ import annotations

from typing import Any

CURRENT_SHELL_CONTRACT_KEY = "current_shell_contract"
LEGACY_CURRENT_SHELL_CONTRACT_KEYS = ("plce_contract",)

CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_GROUP_ID = "current_shell_compatibility_review_bundle"
LEGACY_REVIEW_BUNDLE_GROUP_IDS = ("pl_ce_review_bundle",)
CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_review_bundle_v1"
)
LEGACY_REVIEW_BUNDLE_ARTIFACT_TYPES = ("accurate_intake_product_loop_review_bundle_v1",)
CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_READY_STATUS = (
    "current_shell_compatibility_context_diagnostic_ready_for_human_review"
)
LEGACY_REVIEW_BUNDLE_READY_STATUSES = (
    "product_loop_context_diagnostic_ready_for_human_review",
)
CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_CLAIM_SCOPE = (
    "current_shell_compatibility_context_review_checkpoint"
)
LEGACY_REVIEW_BUNDLE_CLAIM_SCOPES = ("product_loop_context_review_checkpoint",)

CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID = (
    "current_shell_compatibility_local_review_decision_pack"
)
LEGACY_LOCAL_REVIEW_GROUP_IDS = ("pl_ce_local_review_decision_pack",)
CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_local_review_decision_pack"
)
LEGACY_LOCAL_REVIEW_ARTIFACT_TYPES = ("accurate_intake_pl_ce_local_review_decision_pack",)
CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS = (
    "ready_for_human_current_shell_compatibility_review"
)
LEGACY_LOCAL_REVIEW_READY_STATUSES = ("ready_for_human_pl_ce_review",)
CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_CLAIM_SCOPE = (
    "current_shell_compatibility_local_review_decision_pack"
)
LEGACY_LOCAL_REVIEW_CLAIM_SCOPES = ("pl_ce_local_review_decision_pack",)
CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_NEXT_STEP = (
    "human_review_current_shell_compatibility_checkpoint"
)
CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_FIX_STEP = (
    "fix_current_shell_compatibility_local_evidence"
)
CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_local_review_evidence_manifest"
)
LEGACY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_local_review_evidence_manifest",
)
CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG = (
    "ready_for_current_shell_compatibility_local_review"
)
LEGACY_READY_FOR_LOCAL_REVIEW_FLAGS = ("ready_for_pl_ce_local_review",)

CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID = (
    "current_shell_compatibility_local_mvp_candidate_bundle"
)
LEGACY_LOCAL_MVP_GROUP_IDS = ("pl_ce_local_mvp_candidate_bundle",)
CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_local_mvp_candidate_bundle"
)
LEGACY_LOCAL_MVP_ARTIFACT_TYPES = ("accurate_intake_pl_ce_local_mvp_candidate_bundle",)
CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS = (
    "current_shell_compatibility_local_mvp_candidate_ready_for_human_review"
)
LEGACY_LOCAL_MVP_READY_STATUSES = ("pl_ce_local_mvp_candidate_ready_for_human_review",)
CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_CLAIM_SCOPE = (
    "current_shell_compatibility_local_mvp_candidate_bundle"
)
LEGACY_LOCAL_MVP_CLAIM_SCOPES = ("pl_ce_local_mvp_candidate_bundle",)

CURRENT_SHELL_COMPATIBILITY_CONTEXT_COVERAGE_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_context_coverage_matrix"
)
LEGACY_CONTEXT_COVERAGE_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_context_coverage_matrix",
)

CURRENT_SHELL_COMPATIBILITY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_ui_context_alignment_pack"
)
LEGACY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_ui_context_alignment_pack",
)

CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_browser_activation_evidence_gate"
)
CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_GROUP_ID = (
    "current_shell_compatibility_browser_activation_evidence_gate"
)
LEGACY_BROWSER_ACTIVATION_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_browser_activation_evidence_gate",
)
LEGACY_BROWSER_ACTIVATION_GROUP_IDS = ("pl_ce_browser_activation_evidence_gate",)

CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_product_pages_self_use_flow_gate"
)
CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_GROUP_ID = (
    "current_shell_compatibility_product_pages_self_use_flow_gate"
)
LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_product_pages_self_use_flow_gate",
)
LEGACY_PRODUCT_PAGES_FLOW_GROUP_IDS = ("pl_ce_product_pages_self_use_flow_gate",)

CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID = (
    "current_shell_compatibility_activation_review_manifest"
)
LEGACY_ACTIVATION_REVIEW_GROUP_IDS = ("pl_ce_activation_review_manifest",)
CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_activation_review_manifest"
)
LEGACY_ACTIVATION_REVIEW_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_activation_review_manifest",
)
CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_READY_STATUS = (
    "current_shell_compatibility_activation_review_manifest_ready"
)
LEGACY_ACTIVATION_REVIEW_READY_STATUSES = ("pl_ce_activation_review_manifest_ready",)
CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_CLAIM_SCOPE = (
    "current_shell_compatibility_activation_review_manifest_for_human_review_only"
)
LEGACY_ACTIVATION_REVIEW_CLAIM_SCOPES = (
    "pl_ce_activation_review_manifest_for_human_review_only",
)

CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_metadata_freshness_pack"
)
LEGACY_METADATA_FRESHNESS_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_metadata_freshness_pack",
)
CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS = (
    "metadata_freshness_ready_for_current_shell_compatibility_local_review"
)
LEGACY_METADATA_FRESHNESS_READY_STATUSES = (
    "metadata_freshness_ready_for_pl_ce_local_review",
)
CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_CLAIM_SCOPE = (
    "current_shell_compatibility_metadata_freshness_status_only"
)
LEGACY_METADATA_FRESHNESS_CLAIM_SCOPES = ("pl_ce_metadata_freshness_status_only",)

CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_current_metadata_freshness_pack"
)
LEGACY_CURRENT_METADATA_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_current_metadata_freshness_pack",
)
CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS = (
    "current_shell_compatibility_current_metadata_freshness_ready_for_serial_handoff"
)
LEGACY_CURRENT_METADATA_READY_STATUSES = ("current_metadata_freshness_ready_for_serial_handoff",)
CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_CLAIM_SCOPE = (
    "current_shell_compatibility_current_chain_metadata_freshness_status_only"
)
LEGACY_CURRENT_METADATA_CLAIM_SCOPES = ("pl_ce_current_chain_metadata_freshness_status_only",)

CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_serial_handoff"
)
LEGACY_SERIAL_HANDOFF_ARTIFACT_TYPES = ("accurate_intake_pl_ce_serial_handoff",)
CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_CLAIM_SCOPE = (
    "current_shell_compatibility_merge_queue_handoff_for_review_only"
)
LEGACY_SERIAL_HANDOFF_CLAIM_SCOPES = ("pl_ce_merge_queue_handoff_for_review_only",)

CURRENT_SHELL_COMPATIBILITY_MERGE_QUEUE_METADATA_ARTIFACT_TYPE = (
    "accurate_intake_current_shell_compatibility_merge_queue_metadata"
)
LEGACY_MERGE_QUEUE_METADATA_ARTIFACT_TYPES = (
    "accurate_intake_pl_ce_merge_queue_metadata",
)

LEGACY_LIVE_DIAGNOSTIC_DECISION_FLAG = "ready_for_live_diagnostic_decision"
LEGACY_FDB_INTEGRATION_FLAG = "ready_for_fdb_integration"
LEGACY_BLOCKED_READINESS_FLAGS = (
    LEGACY_LIVE_DIAGNOSTIC_DECISION_FLAG,
    LEGACY_FDB_INTEGRATION_FLAG,
)


def matches_alias(value: Any, canonical: str, *legacy_aliases: str) -> bool:
    return str(value or "") in (canonical, *legacy_aliases)


def first_group_payload(
    evidence: dict[str, Any],
    canonical_group_id: str,
    *legacy_group_ids: str,
) -> tuple[dict[str, Any], str]:
    if canonical_group_id in evidence:
        payload = evidence.get(canonical_group_id)
        return (dict(payload) if isinstance(payload, dict) else {}, canonical_group_id)
    for group_id in legacy_group_ids:
        if group_id in evidence:
            payload = evidence.get(group_id)
            return (dict(payload) if isinstance(payload, dict) else {}, group_id)
    return {}, canonical_group_id


def set_legacy_alias_metadata(
    payload: dict[str, Any],
    *,
    legacy_artifact_types: tuple[str, ...] = (),
    legacy_statuses: tuple[str, ...] = (),
    legacy_claim_scopes: tuple[str, ...] = (),
    legacy_group_ids: tuple[str, ...] = (),
    legacy_flags: tuple[str, ...] = (),
) -> dict[str, Any]:
    if legacy_artifact_types:
        payload["legacy_artifact_type_aliases"] = list(legacy_artifact_types)
    if legacy_statuses:
        payload["legacy_status_aliases"] = list(legacy_statuses)
    if legacy_claim_scopes:
        payload["legacy_claim_scope_aliases"] = list(legacy_claim_scopes)
    if legacy_group_ids:
        payload["legacy_group_id_aliases"] = list(legacy_group_ids)
    if legacy_flags:
        payload["legacy_flag_aliases"] = list(legacy_flags)
    return payload


__all__ = [
    "CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_CLAIM_SCOPE",
    "CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS",
    "CURRENT_SHELL_COMPATIBILITY_CONTEXT_COVERAGE_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_GROUP_ID",
    "CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_GROUP_ID",
    "CURRENT_SHELL_COMPATIBILITY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_CLAIM_SCOPE",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_FIX_STEP",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_CLAIM_SCOPE",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_NEXT_STEP",
    "CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS",
    "CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_CLAIM_SCOPE",
    "CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS",
    "CURRENT_SHELL_COMPATIBILITY_MERGE_QUEUE_METADATA_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG",
    "CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_CLAIM_SCOPE",
    "CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID",
    "CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_READY_STATUS",
    "CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_CLAIM_SCOPE",
    "CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_GROUP_ID",
    "CURRENT_SHELL_COMPATIBILITY_REVIEW_BUNDLE_READY_STATUS",
    "CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_ARTIFACT_TYPE",
    "CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_CLAIM_SCOPE",
    "CURRENT_SHELL_CONTRACT_KEY",
    "LEGACY_ACTIVATION_REVIEW_ARTIFACT_TYPES",
    "LEGACY_ACTIVATION_REVIEW_CLAIM_SCOPES",
    "LEGACY_ACTIVATION_REVIEW_GROUP_IDS",
    "LEGACY_ACTIVATION_REVIEW_READY_STATUSES",
    "LEGACY_BROWSER_ACTIVATION_ARTIFACT_TYPES",
    "LEGACY_BROWSER_ACTIVATION_GROUP_IDS",
    "LEGACY_BLOCKED_READINESS_FLAGS",
    "LEGACY_CONTEXT_COVERAGE_ARTIFACT_TYPES",
    "LEGACY_CURRENT_METADATA_ARTIFACT_TYPES",
    "LEGACY_CURRENT_METADATA_CLAIM_SCOPES",
    "LEGACY_CURRENT_METADATA_READY_STATUSES",
    "LEGACY_FDB_INTEGRATION_FLAG",
    "LEGACY_CURRENT_SHELL_CONTRACT_KEYS",
    "LEGACY_LIVE_DIAGNOSTIC_DECISION_FLAG",
    "LEGACY_LOCAL_MVP_ARTIFACT_TYPES",
    "LEGACY_LOCAL_MVP_CLAIM_SCOPES",
    "LEGACY_LOCAL_MVP_GROUP_IDS",
    "LEGACY_LOCAL_MVP_READY_STATUSES",
    "LEGACY_LOCAL_REVIEW_ARTIFACT_TYPES",
    "LEGACY_LOCAL_REVIEW_CLAIM_SCOPES",
    "LEGACY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPES",
    "LEGACY_LOCAL_REVIEW_GROUP_IDS",
    "LEGACY_LOCAL_REVIEW_READY_STATUSES",
    "LEGACY_MERGE_QUEUE_METADATA_ARTIFACT_TYPES",
    "LEGACY_METADATA_FRESHNESS_ARTIFACT_TYPES",
    "LEGACY_METADATA_FRESHNESS_CLAIM_SCOPES",
    "LEGACY_METADATA_FRESHNESS_READY_STATUSES",
    "LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES",
    "LEGACY_PRODUCT_PAGES_FLOW_GROUP_IDS",
    "LEGACY_READY_FOR_LOCAL_REVIEW_FLAGS",
    "LEGACY_REVIEW_BUNDLE_ARTIFACT_TYPES",
    "LEGACY_REVIEW_BUNDLE_CLAIM_SCOPES",
    "LEGACY_REVIEW_BUNDLE_GROUP_IDS",
    "LEGACY_REVIEW_BUNDLE_READY_STATUSES",
    "LEGACY_SERIAL_HANDOFF_ARTIFACT_TYPES",
    "LEGACY_SERIAL_HANDOFF_CLAIM_SCOPES",
    "LEGACY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPES",
    "first_group_payload",
    "matches_alias",
    "set_legacy_alias_metadata",
]
