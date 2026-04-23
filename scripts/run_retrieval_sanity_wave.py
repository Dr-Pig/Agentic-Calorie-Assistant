from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.agent.local_knowledge_selector import search_local_knowledge


def _load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Fixture must be a JSON array.")
    return payload


def _title_matches(expected_title: str, actual_title: str) -> bool:
    expected = str(expected_title or "").strip()
    actual = str(actual_title or "").strip()
    return bool(expected and actual and (expected in actual or actual in expected))


def _brand_matches(expected_brand: str, actual_brand: str) -> bool:
    expected = str(expected_brand or "").strip()
    actual = str(actual_brand or "").strip()
    if not expected:
        return not actual
    return bool(actual and (expected in actual or actual in expected))


def _run_case(case: dict) -> dict:
    query = str(case["query"])
    docs = search_local_knowledge(query, user_input=query, limit=5)
    top = docs[0] if docs else {}
    title_ok = _title_matches(str(case.get("expected_title") or ""), str(top.get("title") or ""))
    brand_ok = _brand_matches(str(case.get("expected_brand") or ""), str(top.get("brand") or ""))
    exact_ok = top.get("evidence_role") == "exact_truth"
    confidence_ok = top.get("match_confidence") in {"high", "medium"}
    passed = bool(docs and title_ok and brand_ok and exact_ok and confidence_ok)
    return {
        "id": case["id"],
        "bucket": case["bucket"],
        "query": query,
        "expected_title": case.get("expected_title"),
        "expected_brand": case.get("expected_brand"),
        "passed": passed,
        "checks": {
            "title_ok": title_ok,
            "brand_ok": brand_ok,
            "exact_ok": exact_ok,
            "confidence_ok": confidence_ok,
        },
        "top_hit": {
            "title": top.get("title"),
            "brand": top.get("brand"),
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
                "source_type": doc.get("source_type"),
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

    top_hit_confidence = collections.Counter(str(result["top_hit"].get("match_confidence") or "none") for result in results)
    return {
        "total_cases": len(results),
        "passed_cases": sum(1 for result in results if result["passed"]),
        "failed_cases": sum(1 for result in results if not result["passed"]),
        "by_bucket": by_bucket,
        "top_hit_confidence": dict(top_hit_confidence),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run retrieval sanity checks against local exact-card ranking.")
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "tests" / "fixtures" / "retrieval_sanity_cases.json"),
        help="Path to the retrieval sanity fixture JSON file.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / ".logs" / "retrieval_sanity_wave_extended_20260331.json"),
        help="Path to write the sanity wave results JSON file.",
    )
    args = parser.parse_args()

    fixture_path = Path(args.fixture).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cases = _load_cases(fixture_path)
    results = [_run_case(case) for case in cases]
    summary = _build_summary(results)
    payload = {"summary": summary, "cases": results}
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved retrieval sanity wave to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
