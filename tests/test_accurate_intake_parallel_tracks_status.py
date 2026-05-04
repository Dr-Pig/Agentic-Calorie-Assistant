from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "quality" / "ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md"


def _status_text() -> str:
    return STATUS_PATH.read_text(encoding="utf-8-sig")


def test_parallel_tracks_status_pack_exists_with_required_sections() -> None:
    text = _status_text()

    required_sections = [
        "# Accurate Intake MVP Parallel Tracks Status",
        "## Current MVP Goal",
        "## Track Ownership",
        "### Track FDB: FoodDB / Evidence Pipeline",
        "### Track PL: Product Loop / Browser Shell",
        "### Track CE: Context Engineering",
        "## Shared Interface Contracts",
        "## Shared Contract Change Gate",
        "## Artifact Compatibility Gate",
        "## Current Active Branches",
        "## Cross-Track Blockers",
        "## Sync Protocol",
        "## Standard Slice Report",
        "## Startup Message For Parallel Agents",
    ]
    for section in required_sections:
        assert section in text


def test_parallel_tracks_status_pack_lists_human_gated_contracts() -> None:
    text = _status_text()

    gated_contracts = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord schema",
        "PacketReadyAnchor schema",
        "ManagerContextPacket schema",
        "packetizer accepted/rejected evidence format",
        "estimate output format",
        "basket semantics",
        "Food Evidence promotion policy",
    ]
    for contract in gated_contracts:
        assert contract in text


def test_parallel_tracks_status_pack_enforces_track_owned_status_blocks() -> None:
    text = _status_text()

    for track in ("FDB", "PL", "CE"):
        assert f"### {track} Status" in text
        block = text.split(f"### {track} Status", 1)[1].split("### ", 1)[0]
        for field in (
            "track:",
            "branch:",
            "current_slice:",
            "status:",
            "expected_output:",
            "shared_contract_changed:",
            "blocked_by:",
        ):
            assert field in block


def test_parallel_tracks_status_pack_keeps_non_claims_visible() -> None:
    text = _status_text()

    for non_claim in (
        "no Kimi",
        "no GrokFast",
        "no live provider",
        "no LLM extraction",
        "no production DB",
        "no long-term memory",
        "no proactive, rescue, or recommendation behavior",
        "no product, web, private self-use, or production readiness claim",
    ):
        assert non_claim in text


def test_parallel_tracks_status_pack_contains_mandatory_report_shape() -> None:
    text = _status_text()

    report_fields = [
        "track:",
        "slice_id:",
        "branch:",
        "changed_files:",
        "shared_contract_changed: true | false",
        "artifact_outputs:",
        "dependencies_for_other_tracks:",
        "blocked_by:",
        "tests:",
        "non_claims:",
        "pushed_sha:",
    ]
    for field in report_fields:
        assert field in text
