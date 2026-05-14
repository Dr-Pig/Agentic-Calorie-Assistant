from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


_CASE_HEADER_RE = re.compile(r"(?m)^(case_\d+)\s*$")
_SECTION_NAMES = ("input", "expected_behavior", "expected_evidence_outcome", "source_of_truth")


def parse_benchmark_text(raw: str) -> list[dict[str, Any]]:
    text = str(raw or "").replace("\ufeff", "")
    text = re.sub(r"(?<!\n)(case_\d+\s*\n)", r"\n\1", text)
    matches = list(_CASE_HEADER_RE.finditer(text))
    cases: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if not block:
            continue
        cases.append(_parse_case_block(block))
    return cases


def load_benchmark_cases(path: str | Path) -> list[dict[str, Any]]:
    fixture_path = Path(path)
    if fixture_path.suffix.lower() == ".json":
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Benchmark JSON fixture must be a list.")
        return data
    raw_text = fixture_path.read_text(encoding="utf-8")
    structured = _try_parse_structured_fixture(raw_text, fixture_path=fixture_path)
    if structured is not None:
        return structured
    return parse_benchmark_text(raw_text)


def _try_parse_structured_fixture(raw: str, *, fixture_path: Path | None = None) -> list[dict[str, Any]] | None:
    try:
        data = yaml.safe_load(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("items")
    if not isinstance(items, list):
        return None
    cases: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cases.append(_normalize_structured_case(item, fixture_path=fixture_path))
    return cases


def _parse_case_block(block: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in block.splitlines()]
    case_id = lines[0].strip()
    sections = _collect_sections(lines[1:])
    input_text = "\n".join(sections.get("input", [])).strip()
    expected_behavior = _parse_key_values(sections.get("expected_behavior", []))
    expected_evidence_outcome = _parse_key_values(sections.get("expected_evidence_outcome", []))
    source_of_truth_lines = [line for line in sections.get("source_of_truth", []) if line.strip()]
    source_of_truth = "\n".join(source_of_truth_lines).strip()
    parsed_truth = _extract_truth_hints(source_of_truth)
    return {
        "id": case_id,
        "input": input_text,
        "expected_behavior": expected_behavior,
        "expected_evidence_outcome": expected_evidence_outcome,
        "source_of_truth": source_of_truth,
        "parsed_truth": parsed_truth,
    }


def _normalize_structured_case(item: dict[str, Any], *, fixture_path: Path | None = None) -> dict[str, Any]:
    source_fixture = str(item.get("source_fixture") or "").strip()
    source_case_id = str(item.get("source_case_id") or item.get("id") or "").strip()
    resolved_input = item.get("input", "")
    source_expected_behavior = dict(item.get("expected_behavior") or {})
    source_expected_evidence_outcome = dict(item.get("expected_evidence_outcome") or {})
    source_source_of_truth = dict(item.get("source_of_truth") or {})

    if source_fixture and source_case_id:
        source_path = Path(source_fixture)
        if fixture_path is not None and not source_path.is_absolute():
            source_path = fixture_path.resolve().parents[2] / source_path
        if source_path.exists():
            source_cases = load_benchmark_cases(source_path)
            source_case = next((case for case in source_cases if str(case.get("id") or "") == source_case_id), None)
            if source_case:
                resolved_input = source_case.get("input", resolved_input)
                if not source_expected_behavior:
                    source_expected_behavior = dict(source_case.get("expected_behavior") or {})
                if not source_expected_evidence_outcome:
                    source_expected_evidence_outcome = dict(source_case.get("expected_evidence_outcome") or {})
                if not source_source_of_truth:
                    source_source_of_truth = dict(source_case.get("source_of_truth") or {})

    source_of_truth = source_source_of_truth
    target = dict(source_of_truth.get("target_calories_kcal") or {})
    parsed_truth = {
        "exact_kcal": target.get("exact"),
        "reference_kcal": target.get("center", target.get("exact")),
        "kcal_mentions": [
            float(value)
            for value in (
                target.get("exact"),
                target.get("min"),
                target.get("max"),
                target.get("center"),
            )
            if isinstance(value, (int, float))
        ],
        "macro_truth": None,
    }
    return {
        "id": item.get("id"),
        "input": resolved_input,
        "expected_behavior": source_expected_behavior,
        "expected_contract": dict(item.get("expected_contract") or {}),
        "expected_retrieval": dict(item.get("expected_retrieval") or {}),
        "expected_evidence_outcome": source_expected_evidence_outcome,
        "source_of_truth": source_of_truth,
        "parsed_truth": parsed_truth,
    }


def _collect_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        name = line.strip()
        if name in _SECTION_NAMES:
            current = name
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        sections[current].append(line)
    return sections


def _parse_key_values(lines: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if current_list_key and line.startswith("-"):
            data.setdefault(current_list_key, []).append(_parse_scalar(line[1:].strip()))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            data[key] = []
            current_list_key = key
            continue
        parsed = _parse_scalar(value)
        data[key] = parsed
    return data


def _parse_scalar(value: str) -> Any:
    if not value:
        return ""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _extract_truth_hints(source_of_truth: str) -> dict[str, Any]:
    text = str(source_of_truth or "")
    exact_kcal = _search_number(r"final answer.*?([0-9]+(?:\.[0-9]+)?)\s*kcal", text, flags=re.IGNORECASE | re.DOTALL)
    center_kcal = _search_number(r"\b(?:center|enter)\s+([0-9]+(?:\.[0-9]+)?)\b", text, flags=re.IGNORECASE)
    kcal_numbers = [float(item) for item in re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*kcal", text, flags=re.IGNORECASE)]
    macros = _extract_macro_truth(text)
    return {
        "exact_kcal": exact_kcal,
        "reference_kcal": center_kcal if center_kcal is not None else exact_kcal,
        "kcal_mentions": kcal_numbers,
        "macro_truth": macros,
    }


def _search_number(pattern: str, text: str, *, flags: int = 0) -> float | None:
    match = re.search(pattern, text, flags=flags)
    if not match:
        return None
    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return None


def _extract_macro_truth(text: str) -> dict[str, float] | None:
    # Prefer explicit P/F/C notation when present.
    pfc_match = re.search(
        r"\bP\s*([0-9]+(?:\.[0-9]+)?)g\s*/\s*F\s*([0-9]+(?:\.[0-9]+)?)g\s*/\s*C\s*([0-9]+(?:\.[0-9]+)?)g",
        text,
        flags=re.IGNORECASE,
    )
    if pfc_match:
        return {
            "protein_g": float(pfc_match.group(1)),
            "fat_g": float(pfc_match.group(2)),
            "carb_g": float(pfc_match.group(3)),
        }
    return None


def benchmark_fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "benchmark_test_set_v1.json"
