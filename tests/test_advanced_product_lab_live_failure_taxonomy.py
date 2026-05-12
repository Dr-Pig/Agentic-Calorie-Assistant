from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/build_advanced_product_lab_live_failure_taxonomy.py"


def test_live_failure_taxonomy_classifies_provider_claim_boundary_failure() -> None:
    from app.advanced_shadow_lab.product_lab_live_failure_taxonomy import (
        build_live_failure_taxonomy_report,
    )

    report = build_live_failure_taxonomy_report(
        [_artifact(blockers=["provider_review.durable_product_memory_written"])]
    )

    assert report["artifact_type"] == "advanced_product_lab_live_failure_taxonomy"
    assert report["status"] == "pass"
    assert report["failure_count"] == 1
    assert report["failure_records"][0] == {
        "source_artifact_type": "advanced_product_lab_integrated_live_e2e",
        "source_status": "blocked",
        "blocker": "provider_review.durable_product_memory_written",
        "failure_family": "activation_boundary_claim_drift",
        "attribution_owner": "live_provider_review_contract",
        "next_safe_slice": "clarify_activation_boundary_payload_or_add_holdout",
        "semantic_hardening_allowed": False,
    }
    assert report["summary"]["activation_boundary_claim_drift"] == 1
    assert report["live_failures_create_attribution_only"] is True
    assert report["semantic_hardening_allowed"] is False
    assert report["product_truth_changed"] is False


def test_live_failure_taxonomy_blocks_unknown_failure_family() -> None:
    from app.advanced_shadow_lab.product_lab_live_failure_taxonomy import (
        build_live_failure_taxonomy_report,
    )

    report = build_live_failure_taxonomy_report(
        [_artifact(blockers=["provider_review.unexpected_new_blocker"])]
    )

    assert report["status"] == "blocked"
    assert report["unclassified_failure_count"] == 1
    assert report["blockers"] == [
        "unclassified_failure:provider_review.unexpected_new_blocker"
    ]
    assert report["semantic_hardening_allowed"] is False


def test_live_failure_taxonomy_tracks_passed_milestones_without_failures() -> None:
    from app.advanced_shadow_lab.product_lab_live_failure_taxonomy import (
        build_live_failure_taxonomy_report,
    )

    report = build_live_failure_taxonomy_report(
        [
            _artifact(
                status="pass",
                blockers=[],
                milestone_status="satisfied_live_grokfast",
            )
        ]
    )

    assert report["status"] == "pass"
    assert report["failure_count"] == 0
    assert report["milestone_statuses"] == {
        "advanced_product_lab_integrated_live_e2e": "satisfied_live_grokfast"
    }
    assert report["next_allowed_slices"] == ["live_edd_decision_pack"]


def test_live_failure_taxonomy_cli_roundtrip(tmp_path: Path) -> None:
    artifact_path = tmp_path / "integrated-live-e2e.json"
    output = tmp_path / "failure-taxonomy.json"
    write_json_artifact(
        artifact_path,
        _artifact(blockers=["provider_review.scheduler_delivery_allowed"]),
    )

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--artifact-json",
            str(artifact_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_report = json.loads(result.stdout)
    file_report = read_json_artifact(output)
    assert stdout_report == file_report
    assert file_report["status"] == "pass"
    assert file_report["summary"]["delivery_claim_drift"] == 1


def _artifact(
    *,
    status: str = "blocked",
    blockers: list[str],
    milestone_status: str = "blocked_contract_or_guard",
) -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_integrated_live_e2e",
        "status": status,
        "diagnostic_evidence_class": "live_grokfast",
        "live_milestone_status": milestone_status,
        "blockers": blockers,
        "provider_error": {},
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
    }
