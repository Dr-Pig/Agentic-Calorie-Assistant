from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.exact_card_candidate_promotion_readiness import (  # noqa: E402
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (  # noqa: E402
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.grokfast_websearch_packet_diagnostic import (  # noqa: E402
    build_fixture_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
)
from app.nutrition.application.websearch_exact_candidate_review_packet import (  # noqa: E402
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (  # noqa: E402
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (  # noqa: E402
    build_websearch_selected_extract_packet_smoke,
)
from scripts.build_accurate_intake_rt9c_websearch_candidate_live_probe_gate import (  # noqa: E402
    build_rt9c_websearch_candidate_live_probe_gate,
)


def _build_live_websearch_packet_smoke_artifact() -> dict:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected
    )
    review_packet = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )
    return build_grokfast_websearch_packet_diagnostic(
        review_packet_artifact=review_packet,
        manager_outputs=build_fixture_manager_outputs(review_packet_artifact=review_packet),
        live_provider_used=True,
    )


def test_rt9c_websearch_candidate_live_probe_gate_passes_for_live_packet_smoke_shape() -> None:
    source = _build_live_websearch_packet_smoke_artifact()

    artifact = build_rt9c_websearch_candidate_live_probe_gate(
        live_packet_artifact=source,
    )

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt9c_websearch_candidate_live_probe"
    assert artifact["summary"]["required_provider_profile_id"] == (
        "builderspace-grok-4-fast-websearch-packet-smoke"
    )
    assert artifact["summary"]["non_claim_flags_preserved"] is True


def test_rt9c_websearch_candidate_live_probe_gate_blocks_non_live_artifact() -> None:
    source = _build_live_websearch_packet_smoke_artifact()
    source["live_provider_used"] = False

    artifact = build_rt9c_websearch_candidate_live_probe_gate(
        live_packet_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "live_provider_not_used" in artifact["blockers"]


def test_rt9c_websearch_candidate_live_probe_gate_blocks_truth_promotion_signal() -> None:
    source = _build_live_websearch_packet_smoke_artifact()
    source["cases"][0]["final_action"] = "commit"

    artifact = build_rt9c_websearch_candidate_live_probe_gate(
        live_packet_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert any(
        blocker.startswith("case_final_action_not_candidate_review_safe:")
        for blocker in artifact["blockers"]
    )


def test_rt9c_websearch_candidate_live_probe_gate_cli_writes_json(tmp_path: Path) -> None:
    source = _build_live_websearch_packet_smoke_artifact()
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "accurate_intake_rt9c_websearch_candidate_live_probe_gate.json"

    from scripts.build_accurate_intake_rt9c_websearch_candidate_live_probe_gate import main

    exit_code = main(
        [
            "--source-artifact",
            str(source_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt9c_websearch_candidate_live_probe_gate"
    assert payload["status"] == "pass"
