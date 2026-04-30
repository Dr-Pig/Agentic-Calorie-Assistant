from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = REPO_ROOT / "config" / "architecture_dependency_debt_baseline.json"
DEFAULT_BASELINE_REF = "origin/main"
BUSINESS_DOMAIN_PREFIXES = (
    "app.intake",
    "app.nutrition",
    "app.budget",
    "app.body",
    "app.memory",
    "app.recommendation",
    "app.rescue",
    "app." + "archive",
)
CENTRAL_DATA_MODULES = ("app.models", "app.database")
RUNTIME_SHARED_PREFIXES = ("app/runtime/", "app/shared/")
BUSINESS_DOMAIN_PATH_PREFIXES = (
    "app/intake/",
    "app/nutrition/",
    "app/budget/",
    "app/body/",
    "app/memory/",
    "app/recommendation/",
    "app/rescue/",
)


@dataclass(frozen=True, order=True)
class Finding:
    category: str
    path: str
    line: int
    import_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "path": self.path,
            "line": self.line,
            "import_name": self.import_name,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Finding":
        return cls(
            category=str(payload["category"]),
            path=str(payload["path"]),
            line=int(payload["line"]),
            import_name=str(payload["import_name"]),
        )


def audit_architecture_dependency_debt(
    *,
    repo_root: Path = REPO_ROOT,
    baseline_path: Path = DEFAULT_BASELINE,
    baseline_ref: str = DEFAULT_BASELINE_REF,
) -> dict[str, Any]:
    findings = set(scan_findings(repo_root))
    allowed_findings = set(_load_baseline(baseline_path, repo_root=repo_root, baseline_ref=baseline_ref))
    new_findings = sorted(findings - allowed_findings)
    removed_findings = sorted(allowed_findings - findings)

    return {
        "artifact_type": "architecture_dependency_debt_audit",
        "passed": not new_findings,
        "finding_count": len(findings),
        "known_finding_count": len(findings & allowed_findings),
        "new_finding_count": len(new_findings),
        "removed_finding_count": len(removed_findings),
        "baseline_path": str(baseline_path),
        "baseline_ref": baseline_ref if not baseline_path.exists() else None,
        "new_findings": [finding.to_dict() for finding in new_findings],
        "removed_findings": [finding.to_dict() for finding in removed_findings],
    }


def scan_findings(repo_root: Path) -> list[Finding]:
    app_root = repo_root / "app"
    if not app_root.exists():
        return []
    findings: list[Finding] = []
    for py_file in sorted(app_root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(repo_root).as_posix()
        findings.extend(scan_source_findings(rel_path, py_file.read_text(encoding="utf-8")))
    return sorted(findings)


def scan_source_findings(rel_path: str, source: str) -> list[Finding]:
    module_name = rel_path.removesuffix(".py").replace("/", ".")
    tree = ast.parse(source, filename=rel_path)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        for line, import_name in resolve_import(node, current_module=module_name):
            category = classify_import(rel_path, import_name)
            if category is None:
                continue
            findings.append(
                Finding(
                    category=category,
                    path=rel_path,
                    line=line,
                    import_name=import_name,
                )
            )
    return findings


def module_name_for_path(path: Path, *, repo_root: Path = REPO_ROOT) -> str:
    rel = path.relative_to(repo_root).with_suffix("")
    return ".".join(rel.parts)


def resolve_import(node: ast.AST, *, current_module: str) -> list[tuple[int, str]]:
    if isinstance(node, ast.Import):
        return [(node.lineno, alias.name) for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []

    module = node.module or ""
    if node.level == 0:
        return [(node.lineno, module)] if module else []

    parts = current_module.split(".")
    base_parts = parts[: -node.level] if node.level <= len(parts) else []
    resolved = ".".join([*base_parts, module]) if module else ".".join(base_parts)
    return [(node.lineno, resolved)] if resolved else []


def classify_import(rel_path: str, import_name: str) -> str | None:
    if rel_path.startswith(RUNTIME_SHARED_PREFIXES):
        if _matches_any(import_name, (*BUSINESS_DOMAIN_PREFIXES, *CENTRAL_DATA_MODULES)):
            return "runtime_shared_to_business_domain"

    active_domain = _domain_prefix_for_path(rel_path)
    if active_domain is not None:
        if _matches_any(import_name, CENTRAL_DATA_MODULES):
            return "business_domain_to_central_data_module"
        imported_domain = _domain_prefix_for_import(import_name)
        if imported_domain is not None and imported_domain != active_domain:
            return "business_domain_to_other_business_domain"

    return None


def _domain_prefix_for_path(rel_path: str) -> str | None:
    for prefix in BUSINESS_DOMAIN_PATH_PREFIXES:
        if rel_path.startswith(prefix):
            return prefix.strip("/").replace("/", ".")
    return None


def _domain_prefix_for_import(import_name: str) -> str | None:
    for prefix in BUSINESS_DOMAIN_PREFIXES:
        if import_name == prefix or import_name.startswith(prefix + "."):
            return prefix
    return None


def _matches_any(import_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(import_name == prefix or import_name.startswith(prefix + ".") for prefix in prefixes)


def _load_baseline(path: Path, *, repo_root: Path, baseline_ref: str) -> list[Finding]:
    if not path.exists():
        return _load_git_baseline(repo_root=repo_root, baseline_ref=baseline_ref)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Finding.from_dict(item) for item in payload.get("allowed_findings", [])]


def _load_git_baseline(*, repo_root: Path, baseline_ref: str) -> list[Finding]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", baseline_ref, "--", "app"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []

    findings: list[Finding] = []
    for rel_path in sorted(line.strip() for line in result.stdout.splitlines() if line.strip().endswith(".py")):
        show = subprocess.run(
            ["git", "show", f"{baseline_ref}:{rel_path}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if show.returncode != 0:
            continue
        findings.extend(scan_source_findings(rel_path, show.stdout))
    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail when architecture dependency debt grows beyond baseline.")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--baseline-ref", default=DEFAULT_BASELINE_REF)
    args = parser.parse_args()

    report = audit_architecture_dependency_debt(baseline_path=Path(args.baseline), baseline_ref=args.baseline_ref)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
