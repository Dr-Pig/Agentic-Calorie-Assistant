"""
DB search測試集 runner.

Tests the 5 cases from "DB search測試集.txt" against the running canary server.
Each case has an expected behavior (action, should_search, should_use_db) and
expected kcal values.

Usage:
    python scripts/run_db_search_tests.py [--allow-search]
"""
from __future__ import annotations

import argparse
import json
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TESTSET_PATH = ROOT / "DB search測試集.txt"


@dataclass
class TestCase:
    id: str
    input: str
    expected_action: str
    should_search: bool
    should_use_db: bool
    target_kcal: dict[str, Any]


def _load_tests(path: Path) -> list[TestCase]:
    import re

    text = path.read_text(encoding="utf-8")
    # Extract each case block
    blocks = re.split(r"\n  - id:", text)
    cases = []
    for i, block in enumerate(blocks):
        if i == 0:
            block = block.strip()
            if not block:
                continue
        else:
            block = "  - id:" + block

        # Extract id
        id_m = re.search(r"- id:\s*(\S+)", block)
        if not id_m:
            continue
        case_id = id_m.group(1)

        # Extract input
        input_m = re.search(r"input:\s*[\"']?([^\"'\n]+)[\"']?\s*\n", block)
        if not input_m:
            input_m = re.search(r"input:\s*\"([^\"]+)\"", block)
        if not input_m:
            input_m = re.search(r"input:\s*'([^']+)'", block)
        input_text = input_m.group(1) if input_m else ""

        # Extract expected behavior fields
        action_m = re.search(r"action:\s*\"?(\w+)\"?\s*\n", block)
        should_search_m = re.search(r"should_search:\s*(true|false)", block)
        should_use_db_m = re.search(r"should_use_db:\s*(true|false)", block)

        expected_action = action_m.group(1) if action_m else ""
        should_search = should_search_m.group(1) == "true" if should_search_m else False
        should_use_db = should_use_db_m.group(1) == "true" if should_use_db_m else False

        # Extract kcal target
        exact_m = re.search(r"exact:\s*(\d+)", block)
        min_m = re.search(r"min:\s*(\d+)", block)
        max_m = re.search(r"max:\s*(\d+)", block)

        target_kcal = {}
        if exact_m:
            target_kcal["exact"] = int(exact_m.group(1))
        if min_m:
            target_kcal["min"] = int(min_m.group(1))
        if max_m:
            target_kcal["max"] = int(max_m.group(1))

        cases.append(TestCase(
            id=case_id,
            input=input_text,
            expected_action=expected_action,
            should_search=should_search,
            should_use_db=should_use_db,
            target_kcal=target_kcal,
        ))
    return cases


def _post(base_url: str, text: str, allow_search: bool) -> dict:
    body = json.dumps(
        {"text": text, "allow_search": allow_search},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/estimate",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _kcal_ok(result_kcal: float | None, target: dict) -> bool:
    if result_kcal is None:
        return False
    if "exact" in target:
        return abs(result_kcal - target["exact"]) <= 20
    if "min" in target and "max" in target:
        return target["min"] - 20 <= result_kcal <= target["max"] + 20
    if "min" in target:
        return result_kcal >= target["min"] - 20
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DB search test set against canary server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8032")
    parser.add_argument("--output", default=str(ROOT / ".logs" / "db_search_results.json"))
    args = parser.parse_args()

    cases = _load_tests(TESTSET_PATH)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for case in cases:
        print(f"\n[{case.id}] {case.input[:50]}")
        print(f"  Expected: action={case.expected_action}, search={case.should_search}, db={case.should_use_db}")
        try:
            payload = _post(args.base_url, case.input, allow_search=True)
            inner = payload.get("payload") or {}
            estimated = inner.get("estimated_kcal")
            source = inner.get("best_answer_source")
            mode = inner.get("best_estimate_mode")
            used_search = inner.get("used_search")
            retrieval_triggered = inner.get("retrieval_triggered")

            kcal_ok = _kcal_ok(estimated, case.target_kcal)

            print(f"  Got: kcal={estimated} (ok={kcal_ok}), source={source}, mode={mode}")
            print(f"  used_search={used_search}, retrieval_triggered={retrieval_triggered}")

            results.append({
                "id": case.id,
                "input": case.input,
                "estimated_kcal": estimated,
                "target_kcal": case.target_kcal,
                "kcal_ok": kcal_ok,
                "expected_action": case.expected_action,
                "got_action": mode,
                "source": source,
                "used_search": used_search,
                "retrieval_triggered": retrieval_triggered,
            })
        except urllib.error.HTTPError as exc:
            print(f"  HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:200]}")
            results.append({"id": case.id, "input": case.input, "error": f"HTTP {exc.code}"})
        except Exception as exc:
            print(f"  Error: {exc}")
            results.append({"id": case.id, "input": case.input, "error": str(exc)})

    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
