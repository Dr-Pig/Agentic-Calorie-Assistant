from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
ARCHIVE_IMPORT_PREFIX = "app." + "archive"
CONCRETE_PROVIDER_PREFIX = "app.providers"
TAVILY_ADAPTER_PREFIX = "app.providers.tavily_adapter"
PROVIDER_RUNTIME_COMPOSITION_ROOT = "app/runtime/interface/provider_runtime.py"
TAVILY_INFRA_PREFIX = "app/providers/"
ACTIVE_DOMAIN_PREFIXES = (
    "app.intake",
    "app.nutrition",
    "app.budget",
    "app.body",
    "app.knowledge",
    "app.memory",
    "app.recommendation",
    "app.rescue",
)


@dataclass(frozen=True)
class Rule:
    importer_prefix: str
    forbidden_import_prefixes: tuple[str, ...]
    label: str


RUNTIME_RULES: tuple[Rule, ...] = (
    Rule(
        importer_prefix="app/runtime/",
        forbidden_import_prefixes=(
            "app.intake.domain",
            "app.nutrition.domain",
            "app.budget.domain",
            "app.knowledge",
            "app.memory",
            "app.recommendation",
            "app.rescue",
            ARCHIVE_IMPORT_PREFIX,
        ),
        label="runtime-must-not-own-domain-semantics",
    ),
    Rule(
        importer_prefix="app/shared/",
        forbidden_import_prefixes=(*ACTIVE_DOMAIN_PREFIXES, ARCHIVE_IMPORT_PREFIX),
        label="shared-must-remain-neutral",
    ),
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    import_name: str
    message: str


def module_name_for_path(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    return ".".join(rel.parts)


def resolve_import(node: ast.AST, current_module: str) -> list[tuple[int, str]]:
    if isinstance(node, ast.Import):
        return [(node.lineno, alias.name) for alias in node.names]

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
    return path_str.replace("\\", "/").startswith(rule.importer_prefix)


def import_blocked(import_name: str, rule: Rule) -> bool:
    return any(
        import_name == prefix or import_name.startswith(prefix + ".")
        for prefix in rule.forbidden_import_prefixes
    )


def collect_findings(py_file: Path) -> list[Finding]:
    rel_path = py_file.relative_to(REPO_ROOT).as_posix()
    active_rules = [rule for rule in RUNTIME_RULES if matches_rule(rel_path, rule)]

    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_file))
    current_module = module_name_for_path(py_file)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        for lineno, import_name in resolve_import(node, current_module):
            for rule in active_rules:
                if import_blocked(import_name, rule):
                    findings.append(
                        Finding(
                            path=rel_path,
                            line=lineno,
                            import_name=import_name,
                            message=f"{rule.label} violation: {rel_path} must not import {import_name}",
                        )
                    )
            if _concrete_provider_import_blocked(rel_path, import_name):
                findings.append(
                    Finding(
                        path=rel_path,
                        line=lineno,
                        import_name=import_name,
                        message=f"provider-inversion violation: {rel_path} must not import concrete provider adapter {import_name}",
                    )
                )
            if _tavily_adapter_import_blocked(rel_path, import_name):
                findings.append(
                    Finding(
                        path=rel_path,
                        line=lineno,
                        import_name=import_name,
                        message=f"tavily-inversion violation: {rel_path} must not import concrete Tavily adapter {import_name}",
                    )
                )
    return findings


def _concrete_provider_import_blocked(rel_path: str, import_name: str) -> bool:
    if not (import_name == CONCRETE_PROVIDER_PREFIX or import_name.startswith(CONCRETE_PROVIDER_PREFIX + ".")):
        return False
    if rel_path.startswith("app/providers/"):
        return False
    return rel_path != PROVIDER_RUNTIME_COMPOSITION_ROOT


def _tavily_adapter_import_blocked(rel_path: str, import_name: str) -> bool:
    if not (import_name == TAVILY_ADAPTER_PREFIX or import_name.startswith(TAVILY_ADAPTER_PREFIX + ".")):
        return False
    return not rel_path.startswith(TAVILY_INFRA_PREFIX)


def main() -> int:
    py_files = sorted(path for path in APP_ROOT.rglob("*.py") if "__pycache__" not in path.parts)
    findings: list[Finding] = []
    for py_file in py_files:
        findings.extend(collect_findings(py_file))

    if findings:
        print("Runtime boundary check failed.")
        for finding in findings:
            print(f"- {finding.path}:{finding.line} {finding.message}")
        return 1

    print("Runtime boundary check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
