from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from app.composition.current_shell_compatibility_ids import (  # noqa: E402
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
)
from scripts.build_accurate_intake_local_web_self_use_candidate_v2 import (  # noqa: E402
    build_local_web_self_use_candidate_v2,
)
from scripts.build_accurate_intake_pre_live_self_use_decision_pack import (  # noqa: E402
    build_pre_live_self_use_decision_pack,
)

DEFAULT_EVIDENCE_PATHS = {
    "phase_c_gate": ROOT / "artifacts" / "phase_c_gate.json",
    "accurate_intake_mvp_gate": ROOT / "artifacts" / "accurate_intake_mvp_gate.json",
    "browser_shell_smoke": ROOT / "artifacts" / "accurate_intake_browser_shell_smoke.json",
    "chat_history_reload_gate": ROOT / "artifacts" / "accurate_intake_chat_history_reload_gate.json",
    "free_text_manual_target_gate": ROOT / "artifacts" / "accurate_intake_free_text_manual_target_gate.json",
    "dogfood_review_queue": ROOT / "artifacts" / "accurate_intake_dogfood_review_queue.json",
    "local_dogfood_data_hygiene": ROOT / "artifacts" / "accurate_intake_local_dogfood_data_hygiene.json",
    "local_operator_data_hygiene_bundle": ROOT
    / "artifacts"
    / "accurate_intake_local_operator_data_hygiene_bundle.json",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_local_review_decision_pack.json",
    "product_pages_self_use_flow_gate": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_product_pages_self_use_flow_gate.json",
    "ui_context_alignment_pack": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_ui_context_alignment_pack.json",
    "today_macro_mirror_gate": ROOT / "artifacts" / "accurate_intake_today_macro_mirror_gate.json",
    "bootstrap_same_truth_gate": ROOT / "artifacts" / "accurate_intake_bootstrap_same_truth_gate.json",
    "body_observation_same_truth_gate": ROOT
    / "artifacts"
    / "accurate_intake_body_observation_same_truth_gate.json",
    "clarify_commit_correction_same_truth_gate": ROOT
    / "artifacts"
    / "accurate_intake_clarify_commit_correction_same_truth_gate.json",
    "browser_activation_evidence_gate": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_browser_activation_evidence_gate.json",
    "manager_tool_surface_inventory": ROOT
    / "artifacts"
    / "accurate_intake_manager_tool_surface_inventory.json",
    "non_fooddb_manager_tool_contract": ROOT
    / "artifacts"
    / "accurate_intake_non_fooddb_manager_tool_contract.json",
    "manager_tool_choice_regression_wall": ROOT
    / "artifacts"
    / "accurate_intake_manager_tool_choice_regression_wall.json",
    "context_conditioned_intent_wall": ROOT
    / "artifacts"
    / "accurate_intake_context_conditioned_intent_wall_ci.json",
    "non_fooddb_read_only_tool_loop_fake_smoke": ROOT
    / "artifacts"
    / "accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke.json",
    "non_fooddb_mutation_tool_guard_smoke": ROOT
    / "artifacts"
    / "accurate_intake_non_fooddb_mutation_tool_guard_smoke.json",
    "manager_intent_readiness_review_pack": ROOT
    / "artifacts"
    / "accurate_intake_manager_intent_readiness_review_pack.json",
    "context_live_diagnostic_case_matrix": ROOT
    / "artifacts"
    / "accurate_intake_context_live_diagnostic_case_matrix.json",
    "context_live_diagnostic_anti_overfit_guard": ROOT
    / "artifacts"
    / "accurate_intake_context_live_diagnostic_anti_overfit_guard.json",
    "context_live_diagnostic_holdout_plan": ROOT
    / "artifacts"
    / "accurate_intake_context_live_diagnostic_holdout_plan.json",
    "context_live_provider_input_preflight": ROOT
    / "artifacts"
    / "accurate_intake_context_live_provider_input_preflight.json",
    "context_live_response_contract_dry_run": ROOT
    / "artifacts"
    / "accurate_intake_context_live_response_contract_dry_run.json",
    "context_live_diagnostic_gate": ROOT
    / "artifacts"
    / "accurate_intake_context_live_diagnostic_gate.json",
}
DEFAULT_PRE_LIVE_EVIDENCE_OUTPUT = ROOT / "artifacts" / "accurate_intake_pre_live_evidence.json"
DEFAULT_PRE_LIVE_OUTPUT = ROOT / "artifacts" / "accurate_intake_pre_live_self_use_decision_pack.json"
DEFAULT_CANDIDATE_OUTPUT = ROOT / "artifacts" / "accurate_intake_local_web_self_use_candidate_v2.json"


def _artifact_identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if str(payload.get("status") or "") == "missing":
        return []
    blockers: list[str] = []
    if payload.get("artifact_schema_version") != "1.0":
        blockers.append(f"{group_id}_artifact_schema_version_missing")
    if not any(payload.get(key) for key in ("artifact_type", "gate_id", "claim_scope")):
        blockers.append(f"{group_id}_artifact_identity_missing")
    if group_id == "phase_c_gate":
        identity_text = " ".join(
            str(payload.get(key) or "")
            for key in ("artifact_type", "gate_id", "claim_scope")
        ).lower()
        if "phase_c" not in identity_text and "same_truth" not in identity_text:
            blockers.append("phase_c_gate_artifact_identity_mismatch")
    return blockers


def _missing_payload(group_id: str, path: Path) -> dict[str, Any]:
    return {
        "artifact_type": "missing_local_web_self_use_candidate_v2_evidence",
        "status": "missing",
        "group_id": group_id,
        "artifact_path": str(path),
        "autofix_attempted": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "private_self_use_approved": False,
        "product_readiness_claimed": False,
    }


def _phase_c_payload_from_mvp_gate(mvp_gate: dict[str, Any], path: Path) -> dict[str, Any]:
    groups = mvp_gate.get("groups") if isinstance(mvp_gate.get("groups"), list) else []
    ledger_group = next(
        (
            dict(group)
            for group in groups
            if isinstance(group, dict)
            and group.get("group_id") == "ledger_truth_and_read_model"
        ),
        {},
    )
    status = (
        "pass"
        if mvp_gate.get("status") == "pass" and ledger_group.get("status") == "pass"
        else "blocked"
    )
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_phase_c_gate_from_mvp_gate",
        "gate_id": "phase_c_gate_from_accurate_intake_mvp_gate",
        "claim_scope": "derived_phase_c_same_truth_evidence_from_local_mvp_gate",
        "status": status,
        "source_artifact_path": str(path),
        "source_gate_id": mvp_gate.get("gate_id"),
        "source_group_id": "ledger_truth_and_read_model",
        "source_group_status": ledger_group.get("status"),
        "derived_from_existing_artifact": True,
        "autofix_attempted": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "private_self_use_approved": False,
        "product_readiness_claimed": False,
    }


def _read_or_missing(group_id: str, path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return _missing_payload(group_id, path), True
    payload = read_json_artifact(path)
    payload.setdefault("artifact_path", str(path))
    return payload, False


def build_local_web_candidate_gate_evidence(
    *,
    path_overrides: dict[str, Path] | None = None,
) -> dict[str, Any]:
    evidence_paths = {
        group_id: Path(path_overrides.get(group_id, default_path)) if path_overrides else default_path
        for group_id, default_path in DEFAULT_EVIDENCE_PATHS.items()
    }
    missing_evidence: list[str] = []
    evidence_blockers: list[str] = []
    invalid_evidence: list[str] = []
    evidence: dict[str, Any] = {}
    for group_id, path in evidence_paths.items():
        if group_id == "phase_c_gate" and not path.exists():
            mvp_gate_path = evidence_paths["accurate_intake_mvp_gate"]
            if mvp_gate_path.exists():
                payload, missing = _phase_c_payload_from_mvp_gate(
                    read_json_artifact(mvp_gate_path),
                    mvp_gate_path,
                ), False
            else:
                payload, missing = _read_or_missing(group_id, path)
        else:
            payload, missing = _read_or_missing(group_id, path)
        evidence[group_id] = payload
        if missing:
            missing_evidence.append(group_id)
        else:
            identity_blockers = _artifact_identity_blockers(group_id, payload)
            if identity_blockers:
                invalid_evidence.append(group_id)
                evidence_blockers.extend(identity_blockers)
    status = (
        "blocked_missing_evidence"
        if missing_evidence
        else "blocked_invalid_evidence"
        if evidence_blockers
        else "complete"
    )
    evidence["_evidence_metadata"] = {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_local_web_self_use_candidate_v2_gate_evidence",
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "required_evidence": list(DEFAULT_EVIDENCE_PATHS),
        "missing_evidence": missing_evidence,
        "invalid_evidence": invalid_evidence,
        "blockers": sorted(list(dict.fromkeys(evidence_blockers))),
        "local_web_candidate_gate_blocked": status != "complete",
        "autofix_attempted": False,
        "local_only": True,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "private_self_use_approved": False,
        "product_readiness_claimed": False,
        "evidence_paths": {
            group_id: str(path)
            for group_id, path in evidence_paths.items()
        },
    }
    return evidence


def build_candidate_evidence_payload(
    pre_live_evidence: dict[str, Any],
    pre_live_pack: dict[str, Any],
) -> dict[str, Any]:
    mapped = {
        "browser_shell_smoke": pre_live_evidence["browser_shell_smoke"],
        "chat_history_reload": pre_live_evidence["chat_history_reload_gate"],
        "free_text_manual_target": pre_live_evidence["free_text_manual_target_gate"],
        "dogfood_review_queue": pre_live_evidence["dogfood_review_queue"],
        "local_dogfood_data_hygiene": pre_live_evidence["local_dogfood_data_hygiene"],
        "pre_live_decision_pack": pre_live_pack,
        CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: pre_live_evidence[
            CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID
        ],
        "product_pages_self_use_flow_gate": pre_live_evidence["product_pages_self_use_flow_gate"],
        "ui_context_alignment_pack": pre_live_evidence["ui_context_alignment_pack"],
        "today_macro_mirror_gate": pre_live_evidence["today_macro_mirror_gate"],
        "bootstrap_same_truth_gate": pre_live_evidence["bootstrap_same_truth_gate"],
        "body_observation_same_truth_gate": pre_live_evidence["body_observation_same_truth_gate"],
        "clarify_commit_correction_same_truth_gate": pre_live_evidence[
            "clarify_commit_correction_same_truth_gate"
        ],
        "browser_activation_evidence_gate": pre_live_evidence["browser_activation_evidence_gate"],
        "manager_tool_surface_inventory": pre_live_evidence["manager_tool_surface_inventory"],
        "non_fooddb_manager_tool_contract": pre_live_evidence["non_fooddb_manager_tool_contract"],
        "manager_tool_choice_regression_wall": pre_live_evidence["manager_tool_choice_regression_wall"],
        "context_conditioned_intent_wall": pre_live_evidence["context_conditioned_intent_wall"],
        "non_fooddb_read_only_tool_loop_fake_smoke": pre_live_evidence[
            "non_fooddb_read_only_tool_loop_fake_smoke"
        ],
        "non_fooddb_mutation_tool_guard_smoke": pre_live_evidence[
            "non_fooddb_mutation_tool_guard_smoke"
        ],
        "manager_intent_readiness_review_pack": pre_live_evidence[
            "manager_intent_readiness_review_pack"
        ],
        "context_live_diagnostic_case_matrix": pre_live_evidence["context_live_diagnostic_case_matrix"],
        "context_live_diagnostic_anti_overfit_guard": pre_live_evidence[
            "context_live_diagnostic_anti_overfit_guard"
        ],
        "context_live_diagnostic_holdout_plan": pre_live_evidence[
            "context_live_diagnostic_holdout_plan"
        ],
        "context_live_provider_input_preflight": pre_live_evidence[
            "context_live_provider_input_preflight"
        ],
        "context_live_response_contract_dry_run": pre_live_evidence[
            "context_live_response_contract_dry_run"
        ],
        "context_live_diagnostic_gate": pre_live_evidence["context_live_diagnostic_gate"],
        "local_operator_data_hygiene_bundle": pre_live_evidence["local_operator_data_hygiene_bundle"],
        "local_web_candidate_gate_evidence": pre_live_evidence["_evidence_metadata"],
        "mvp_gate": pre_live_evidence["accurate_intake_mvp_gate"],
        "phase_c_gate": pre_live_evidence["phase_c_gate"],
    }
    return {
        group_id: payload
        for group_id, payload in mapped.items()
        if not (isinstance(payload, dict) and payload.get("status") == "missing")
    }


def run_local_web_self_use_candidate_v2_gate(
    *,
    pre_live_evidence_output: Path,
    pre_live_output: Path,
    candidate_output: Path,
    path_overrides: dict[str, Path] | None = None,
) -> dict[str, Any]:
    pre_live_evidence = build_local_web_candidate_gate_evidence(path_overrides=path_overrides)
    pre_live_pack = build_pre_live_self_use_decision_pack(pre_live_evidence)
    candidate = build_local_web_self_use_candidate_v2(
        build_candidate_evidence_payload(pre_live_evidence, pre_live_pack)
    )

    write_json_artifact(pre_live_evidence_output, pre_live_evidence)
    write_json_artifact(pre_live_output, pre_live_pack)
    write_json_artifact(candidate_output, candidate)

    candidate_payload = candidate["local_web_self_use_candidate_v2"]
    return {
        "pre_live_evidence": str(pre_live_evidence_output),
        "pre_live_decision_pack": str(pre_live_output),
        "local_web_candidate": str(candidate_output),
        "evidence_status": pre_live_evidence["_evidence_metadata"]["status"],
        "pre_live_selected_option": pre_live_pack["selected_option"],
        "candidate_prepared": candidate_payload["candidate_prepared"],
        "missing_evidence": pre_live_evidence["_evidence_metadata"]["missing_evidence"],
        "candidate_blockers": candidate_payload["blockers"],
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "private_self_use_approved": False,
        "product_readiness_claimed": False,
    }


def _parse_artifact_overrides(values: list[str]) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--artifact must be group_id=path, got: {value}")
        group_id, raw_path = value.split("=", 1)
        if group_id not in DEFAULT_EVIDENCE_PATHS:
            raise ValueError(f"Unknown local web candidate evidence group: {group_id}")
        overrides[group_id] = Path(raw_path)
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the local web self-use candidate v2 gate from local artifacts."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Override an evidence path as group_id=path. May be passed multiple times.",
    )
    parser.add_argument("--pre-live-evidence-output", default=str(DEFAULT_PRE_LIVE_EVIDENCE_OUTPUT))
    parser.add_argument("--pre-live-output", default=str(DEFAULT_PRE_LIVE_OUTPUT))
    parser.add_argument("--candidate-output", default=str(DEFAULT_CANDIDATE_OUTPUT))
    args = parser.parse_args(argv)

    try:
        path_overrides = _parse_artifact_overrides(args.artifact)
    except ValueError as exc:
        parser.error(str(exc))

    summary = run_local_web_self_use_candidate_v2_gate(
        pre_live_evidence_output=Path(args.pre_live_evidence_output),
        pre_live_output=Path(args.pre_live_output),
        candidate_output=Path(args.candidate_output),
        path_overrides=path_overrides,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return (
        0
        if summary["evidence_status"] == "complete"
        and summary["pre_live_selected_option"] == "ready_for_human_limited_live_canary_decision"
        and summary["candidate_prepared"] is True
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
