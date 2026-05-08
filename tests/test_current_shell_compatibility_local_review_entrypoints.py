from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_CLAIM_SCOPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
)
from tests.test_current_shell_compatibility_local_review_decision_pack import _evidence
from tests.test_current_shell_compatibility_local_review_gate_runner import _artifact_args, _write


def test_current_shell_local_review_decision_pack_emits_canonical_ids() -> None:
    from scripts.build_current_shell_compatibility_local_review_decision_pack import (
        REQUIRED_CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE,
        build_current_shell_compatibility_local_review_decision_pack,
    )

    pack = build_current_shell_compatibility_local_review_decision_pack(_evidence())

    assert pack["artifact_type"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE
    assert pack["claim_scope"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_CLAIM_SCOPE
    assert pack["status"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS
    assert pack["required_evidence"] == list(
        REQUIRED_CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE
    )
    assert "accurate_intake_pl_ce_local_review_decision_pack" in pack[
        "legacy_artifact_type_aliases"
    ]
    assert "ready_for_human_pl_ce_review" in pack["legacy_status_aliases"]


def test_current_shell_local_review_gate_writes_canonical_manifest_and_pack(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.build_current_shell_compatibility_local_review_decision_pack import (
        REQUIRED_CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE,
    )
    from scripts.run_current_shell_compatibility_local_review_gate import main

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _evidence().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    manifest_output = tmp_path / "current_shell_manifest.json"
    decision_output = tmp_path / "current_shell_decision.json"

    exit_code = main(
        [
            "--manifest-output",
            str(manifest_output),
            "--decision-output",
            str(decision_output),
            *_artifact_args(
                artifact_dir, REQUIRED_CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE
            ),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    manifest = json.loads(manifest_output.read_text(encoding="utf-8"))
    decision = json.loads(decision_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["decision_status"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS
    assert manifest["_manifest_metadata"]["artifact_type"].startswith(
        "accurate_intake_current_shell_compatibility_"
    )
    assert decision["artifact_type"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE
