import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _load_cases(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Input file must be a JSON array.")
    cases: list[str] = []
    for item in data:
        if not isinstance(item, str):
            raise ValueError("Every case must be a string.")
        cases.append(item)
    return cases


def _post_case(base_url: str, text: str, allow_search: bool) -> dict:
    body = json.dumps(
        {"text": text, "allow_search": allow_search},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/estimate",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a batch of text-meal cases through the local canary server using UTF-8 JSON input."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a UTF-8 JSON file containing an array of case strings.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8032",
        help="Base URL of the local canary server.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the full JSON results. Defaults to .logs/<input-stem>_results.json.",
    )
    parser.add_argument(
        "--allow-search",
        action="store_true",
        help="Enable search when calling /estimate.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    cases = _load_cases(input_path)

    output_path = (
        Path(args.output).resolve()
        if args.output
        else Path(".logs", f"{input_path.stem}_results.json").resolve()
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for text in cases:
        payload = _post_case(args.base_url, text, args.allow_search)
        inner = payload.get("payload", {})
        results.append(
            {
                "input": text,
                "request_id": payload.get("request_id"),
                "reply_text": inner.get("reply_text"),
                "estimated_kcal": inner.get("estimated_kcal"),
                "components": inner.get("components"),
                "best_answer_source": inner.get("best_answer_source"),
                "best_estimate_mode": inner.get("best_estimate_mode"),
                "failed_layer": inner.get("failed_layer"),
                "primary_failure_reason": inner.get("primary_failure_reason"),
                "north_star_evaluation": inner.get("north_star_evaluation"),
                "trace_contract": inner.get("trace_contract"),
                "retrieval_triggered": inner.get("retrieval_triggered"),
                "used_search": inner.get("used_search"),
                "search_quality": inner.get("search_quality"),
                "risk_flags": (inner.get("risk_packet") or {}).get("risk_flags"),
                "quality_signals": inner.get("quality_signals"),
                "debug_steps": inner.get("debug_steps"),
                "raw_payload": inner,
            }
        )
        print(f"[ok] {text} -> {inner.get('estimated_kcal')} kcal")

    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved results to: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"HTTP error {exc.code}: {exc.read().decode('utf-8', errors='replace')}\n")
        raise
    except urllib.error.URLError as exc:
        sys.stderr.write(f"Request failed: {exc}\n")
        raise
