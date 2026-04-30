from __future__ import annotations

import json
from pathlib import Path

from scripts.build_wave1_phase_b2_live_search_seam_decision_pack import (
    DECISION_OPTION_IDS,
    build_live_search_seam_decision_pack,
    write_live_search_seam_decision_pack,
)


def _canary_artifact(*, live_invoked: bool = True, case_blockers: bool = True) -> dict[str, object]:
    cases: list[dict[str, object]] = []
    if live_invoked:
        cases = [
            {
                "case_id": "starbucks_latte_positive",
                "verdict_category": "trace_canary_blocker" if case_blockers else "diagnostic_observation",
                "failure_family": "extract_mismatch" if case_blockers else None,
                "runtime_web_activation_recommended": False,
                "trace": {
                    "failure_reason": "no_accepted_web_extract_packet" if case_blockers else None,
                    "accepted_extract_packet_id": None if case_blockers else "pkt_web_extract_exact",
                    "synthesis_evidence_refs": [] if case_blockers else ["pkt_web_extract_exact"],
                    "rejected_web_candidates_used_as_evidence": False,
                    "truth_boundary": {
                        "trace_only": True,
                        "web_candidate_truth_authority": False,
                        "accepted_extract_packet_truth_authority": False,
                        "requires_packetizer_hard_recheck_consumption": True,
                        "requires_synthesis_verifier": True,
                        "runtime_web_activation_recommended": False,
                    },
                },
            }
        ]
    return {
        "artifact_type": "b2_exact_brand_tavily_live_trace_canary",
        "provider_mode": "live" if live_invoked else "not_invoked",
        "live_invoked": live_invoked,
        "failure_family": None if live_invoked else "environment_or_provider_blocker",
        "readiness_claimed": False,
        "trace_only": True,
        "runtime_web_activation_recommended": False,
        "decision_pack_options": list(DECISION_OPTION_IDS),
        "cases": cases,
    }


def test_decision_pack_includes_no_live_search_seam_and_does_not_auto_activate() -> None:
    pack = build_live_search_seam_decision_pack(_canary_artifact(case_blockers=True))

    assert pack["artifact_type"] == "wave1_phase_b2_live_search_seam_decision_pack"
    assert pack["decision_options_ordered"] == list(DECISION_OPTION_IDS)
    assert any(option["option_id"] == "no_live_search_seam" for option in pack["decision_options"])
    assert pack["runtime_web_activation_approved"] is False
    assert pack["runtime_web_activation_recommended"] is False
    assert pack["selected_option"] is None
    assert pack["requires_human_decision"] is True
    assert pack["recommended_safe_default"] == "no_live_search_seam"
    assert pack["evidence_summary"]["failure_families"] == ["extract_mismatch"]


def test_clean_trace_canary_still_requires_separate_runtime_web_seam_slice() -> None:
    pack = build_live_search_seam_decision_pack(_canary_artifact(case_blockers=False))

    narrow_option = next(option for option in pack["decision_options"] if option["option_id"] == "narrow_exact_brand_web_seam")
    assert pack["runtime_web_activation_approved"] is False
    assert pack["selected_option"] is None
    assert pack["requires_human_decision"] is True
    assert narrow_option["requires_new_slice"] is True
    assert narrow_option["auto_activation_allowed"] is False
    assert "runtime_web_activation" in narrow_option["blocked_claims"]


def test_decision_pack_blocks_overclaiming_input_artifact() -> None:
    artifact = _canary_artifact(case_blockers=False)
    artifact["runtime_web_activation_recommended"] = True

    pack = build_live_search_seam_decision_pack(artifact)

    assert pack["input_integrity"]["passed"] is False
    assert "input_runtime_web_activation_recommended" in pack["input_integrity"]["blockers"]
    assert pack["runtime_web_activation_approved"] is False


def test_missing_tavily_token_artifact_keeps_web_deferred() -> None:
    pack = build_live_search_seam_decision_pack(_canary_artifact(live_invoked=False))

    assert pack["evidence_summary"]["live_invoked"] is False
    assert pack["evidence_summary"]["failure_families"] == ["environment_or_provider_blocker"]
    assert pack["recommended_safe_default"] == "no_live_search_seam"
    assert pack["runtime_web_activation_approved"] is False


def test_decision_pack_writer_creates_artifact_without_claiming_readiness(tmp_path: Path) -> None:
    source = tmp_path / "tavily.json"
    source.write_text(json.dumps(_canary_artifact(case_blockers=True), ensure_ascii=False), encoding="utf-8")

    output = write_live_search_seam_decision_pack(tavily_artifact_path=source, output_dir=tmp_path)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "wave1_phase_b2_live_search_seam_decision_pack.json"
    assert data["readiness_claimed"] is False
    assert data["readiness_claim"]["forbidden_claims"] == [
        "runtime_web_activation",
        "product_ready",
        "user_facing_ready",
        "mutation_ready",
    ]
