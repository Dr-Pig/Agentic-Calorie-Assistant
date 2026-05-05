from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_live_search_diagnostic_canary import (  # noqa: E402
    build_websearch_live_search_diagnostic_canary,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_live_search_diagnostic_canary.json"


class _FixtureSearchPort:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fixture", "configured": True}

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "max_results": max_results})
        return [
            {
                "title": "Test Brand Matcha Latte",
                "url": "https://brand.example/products/matcha-latte",
                "snippet": "deterministic official result",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "Test Brand",
                "serving_basis": "per_cup",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
                "raw_ref": "raw:search:fixture",
            }
        ]


class _FixtureExtractPort:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fixture", "configured": True}

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.calls.append({"urls": list(urls), "query": query})
        return [
            {
                "url": "https://brand.example/products/matcha-latte",
                "title": "Test Brand Matcha Latte",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "Test Brand",
                "raw_content": "400 kcal",
                "raw_ref": "raw:extract:fixture",
            }
        ]


async def _main_async(args: argparse.Namespace) -> int:
    artifact = await build_websearch_live_search_diagnostic_canary(
        preflight_artifact=(
            read_json_artifact(Path(args.preflight_artifact))
            if args.preflight_artifact
            else None
        ),
        live_permission_granted=args.live_permission_granted,
        search_port=_FixtureSearchPort(),
        extract_port=_FixtureExtractPort(),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "blockers": artifact["blockers"],
                "live_websearch_used": artifact["live_websearch_used"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run WebSearch live-search diagnostic canary harness with fixture ports."
    )
    parser.add_argument("--preflight-artifact")
    parser.add_argument("--live-permission-granted", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
