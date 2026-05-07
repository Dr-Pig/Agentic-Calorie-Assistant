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

from app.nutrition.application.exact_card_candidate_promotion_readiness import (  # noqa: E402
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_status_packet import (  # noqa: E402
    build_exact_evidence_lane_status_packet,
)
from app.nutrition.application.websearch_candidate_lane_status_packet import (  # noqa: E402
    build_websearch_candidate_lane_status_packet,
)
from app.nutrition.application.websearch_evidence_status_packet import (  # noqa: E402
    build_websearch_evidence_status_packet,
)
from app.nutrition.application.websearch_candidate_pipeline_narrow_expansion import (  # noqa: E402
    build_websearch_candidate_pipeline_narrow_expansion_artifact,
)
from app.nutrition.application.exact_evidence_lane_policy import (  # noqa: E402
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.websearch_exact_candidate_chain_status import (  # noqa: E402
    build_websearch_exact_candidate_chain_status,
)
from app.nutrition.application.websearch_exact_candidate_review_packet import (  # noqa: E402
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (  # noqa: E402
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_grokfast_live_diagnostic_case_matrix import (  # noqa: E402
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)
from app.nutrition.application.websearch_live_diagnostic_report import (  # noqa: E402
    build_websearch_live_diagnostic_report,
)
from app.nutrition.application.websearch_live_extract_preflight import (  # noqa: E402
    build_websearch_live_extract_preflight,
)
from app.nutrition.application.websearch_live_runner_readiness_packet import (  # noqa: E402
    build_websearch_live_runner_readiness_packet,
)
from app.nutrition.application.websearch_manager_contract_handoff import (  # noqa: E402
    build_websearch_manager_contract_handoff,
)
from app.nutrition.application.websearch_manager_contract_probe import (  # noqa: E402
    build_websearch_manager_contract_probe,
)
from app.nutrition.application.websearch_manager_contract_repair_pack import (  # noqa: E402
    build_websearch_manager_contract_repair_pack,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (  # noqa: E402
    build_websearch_selected_extract_packet_smoke,
)
from app.nutrition.application.websearch_status_packet_inspection import (  # noqa: E402
    build_websearch_status_packet_inspection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import (  # noqa: E402
    main as run_grokfast_websearch_packet_smoke,
)
from scripts.websearch_live_bundle_artifacts import (  # noqa: E402
    build_websearch_live_bundle_artifact_paths,
)


DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "accurate_intake_websearch_live_diagnostic_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and run the bounded WebSearch/GrokFast packet live diagnostic bundle."
        )
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--fooddb-status-packet-artifact", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    paths = _artifact_paths(output_dir)
    artifacts = _build_pre_provider_artifacts(paths)
    diagnostic_exit = _run_packet_smoke(
        mode=args.mode,
        allow_live=args.allow_live,
        paths=paths,
    )
    diagnostic = read_json_artifact(paths["diagnostic"])
    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=artifacts["preflight"],
    )
    write_json_artifact(paths["report"], report)
    contract_artifacts = _build_post_diagnostic_artifacts(
        paths=paths,
        diagnostic=diagnostic,
        report=report,
        preflight=artifacts["preflight"],
        chain_status=artifacts["chain_status"],
        readiness=artifacts["readiness"],
        fooddb_status_packet=_read_optional_artifact(args.fooddb_status_packet_artifact),
    )
    manifest = _build_manifest(
        mode=args.mode,
        allow_live=args.allow_live,
        paths=paths,
        diagnostic_exit=diagnostic_exit,
        diagnostic=diagnostic,
        report=report,
        contract_artifacts=contract_artifacts,
    )
    write_json_artifact(paths["manifest"], manifest)
    print(
        json.dumps(
            {
                "artifact": str(paths["manifest"]),
                "bundle_status": manifest["bundle_status"],
                "mode": args.mode,
                "live_provider_used": diagnostic.get("live_provider_used"),
                "seam_status": report["seam_status"],
                "next_recommended_slice": report["next_recommended_slice"],
            },
            ensure_ascii=False,
        )
    )
    return diagnostic_exit


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    return build_websearch_live_bundle_artifact_paths(output_dir)


def _build_pre_provider_artifacts(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    case_matrix = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    candidate_pipeline_narrow_expansion = (
        build_websearch_candidate_pipeline_narrow_expansion_artifact(
            live_case_matrix_artifact=case_matrix
        )
    )
    exact_readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected_extract = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=exact_readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected_extract
    )
    review_packet = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
        case_matrix_artifact=case_matrix,
    )
    chain_status = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact=selected_extract,
        extract_result_artifact=extract_result,
        exact_review_packet_artifact=review_packet,
        preflight_artifact=preflight,
    )
    readiness = build_websearch_live_runner_readiness_packet(
        review_packet_artifact=review_packet,
        preflight_artifact=preflight,
        exact_candidate_chain_status_artifact=chain_status,
    )
    artifacts = {
        "case_matrix": case_matrix,
        "candidate_pipeline_narrow_expansion": candidate_pipeline_narrow_expansion,
        "selected_extract": selected_extract,
        "extract_result": extract_result,
        "review_packet": review_packet,
        "preflight": preflight,
        "chain_status": chain_status,
        "readiness": readiness,
    }
    for key, artifact in artifacts.items():
        write_json_artifact(paths[key], artifact)
    return artifacts


def _run_packet_smoke(
    *,
    mode: str,
    allow_live: bool,
    paths: dict[str, Path],
) -> int:
    argv = [
        "--mode",
        mode,
        "--review-packet-artifact",
        str(paths["review_packet"]),
        "--preflight-artifact",
        str(paths["preflight"]),
        "--exact-candidate-chain-status-artifact",
        str(paths["chain_status"]),
        "--live-runner-readiness-artifact",
        str(paths["readiness"]),
        "--output",
        str(paths["diagnostic"]),
    ]
    if allow_live:
        argv.append("--allow-live")
    return run_grokfast_websearch_packet_smoke(argv)


def _build_post_diagnostic_artifacts(
    *,
    paths: dict[str, Path],
    diagnostic: dict[str, Any],
    report: dict[str, Any],
    preflight: dict[str, Any],
    chain_status: dict[str, Any],
    readiness: dict[str, Any],
    fooddb_status_packet: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    probe = build_websearch_manager_contract_probe(diagnostic_artifact=diagnostic)
    repair_pack = build_websearch_manager_contract_repair_pack(
        contract_probe_artifact=probe
    )
    handoff = build_websearch_manager_contract_handoff(
        live_diagnostic_report=report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )
    candidate_lane_status = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=fooddb_status_packet,
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )
    exact_lane_status = build_exact_evidence_lane_status_packet(
        websearch_status_packet=candidate_lane_status,
        exact_candidate_chain_status_packet=chain_status,
    )
    websearch_status_packet = build_websearch_evidence_status_packet(
        candidate_lane_status_packet=candidate_lane_status,
        exact_lane_status_packet=exact_lane_status,
        manager_contract_handoff_artifact=handoff,
        candidate_pipeline_narrow_expansion_artifact=read_json_artifact(
            paths["candidate_pipeline_narrow_expansion"]
        ),
    )
    status_packet_inspection = build_websearch_status_packet_inspection(
        websearch_status_packet=websearch_status_packet,
        router_readiness_artifact=None,
        exact_candidate_chain_status_artifact=chain_status,
        live_runner_readiness_artifact=readiness,
    )
    artifacts = {
        "manager_contract_probe": probe,
        "manager_contract_repair_pack": repair_pack,
        "manager_contract_handoff": handoff,
        "websearch_evidence_status_packet": websearch_status_packet,
        "websearch_status_packet_inspection": status_packet_inspection,
    }
    for key, artifact in artifacts.items():
        write_json_artifact(paths[key], artifact)
    return artifacts


def _build_manifest(
    *,
    mode: str,
    allow_live: bool,
    paths: dict[str, Path],
    diagnostic_exit: int,
    diagnostic: dict[str, Any],
    report: dict[str, Any],
    contract_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    handoff = contract_artifacts["manager_contract_handoff"]
    evidence_status_packet = contract_artifacts["websearch_evidence_status_packet"]
    status_packet_inspection = contract_artifacts["websearch_status_packet_inspection"]
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_bundle_manifest",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "live_diagnostic_orchestration_only",
        "claim_scope": "websearch_packet_live_diagnostic_bundle_execution",
        "bundle_status": "pass" if diagnostic_exit == 0 else "blocked_or_failed",
        "mode": mode,
        "allow_live": allow_live,
        "diagnostic_exit_code": diagnostic_exit,
        "live_provider_used": diagnostic.get("live_provider_used") is True,
        "live_websearch_used": diagnostic.get("live_websearch_used") is True,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "seam_status": report["seam_status"],
        "next_recommended_slice": _inspection_next_slice(
            status_packet_inspection,
            fallback=_status_packet_next_slice(evidence_status_packet),
        ),
        "manager_contract_handoff_status": handoff.get("status"),
        "manager_contract_handoff_ready": handoff.get("handoff_ready") is True,
        "manager_contract_selected_next_step": handoff.get("selected_next_step"),
        "artifacts": {key: str(path) for key, path in paths.items() if key != "manifest"},
        "non_claims": [
            "not_self_use_gate",
            "not_websearch_tool_loop_gate",
            "not_exact_card_truth_gate",
            "not_runtime_mutation_gate",
            "not_product_readiness",
        ],
    }


def _read_optional_artifact(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json_artifact(path)


def _status_packet_next_slice(evidence_status_packet: dict[str, Any]) -> str:
    next_required_slices = list(evidence_status_packet.get("next_required_slices") or [])
    return str(next_required_slices[0] or "").strip() if next_required_slices else "inspect_websearch_status_packet"


def _inspection_next_slice(inspection_artifact: dict[str, Any], *, fallback: str) -> str:
    summary = dict(inspection_artifact.get("summary") or {})
    next_safe_slice = str(summary.get("next_safe_slice") or "").strip()
    return next_safe_slice or fallback


if __name__ == "__main__":
    raise SystemExit(main())
