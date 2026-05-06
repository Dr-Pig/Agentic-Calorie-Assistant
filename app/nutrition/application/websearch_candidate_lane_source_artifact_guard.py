from __future__ import annotations

from typing import Any


def source_artifact_boundary_blockers(
    *,
    live_diagnostic_report: dict[str, Any],
    contract_probe_artifact: dict[str, Any],
    repair_pack_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for artifact, prefix in (
        (live_diagnostic_report, "live_report"),
        (contract_probe_artifact, "contract_probe"),
        (repair_pack_artifact, "repair_pack"),
        (preflight_artifact, "preflight"),
    ):
        blockers.extend(_overclaim_blockers(artifact=artifact, prefix=prefix))
    for artifact, prefix, keys in (
        (
            live_diagnostic_report,
            "live_report",
            (
                "source_live_websearch_used",
                "runtime_truth_changed",
                "runtime_mutation_attempted",
                "readiness_claimed",
                "self_use_approved",
                "production_selected",
            ),
        ),
        (
            contract_probe_artifact,
            "contract_probe",
            (
                "live_provider_used",
                "live_websearch_used",
                "runtime_truth_changed",
                "runtime_mutation_attempted",
                "readiness_claimed",
                "self_use_approved",
                "production_selected",
                "manager_contract_changed",
                "prompt_changed",
                "schema_changed",
            ),
        ),
        (
            repair_pack_artifact,
            "repair_pack",
            (
                "runtime_truth_changed",
                "runtime_mutation_attempted",
                "readiness_claimed",
                "manager_contract_changed",
                "prompt_changed",
                "schema_changed",
            ),
        ),
        (
            preflight_artifact,
            "preflight",
            (
                "live_provider_used",
                "live_websearch_used",
                "live_extract_used",
                "runtime_truth_changed",
                "runtime_mutation_allowed",
                "manager_context_changed",
                "packetizer_format_changed",
                "readiness_claimed",
                "ready_for_runtime_truth",
            ),
        ),
    ):
        blockers.extend(_required_false_flag_blockers(artifact=artifact, prefix=prefix, keys=keys))
    for artifact, prefix, required in (
        (
            live_diagnostic_report,
            "live_report",
            (
                "no_live_provider_call",
                "no_live_websearch_call",
                "no_kimi_call",
                "no_runtime_mutation",
                "no_websearch_runtime_truth",
                "no_fooddb_truth_promotion",
                "no_exact_card_truth_promotion",
                "no_readiness_claim",
            ),
        ),
        (
            contract_probe_artifact,
            "contract_probe",
            (
                "no_live_provider_call",
                "no_live_websearch_call",
                "no_kimi_call",
                "no_prompt_or_schema_change",
                "no_runtime_mutation",
                "no_websearch_runtime_truth",
                "no_fooddb_truth_promotion",
                "no_exact_card_truth_promotion",
                "no_readiness_claim",
            ),
        ),
        (
            repair_pack_artifact,
            "repair_pack",
            (
                "no_live_provider_call",
                "no_live_websearch_call",
                "no_prompt_or_schema_change",
                "no_manager_contract_change",
                "no_runtime_truth_promotion",
                "no_exact_card_truth_promotion",
                "no_runtime_mutation",
                "no_packetizer_format_change",
                "no_manager_context_change",
                "no_readiness_claim",
            ),
        ),
        (
            preflight_artifact,
            "preflight",
            (
                "no_live_websearch_call",
                "no_live_extract_call",
                "no_live_provider_call",
                "no_websearch_runtime_truth",
                "no_exact_card_truth_promotion",
                "no_runtime_mutation",
                "no_manager_context_change",
                "no_packetizer_format_change",
                "no_readiness_claim",
            ),
        ),
    ):
        blockers.extend(
            _required_non_claim_blockers(
                artifact=artifact,
                prefix=prefix,
                required=required,
            )
        )
    return blockers


def _overclaim_blockers(*, artifact: dict[str, Any], prefix: str) -> list[str]:
    blockers: list[str] = []
    for key, suffix in (
        ("readiness_claimed", "claimed_readiness"),
        ("runtime_truth_changed", "changed_runtime_truth"),
        ("runtime_mutation_attempted", "attempted_runtime_mutation"),
        ("mutation_changed", "changed_mutation"),
        ("prompt_changed", "changed_prompt"),
        ("schema_changed", "changed_schema"),
        ("manager_contract_changed", "changed_manager_contract"),
        ("shared_contract_changed", "changed_shared_contract"),
        ("manager_context_changed", "changed_manager_context"),
        ("packetizer_format_changed", "changed_packetizer_format"),
        ("live_provider_used", "used_live_provider"),
        ("live_websearch_used", "used_live_websearch"),
        ("self_use_approved", "claimed_self_use"),
        ("private_self_use_approved", "claimed_private_self_use"),
        ("production_selected", "claimed_production_selection"),
        ("product_readiness_claimed", "claimed_product_readiness"),
    ):
        if key in artifact and artifact.get(key) is not False:
            blockers.append(f"{prefix}_{suffix}")
    return blockers


def _required_false_flag_blockers(
    *,
    artifact: dict[str, Any],
    prefix: str,
    keys: tuple[str, ...],
) -> list[str]:
    return [
        f"{prefix}_{key}_missing_or_not_false"
        for key in keys
        if artifact.get(key) is not False
    ]


def _required_non_claim_blockers(
    *,
    artifact: dict[str, Any],
    prefix: str,
    required: tuple[str, ...],
) -> list[str]:
    non_claims = artifact.get("non_claims")
    if not isinstance(non_claims, list):
        return [f"{prefix}_non_claims_missing"]
    present = {str(item) for item in non_claims if isinstance(item, str)}
    return [
        f"{prefix}_missing_non_claim.{claim}"
        for claim in required
        if claim not in present
    ]


__all__ = ["source_artifact_boundary_blockers"]
