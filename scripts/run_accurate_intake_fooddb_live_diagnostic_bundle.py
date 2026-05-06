from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_evidence_status_packet import (  # noqa: E402
    build_fooddb_evidence_status_packet,
)
from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (  # noqa: E402
    build_fooddb_grokfast_live_diagnostic_case_matrix_artifact,
)
from app.nutrition.application.fooddb_index_backend_parity import (  # noqa: E402
    build_fooddb_index_backend_parity,
)
from app.nutrition.application.fooddb_live_diagnostic_report import (  # noqa: E402
    build_fooddb_live_diagnostic_report,
)
from app.nutrition.application.fooddb_manager_contract_handoff import (  # noqa: E402
    build_fooddb_manager_contract_handoff,
)
from app.nutrition.application.fooddb_manager_packet_smoke import (  # noqa: E402
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_manager_contract_probe import (  # noqa: E402
    build_fooddb_manager_contract_probe,
)
from app.nutrition.application.fooddb_manager_contract_repair_pack import (  # noqa: E402
    build_fooddb_manager_contract_repair_pack,
)
from app.nutrition.application.grokfast_fooddb_diagnostic_preflight import (  # noqa: E402
    build_grokfast_fooddb_diagnostic_preflight,
)
from app.nutrition.application.retrieval_eval_wall import build_retrieval_eval_wall  # noqa: E402
from app.nutrition.infrastructure.local_food_evidence_index import (  # noqa: E402
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (  # noqa: E402
    SQLiteFtsFoodEvidenceIndex,
)
from app.nutrition.infrastructure.supabase_food_evidence_index import (  # noqa: E402
    SupabaseRowsFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.fooddb_live_bundle_artifacts import (  # noqa: E402
    build_fooddb_live_bundle_artifact_paths,
)
from scripts.run_accurate_intake_grokfast_fooddb_packet_smoke import (  # noqa: E402
    main as run_grokfast_fooddb_packet_smoke,
)


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_TFDA_SOURCE = ROOT / "app" / "knowledge" / "tfda_per100g_source_evidence_tw.json"
DEFAULT_EXACT_CARDS = ROOT / "app" / "knowledge" / "exact_item_cards_tw.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "accurate_intake_fooddb_live_diagnostic_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and run the bounded FoodDB/GrokFast packet live diagnostic bundle."
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--tfda-source", default=str(DEFAULT_TFDA_SOURCE))
    parser.add_argument("--exact-cards", default=str(DEFAULT_EXACT_CARDS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    paths = _artifact_paths(output_dir)
    source_payloads = _source_payloads(
        small_anchor_store=Path(args.small_anchor_store),
        tfda_source=Path(args.tfda_source),
        exact_cards=Path(args.exact_cards),
    )
    artifacts = _build_pre_provider_artifacts(
        paths=paths,
        source_payloads=source_payloads,
        small_anchor_store_path=Path(args.small_anchor_store),
    )
    diagnostic_exit = _run_packet_smoke(
        mode=args.mode,
        allow_live=args.allow_live,
        paths=paths,
    )
    diagnostic = read_json_artifact(paths["diagnostic"])
    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)
    write_json_artifact(paths["report"], report)
    contract_artifacts = _build_post_diagnostic_artifacts(
        paths=paths,
        source_payloads=source_payloads,
        diagnostic=diagnostic,
        report=report,
    )
    manifest = _build_manifest(
        mode=args.mode,
        allow_live=args.allow_live,
        paths=paths,
        diagnostic_exit=diagnostic_exit,
        diagnostic=diagnostic,
        report=report,
        preflight=artifacts["preflight"],
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
    return build_fooddb_live_bundle_artifact_paths(output_dir)


def _source_payloads(
    *,
    small_anchor_store: Path,
    tfda_source: Path,
    exact_cards: Path,
) -> dict[str, Any]:
    return {
        "small_anchor_payload": read_json_artifact(small_anchor_store),
        "tfda_source_payload": read_json_artifact(tfda_source),
        "exact_card_payload": read_json_artifact(exact_cards),
    }


def _build_pre_provider_artifacts(
    *,
    paths: dict[str, Path],
    source_payloads: dict[str, Any],
    small_anchor_store_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    local_index = LocalSmallAnchorFoodEvidenceIndex.from_path(
        small_anchor_store_path or DEFAULT_SMALL_ANCHOR_STORE
    )
    retrieval_records = local_index.load_records()
    retrieval_eval_wall = build_retrieval_eval_wall(retrieval_records=retrieval_records)
    manager_packet_smoke = build_fooddb_manager_packet_smoke(retrieval_records=retrieval_records)
    index_backend_parity = _build_index_backend_parity(
        local_index=local_index,
        sqlite_db_path=paths["sqlite_db"],
    )
    case_matrix = build_fooddb_grokfast_live_diagnostic_case_matrix_artifact()
    fooddb_status_packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=source_payloads["small_anchor_payload"],
        tfda_source_payload=source_payloads["tfda_source_payload"],
        exact_card_payload=source_payloads["exact_card_payload"],
    )
    preflight = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=retrieval_eval_wall,
        fooddb_status_packet=fooddb_status_packet,
        manager_packet_smoke_artifact=manager_packet_smoke,
        index_backend_parity_artifact=index_backend_parity,
        case_matrix_artifact=case_matrix,
    )

    artifacts = {
        "retrieval_eval_wall": retrieval_eval_wall,
        "fooddb_status_packet": fooddb_status_packet,
        "manager_packet_smoke": manager_packet_smoke,
        "index_backend_parity": index_backend_parity,
        "case_matrix": case_matrix,
        "preflight": preflight,
    }
    for key, artifact in artifacts.items():
        write_json_artifact(paths[key], artifact)
    return artifacts


def _build_index_backend_parity(
    *,
    local_index: LocalSmallAnchorFoodEvidenceIndex,
    sqlite_db_path: Path,
) -> dict[str, Any]:
    records = local_index.load_records()
    sqlite_index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(sqlite_db_path, records)
    supabase_index = SupabaseRowsFoodEvidenceIndex.from_rows(_supabase_rows_from_records(records))
    return build_fooddb_index_backend_parity(
        local_index=local_index,
        sqlite_index=sqlite_index,
        supabase_index=supabase_index,
    )


def _supabase_rows_from_records(records: object) -> tuple[dict[str, object], ...]:
    return tuple(asdict(record) for record in records)


def _run_packet_smoke(
    *,
    mode: str,
    allow_live: bool,
    paths: dict[str, Path],
) -> int:
    argv = [
        "--mode",
        mode,
        "--packet-smoke",
        str(paths["manager_packet_smoke"]),
        "--preflight-artifact",
        str(paths["preflight"]),
        "--output",
        str(paths["diagnostic"]),
    ]
    if allow_live:
        argv.append("--allow-live")
    return run_grokfast_fooddb_packet_smoke(argv)


def _build_post_diagnostic_artifacts(
    *,
    paths: dict[str, Path],
    source_payloads: dict[str, Any],
    diagnostic: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    probe = build_fooddb_manager_contract_probe(diagnostic_artifact=diagnostic)
    repair_pack = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic,
        contract_probe_artifact=probe,
    )
    handoff = build_fooddb_manager_contract_handoff(
        live_diagnostic_report=report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
    )
    post_contract_status = build_fooddb_evidence_status_packet(
        small_anchor_payload=source_payloads["small_anchor_payload"],
        tfda_source_payload=source_payloads["tfda_source_payload"],
        exact_card_payload=source_payloads["exact_card_payload"],
        contract_handoff_artifact=handoff,
    )
    artifacts = {
        "manager_contract_probe": probe,
        "manager_contract_repair_pack": repair_pack,
        "manager_contract_handoff": handoff,
        "fooddb_status_packet_post_contract": post_contract_status,
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
    preflight: dict[str, Any],
    contract_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    contract_probe = contract_artifacts["manager_contract_probe"]
    post_contract_status = contract_artifacts["fooddb_status_packet_post_contract"]
    post_contract_summary = (
        dict(post_contract_status.get("summary") or {})
        if isinstance(post_contract_status, dict)
        else {}
    )
    post_contract_integration = (
        dict(post_contract_status.get("integration_status") or {})
        if isinstance(post_contract_status, dict)
        else {}
    )
    return {
        "artifact_type": "accurate_intake_fooddb_live_diagnostic_bundle_manifest",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "live_diagnostic_orchestration_only",
        "claim_scope": "fooddb_packet_live_diagnostic_bundle_execution",
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
        "preflight_clear_to_run_live_diagnostic": preflight.get("clear_to_run_live_diagnostic") is True,
        "preflight_status": preflight.get("status"),
        "seam_status": report["seam_status"],
        "next_recommended_slice": report["next_recommended_slice"],
        "manager_contract_probe_detected_failure": contract_probe.get(
            "contract_failure_detected"
        )
        is True,
        "manager_contract_handoff_status": post_contract_summary.get(
            "manager_contract_handoff_status"
        ),
        "manager_contract_handoff_ready": post_contract_summary.get(
            "manager_contract_owner_handoff_ready"
        )
        is True,
        "manager_contract_selected_next_step": post_contract_integration.get(
            "manager_contract_selected_next_step"
        ),
        "artifacts": {
            key: str(path)
            for key, path in paths.items()
            if key in {
                "retrieval_eval_wall",
                "fooddb_status_packet",
                "manager_packet_smoke",
                "index_backend_parity",
                "case_matrix",
                "preflight",
                "diagnostic",
                "report",
                "manager_contract_probe",
                "manager_contract_repair_pack",
                "manager_contract_handoff",
                "fooddb_status_packet_post_contract",
            }
        },
        "non_claims": [
            "not_self_use_gate",
            "not_fooddb_truth_promotion",
            "not_websearch_tool_loop_gate",
            "not_runtime_mutation_gate",
            "not_product_readiness",
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
