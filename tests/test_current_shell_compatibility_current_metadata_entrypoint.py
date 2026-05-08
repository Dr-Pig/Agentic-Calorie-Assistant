from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS,
)
from tests.test_current_shell_compatibility_current_metadata_freshness_pack import _evidence


def test_current_shell_current_metadata_entrypoint_writes_canonical_artifact(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import build_current_shell_compatibility_current_metadata_freshness_pack as module

    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    for group_id, payload in _evidence().items():
        (artifact_dir / f"{group_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    output_path = tmp_path / "current-metadata.json"
    args = ["--output", str(output_path)]
    for group_id in module.DEFAULT_EVIDENCE_PATHS:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])

    exit_code = module.main(args)
    printed = json.loads(capsys.readouterr().out)
    pack = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS
    assert pack["artifact_type"] == CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE
    assert pack["status"] == CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS
    assert "accurate_intake_pl_ce_current_metadata_freshness_pack" in pack[
        "legacy_artifact_type_aliases"
    ]
