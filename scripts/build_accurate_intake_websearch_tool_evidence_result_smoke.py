from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.tool_evidence_result import (  # noqa: E402
    build_tool_evidence_result,
)
from app.nutrition.application.websearch_candidate_packet_smoke import (  # noqa: E402
    build_websearch_candidate_packet_smoke,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_tool_evidence_result_smoke.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch ToolEvidenceResult smoke artifact."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    packet_artifact = build_websearch_candidate_packet_smoke()
    packets = tuple(
        case["websearch_candidate_packet"]
        for case in packet_artifact["cases"]
        if isinstance(case.get("websearch_candidate_packet"), dict)
    )
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-websearch-candidate-packet-smoke",
        evidence_packets=packets,
        index_adapter={
            "adapter_kind": "web_search_candidate_adapter",
            "storage_backend": "external_search",
            "search_provider": "fixture_only",
            "index_policy_version": "websearch_candidate_packet_v1",
        },
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
            "live_websearch_used": False,
            "websearch_runtime_truth_allowed": False,
        },
    )
    artifact = {
        "artifact_type": "accurate_intake_websearch_tool_evidence_result_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "deterministic_websearch_tool_evidence_result_smoke",
        "runtime_truth_changed": False,
        "live_websearch_used": False,
        "live_provider_used": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "product_loop_integration_claimed": False,
        "websearch_runtime_truth_allowed": False,
        "adapter_diagnostics": {
            "adapter_kind": "web_search_candidate_adapter",
            "storage_backend": "external_search",
            "search_provider": "fixture_only",
            "packet_count": len(packets),
            "manager_visible": False,
        },
        "tool_evidence_result": tool_result,
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_runtime_truth_promotion",
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
                "live_websearch_used": artifact["live_websearch_used"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
