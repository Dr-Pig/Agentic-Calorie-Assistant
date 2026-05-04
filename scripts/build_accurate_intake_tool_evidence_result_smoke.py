from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_manager_packet_smoke import (  # noqa: E402
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.tool_evidence_result import (  # noqa: E402
    build_tool_evidence_result,
)
from app.nutrition.infrastructure.local_food_evidence_index import (  # noqa: E402
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_tool_evidence_result_smoke.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic FoodDB ToolEvidenceResult smoke artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    index = LocalSmallAnchorFoodEvidenceIndex.from_path(Path(args.small_anchor_store))
    retrieval_records = index.load_records()
    packet_artifact = build_fooddb_manager_packet_smoke(retrieval_records=retrieval_records)
    packets = tuple(
        case["manager_evidence_packet"]
        for case in packet_artifact["cases"]
        if isinstance(case.get("manager_evidence_packet"), dict)
    )
    tool_result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id="tool-fooddb-manager-packet-smoke",
        evidence_packets=packets,
        index_adapter={
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
            "record_count": len(retrieval_records),
            "index_policy_version": "food_evidence_index_port_v1",
        },
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
        },
    )
    artifact = {
        "artifact_type": "accurate_intake_tool_evidence_result_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "deterministic_tool_evidence_result_smoke",
        "runtime_truth_changed": False,
        "live_provider_used": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "product_loop_integration_claimed": False,
        "adapter_diagnostics": {
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
            "record_count": len(retrieval_records),
            "index_policy_version": "food_evidence_index_port_v1",
            "manager_visible": False,
        },
        "tool_evidence_result": tool_result,
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_live_provider_call",
            "no_manager_context_change",
            "no_runtime_packetizer_contract_change",
            "no_product_loop_integration",
            "no_readiness_claim",
        ],
    }
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": artifact["claim_scope"],
                "packet_count": tool_result["trace"]["packet_count"],
                "compact_packet_pass_count": tool_result["trace"]["compact_packet_pass_count"],
                "live_provider_used": artifact["live_provider_used"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
