from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Issue:
    code: str
    message: str = ""
    shard_id: str = ""
    record_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "shard_id": self.shard_id,
            "record_id": self.record_id,
        }


def issue_dicts(issues: Iterable[Issue]) -> list[dict[str, str]]:
    return [issue.to_dict() for issue in issues]


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def create_run_layout(
    root: Path,
    *,
    run_id: str,
    manifest: Mapping[str, Any],
    prompts: Mapping[str, str],
    schema_signature: str = "",
) -> Path:
    run_dir = Path(root) / run_id
    (run_dir / "child_outputs").mkdir(parents=True, exist_ok=True)
    (run_dir / "prompts").mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "manifest.json", {**dict(manifest), "schema_signature": schema_signature})
    write_json(run_dir / "notes.json", {"run_id": run_id, "notes": []})
    for shard_id, prompt in prompts.items():
        (run_dir / "prompts" / f"{shard_id}.md").write_text(prompt, encoding="utf-8")
    (run_dir / "dry_run.ps1").write_text("Write-Output 'dry run'\n", encoding="utf-8")
    (run_dir / "run_all.ps1").write_text("Write-Output 'run all'\n", encoding="utf-8")
    return run_dir


def child_output_paths(run_dir: Path) -> list[Path]:
    return sorted((Path(run_dir) / "child_outputs").glob("*.json"))
