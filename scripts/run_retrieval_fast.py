"""
Fast retrieval sanity wave using FTS-based chain_retrieval.

This script runs the same retrieval_sanity_cases.json test set but uses
the FTS-based fast path (chain_retrieval) instead of the slow
search_local_knowledge scoring pipeline.

Usage:
    python scripts/run_retrieval_fast.py
    python scripts/run_retrieval_fast.py --fixture tests/fixtures/retrieval_sanity_cases.json
    python scripts/run_retrieval_fast.py --output .logs/retrieval_fast_results.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.search.chain_retrieval import resolve_chain_item


def _load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Fixture must be a JSON array.")
    return payload


def _title_matches(expected_title: str, actual_title: str) -> bool:
    expected = str(expected_title or "").strip()
    actual = str(actual_title or "").strip()
    if not expected or not actual:
        return False
    # Allow substring match (expected in actual or actual in expected)
    return expected in actual or actual in expected or _fuzzy_match(expected, actual)


def _fuzzy_match(a: str, b: str) -> bool:
    """Simple fuzzy match: remove common suffixes/prefixes and brand prefixes."""
    # Remove temperature suffixes
    a_clean = a.replace("(熱)", "").replace("(冰)", "").replace("熱", "").replace("冰", "").strip()
    b_clean = b.replace("(熱)", "").replace("(冰)", "").replace("熱", "").replace("冰", "").strip()
    # Remove common brand prefixes before comparing
    for prefix in ["CITY ", "CITY PRIMA", "CITY PEARL", "金牌", "台酒", "台酒-"]:
        a_clean = a_clean.replace(prefix, "")
        b_clean = b_clean.replace(prefix, "")
    # Remove common bracketed suffixes like (貿易), (罐裝), (紙包), etc.
    import re
    a_clean = re.sub(r"\([^)]*\)", "", a_clean).strip()
    b_clean = re.sub(r"\([^)]*\)", "", b_clean).strip()
    return a_clean in b_clean or b_clean in a_clean


def _brand_matches(expected_brand: str, actual_brand: str) -> bool:
    expected = str(expected_brand or "").strip()
    actual = str(actual_brand or "").strip()
    if not expected:
        return not actual
    if not actual:
        return False
    # Exact or substring match
    if expected in actual or actual in expected:
        return True
    # Allow brand-prefix match: expected brand like "新東陽股份有限公司"
    # matches DB brand "新東陽股份有限公司" if the prefix (before 股份有限公司/有限/股份)
    # matches. Handles cases where DB items don't have the brand prefix in title.
    import re
    # Extract the meaningful brand prefix (everything before 公司/有限/股份 suffix)
    brand_prefix_pattern = r"^(.+?)(股份有限公司|有限公司|股份有限公司|股份|有限)$"
    exp_match = re.match(brand_prefix_pattern, expected)
    act_match = re.match(brand_prefix_pattern, actual)
    if exp_match and act_match:
        exp_prefix = exp_match.group(1)
        act_prefix = act_match.group(1)
        if exp_prefix and act_prefix and exp_prefix == act_prefix:
            return True
    return False


def _run_case(case: dict) -> dict:
    query = str(case["query"])
    t0 = time.time()
    docs = resolve_chain_item(query, limit=5)
    elapsed = time.time() - t0
    top = docs[0] if docs else {}
    expected_title = str(case.get("expected_title") or "").strip()
    expected_brand = str(case.get("expected_brand") or "").strip()
    title_ok = _title_matches(expected_title, str(top.get("title") or ""))
    brand_ok = _brand_matches(expected_brand, str(top.get("brand") or ""))
    exact_ok = top.get("evidence_role") == "exact_truth"
    confidence_ok = top.get("match_confidence") in {"high", "medium"}
    passed = bool(docs and title_ok and brand_ok and exact_ok and confidence_ok)
    return {
        "id": case["id"],
        "bucket": case["bucket"],
        "query": query,
        "expected_title": expected_title,
        "expected_brand": expected_brand,
        "passed": passed,
        "elapsed_ms": round(elapsed * 1000, 1),
        "checks": {
            "title_ok": title_ok,
            "brand_ok": brand_ok,
            "exact_ok": exact_ok,
            "confidence_ok": confidence_ok,
        },
        "top_hit": {
            "title": top.get("title"),
            "brand": top.get("brand"),
            "kcal": top.get("kcal"),
            "source_type": top.get("source_type"),
            "evidence_role": top.get("evidence_role"),
            "match_confidence": top.get("match_confidence"),
            "match_path": top.get("match_path"),
            "score": top.get("score"),
        },
        "top3": [
            {
                "title": doc.get("title"),
                "brand": doc.get("brand"),
                "kcal": doc.get("kcal"),
                "evidence_role": doc.get("evidence_role"),
                "match_confidence": doc.get("match_confidence"),
                "match_path": doc.get("match_path"),
                "score": doc.get("score"),
            }
            for doc in docs[:3]
        ],
    }


def _build_summary(results: list[dict]) -> dict:
    by_bucket: dict[str, dict[str, int]] = {}
    bucket_names = sorted({str(result["bucket"]) for result in results})
    for bucket in bucket_names:
        bucket_rows = [result for result in results if result["bucket"] == bucket]
        by_bucket[bucket] = {
            "total_cases": len(bucket_rows),
            "passed_cases": sum(1 for row in bucket_rows if row["passed"]),
            "failed_cases": sum(1 for row in bucket_rows if not row["passed"]),
        }
    total_time = sum(r["elapsed_ms"] for r in results)
    top_hit_confidence = collections.Counter(str(result["top_hit"].get("match_confidence") or "none") for result in results)
    return {
        "total_cases": len(results),
        "passed_cases": sum(1 for result in results if result["passed"]),
        "failed_cases": sum(1 for result in results if not result["passed"]),
        "by_bucket": by_bucket,
        "top_hit_confidence": dict(top_hit_confidence),
        "total_time_ms": round(total_time, 1),
        "avg_time_ms": round(total_time / len(results), 1) if results else 0,
    }


def _safeascii(s: str) -> str:
    if s is None:
        return "NONE"
    return str(s).encode("cp950", errors="replace").decode("cp950")

def _print_results(results: list[dict], summary: dict) -> None:
    print(f"\n{'='*60}")
    print(f"RETRIEVAL SANITY WAVE — FAST FTS PATH")
    print(f"{'='*60}")
    print(f"Total: {summary['total_cases']} cases | "
          f"PASS: {summary['passed_cases']} | "
          f"FAIL: {summary['failed_cases']} | "
          f"Time: {summary['total_time_ms']}ms total, {summary['avg_time_ms']}ms avg")
    print()
    for bucket, stats in summary["by_bucket"].items():
        pct = (stats["passed_cases"] / stats["total_cases"] * 100) if stats["total_cases"] > 0 else 0
        print(f"  [{bucket}] {stats['passed_cases']}/{stats['total_cases']} ({pct:.0f}%)")
    print()
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        hit = result["top_hit"]
        print(f"  [{status}] {result['id']} | {_safeascii(result['query'][:40])}")
        if not result["passed"]:
            checks = result["checks"]
            failed = [k for k, v in checks.items() if not v]
            print(f"       Expected: {_safeascii(result['expected_title'])} | {_safeascii(result['expected_brand'])}")
            print(f"       Got: {_safeascii(hit.get('title', 'NONE'))} | {_safeascii(hit.get('brand', 'NONE'))}")
            print(f"       Failed: {failed}")
        print(f"       kcal={hit.get('kcal', '?')} conf={hit.get('match_confidence')} time={result['elapsed_ms']}ms")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fast retrieval sanity checks using FTS.")
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "tests" / "fixtures" / "retrieval_sanity_cases.json"),
        help="Path to the retrieval sanity fixture JSON file.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / ".logs" / "retrieval_fast_results.json"),
        help="Path to write results JSON.",
    )
    parser.add_argument("--show-failed-only", action="store_true")
    args = parser.parse_args()

    fixture_path = Path(args.fixture).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cases = _load_cases(fixture_path)
    results = [_run_case(case) for case in cases]
    summary = _build_summary(results)
    payload = {"summary": summary, "cases": results}
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_results(results, summary)
    print(f"\nSaved detailed results to: {output_path}")
    return 0 if summary["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
