from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"


@dataclass(frozen=True)
class Rule:
    path_prefix: str
    forbidden_prefixes: tuple[str, ...] = ()
    forbidden_exact: tuple[str, ...] = ()
    label: str = ""
    severity: str = "error"


RULES: tuple[Rule, ...] = (
    Rule(
        path_prefix="app/runtime/",
        forbidden_prefixes=("app.intake.domain", "app.nutrition.domain", "app.budget.domain", "app.archive"),
        label="runtime-boundary",
        severity="error",
    ),
    Rule(
        path_prefix="app/shared/",
        forbidden_prefixes=("app.intake", "app.nutrition", "app.budget", "app.body", "app.archive"),
        label="shared-neutrality",
        severity="error",
    ),
    Rule(
        path_prefix="app/providers/",
        forbidden_prefixes=("app.intake", "app.budget", "app.body", "app.archive"),
        label="provider-domain-ownership",
        severity="error",
    ),
    Rule(
        path_prefix="app/intake/",
        forbidden_prefixes=("app.archive",),
        label="intake-mainline-archive-separation",
        severity="error",
    ),
    Rule(
        path_prefix="app/body/",
        forbidden_prefixes=("app.archive",),
        label="body-mainline-archive-separation",
        severity="error",
    ),
    Rule(
        path_prefix="app/budget/",
        forbidden_prefixes=("app.archive",),
        label="budget-mainline-archive-separation",
        severity="error",
    ),
    Rule(
        path_prefix="app/nutrition/",
        forbidden_prefixes=("app.archive",),
        label="nutrition-mainline-archive-separation",
        severity="error",
    ),
    Rule(
        path_prefix="app/providers/",
        forbidden_prefixes=("fastapi", "sqlalchemy"),
        label="provider-adapter-boundary",
        severity="warning",
    ),
)


@dataclass(frozen=True)
class Finding:
    severity: str
    path: str
    line: int
    import_name: str
    message: str


def module_name_for_path(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    return ".".join(rel.parts)


def resolve_import(node: ast.AST, current_module: str) -> list[tuple[int, str]]:
    if isinstance(node, ast.Import):
        results: list[tuple[int, str]] = []
        for alias in node.names:
            results.append((node.lineno, alias.name))
        return results

    if not isinstance(node, ast.ImportFrom):
        return []

    module = node.module or ""
    if node.level == 0:
        return [(node.lineno, module)] if module else []

    current_parts = current_module.split(".")
    if node.level > len(current_parts):
        base_parts: list[str] = []
    else:
        base_parts = current_parts[: -node.level]

    if module:
        resolved = ".".join([*base_parts, module]) if base_parts else module
        return [(node.lineno, resolved)]

    return []


def matches_rule(path_str: str, rule: Rule) -> bool:
    return path_str.replace("\\", "/").startswith(rule.path_prefix)


def import_blocked(import_name: str, rule: Rule) -> bool:
    if import_name in rule.forbidden_exact:
        return True
    return any(import_name == prefix or import_name.startswith(prefix + ".") for prefix in rule.forbidden_prefixes)


def collect_findings(py_file: Path) -> list[Finding]:
    rel_path = py_file.relative_to(REPO_ROOT).as_posix()
    module_name = module_name_for_path(py_file)
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_file))
    findings: list[Finding] = []

    active_rules = [rule for rule in RULES if matches_rule(rel_path, rule)]
    if not active_rules:
        return findings

    for node in ast.walk(tree):
        for lineno, import_name in resolve_import(node, module_name):
            for rule in active_rules:
                if import_blocked(import_name, rule):
                    findings.append(
                        Finding(
                            severity=rule.severity,
                            path=rel_path,
                            line=lineno,
                            import_name=import_name,
                            message=f"{rule.label} must not import {import_name}",
                        )
                    )
    return findings


def main() -> int:
    py_files = sorted(path for path in APP_ROOT.rglob("*.py") if "__pycache__" not in path.parts)
    findings: list[Finding] = []
    for py_file in py_files:
        findings.extend(collect_findings(py_file))

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    if findings:
        print("Layer integrity report")
        print()
        for finding in findings:
            print(f"[{finding.severity.upper()}] {finding.path}:{finding.line} {finding.message}")
        print()

    if warnings:
        print("Advisory:")
        print("- provider adapter warnings are advisory unless they cross into domain/runtime ownership")
        print("- route ownership belongs in domain interface modules; persistence ownership belongs in domain infrastructure modules")
        print()

    if errors:
        print("Layer integrity check failed.")
        return 1

    print("Layer integrity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
