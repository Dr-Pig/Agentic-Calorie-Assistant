from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_CLAIM_SCOPE,
    CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS,
)
from tests.test_accurate_intake_pl_ce_metadata_freshness_pack import _fresh_evidence, _write


def test_current_shell_metadata_freshness_report_emits_canonical_ids(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import build_current_shell_compatibility_metadata_freshness_pack as module

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _fresh_evidence().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    output_path = tmp_path / "metadata-freshness.json"
    args = ["--output", str(output_path), "--max-age-hours", "24"]
    for group_id in module.DEFAULT_EVIDENCE_PATHS:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])

    exit_code = module.main(args)
    printed = json.loads(capsys.readouterr().out)
    pack = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS
    assert pack["artifact_type"] == CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_ARTIFACT_TYPE
    assert pack["claim_scope"] == CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_CLAIM_SCOPE
    assert pack["status"] == CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS
    assert "accurate_intake_pl_ce_metadata_freshness_pack" in pack[
        "legacy_artifact_type_aliases"
    ]
    assert "metadata_freshness_ready_for_pl_ce_local_review" in pack[
        "legacy_status_aliases"
    ]
