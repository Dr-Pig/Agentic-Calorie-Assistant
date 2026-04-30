from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx

from .tavily_profile_policy import (
    TavilyRuntimeSearchProfile,
    TavilySelectedExtractProfile,
    runtime_search_profile,
    selected_extract_profile,
)


PLACEHOLDER_API_KEYS = {"", "replace-me"}


class TavilyAdapter:
    def __init__(
        self,
        *,
        search_profile: TavilyRuntimeSearchProfile | None = None,
        extract_profile: TavilySelectedExtractProfile | None = None,
    ) -> None:
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.timeout_seconds = min(int(os.getenv("TAVILY_TIMEOUT_SECONDS", "15")), 15)
        self._search_profile = search_profile or runtime_search_profile()
        self._extract_profile = extract_profile or selected_extract_profile()

    def readiness(self) -> dict[str, Any]:
        return {"provider": "tavily", "configured": self._is_configured(), "timeout_seconds": self.timeout_seconds}

    async def search_candidates(
        self,
        query: str,
        *,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        if not self._is_configured():
            raise RuntimeError("Tavily is not configured.")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": self._search_profile.search_depth,
                    "max_results": max_results,
                    "include_raw_content": self._search_profile.include_raw_content,
                },
            )
            response.raise_for_status()
            data = response.json()
        results = []
        for item in data.get("results", []):
            url = item.get("url", "")
            domain = urlparse(url).netloc.lower()
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": url,
                    "snippet": item.get("content", "")[:400],
                    "score": item.get("score"),
                    "domain": domain,
                    "officialness": self._infer_officialness(domain=domain, title=item.get("title", ""), snippet=item.get("content", "")),
                    "raw_content": item.get("raw_content", "") if self._search_profile.include_raw_content else "",
                }
            )
        return results

    async def extract_structured_page_data(
        self,
        *,
        urls: list[str],
        query: str,
    ) -> list[dict[str, Any]]:
        if not self._is_configured():
            raise RuntimeError("Tavily is not configured.")
        if not urls:
            return []
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://api.tavily.com/extract",
                json={
                    "api_key": self.api_key,
                    "urls": urls,
                    "query": query,
                    "chunks_per_source": max(1, min(self._extract_profile.chunks_per_source, 5)),
                    "extract_depth": self._extract_profile.extract_depth,
                },
            )
            response.raise_for_status()
            data = response.json()
        extracted: list[dict[str, Any]] = []
        for item in data.get("results", []) or data.get("data", []) or []:
            url = str(item.get("url") or "")
            title = str(item.get("title") or item.get("metadata", {}).get("title") or "")
            raw_content = str(item.get("raw_content") or item.get("content") or "")
            domain = urlparse(url).netloc.lower()
            detected_brand = self._detect_brand(text=" ".join([title, raw_content, domain]))
            extracted.append(
                {
                    "url": url,
                    "title": title,
                    "domain": domain,
                    "source_type": self._classify_source_type(domain=domain, raw_content=raw_content),
                    "officialness": self._infer_officialness(domain=domain, title=title, snippet=raw_content),
                    "serving_basis": self._infer_serving_basis(raw_content),
                    "identity_confidence": "medium" if detected_brand else "low",
                    "applicability_confidence": "medium",
                    "customization_slots_present": self._detect_customization_slots(raw_content),
                    "brand_detected": detected_brand,
                    "channel_detected": self._detect_channel(text=" ".join([title, raw_content, domain])),
                    "nutrition_fields_present": self._detect_nutrition_fields(raw_content),
                    "evidence_tier_candidate": "near-exact" if detected_brand else "generic",
                    "applicability_notes": self._build_applicability_notes(raw_content),
                    "raw_content": raw_content[:3000],
                }
            )
        return extracted

    async def search(self, query: str, *, max_results: int = 5, limit: int | None = None) -> list[dict[str, Any]]:
        result_limit = int(limit or max_results)
        candidates = await self.search_candidates(query, max_results=result_limit)
        urls = [str(item.get("url") or "") for item in candidates if str(item.get("url") or "").strip()]
        extracted_by_url: dict[str, dict[str, Any]] = {}
        if urls:
            try:
                extracted = await self.extract_structured_page_data(urls=urls[: min(len(urls), 5)], query=query)
                extracted_by_url = {str(item.get("url") or ""): item for item in extracted}
            except Exception:
                extracted_by_url = {}
        merged: list[dict[str, Any]] = []
        for item in candidates:
            extracted = extracted_by_url.get(str(item.get("url") or ""), {})
            merged.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "score": item.get("score"),
                    "officialness": extracted.get("officialness") or item.get("officialness", "unknown"),
                    "source_type": extracted.get("source_type") or "search_candidate",
                    "serving_basis": extracted.get("serving_basis") or "",
                    "identity_confidence": extracted.get("identity_confidence") or "low",
                    "applicability_confidence": extracted.get("applicability_confidence") or "low",
                    "customization_slots_present": extracted.get("customization_slots_present") or [],
                    "brand_detected": extracted.get("brand_detected") or "",
                    "channel_detected": extracted.get("channel_detected") or "",
                    "nutrition_fields_present": extracted.get("nutrition_fields_present") or [],
                    "evidence_tier_candidate": extracted.get("evidence_tier_candidate") or "generic",
                    "applicability_notes": extracted.get("applicability_notes") or "",
                    "raw_content": extracted.get("raw_content") or "",
                }
            )
        return merged

    def _is_configured(self) -> bool:
        return self.api_key.strip() not in PLACEHOLDER_API_KEYS

    @staticmethod
    def _infer_officialness(*, domain: str, title: str, snippet: str) -> str:
        haystack = " ".join([domain, title, snippet]).lower()
        if any(token in haystack for token in ("official", "menu", "nutrition", ".gov", ".edu")):
            return "official"
        if any(token in domain for token in ("7-11", "family", "mcdonald", "starbucks", "coco", "kfc")):
            return "official"
        return "unknown"

    @staticmethod
    def _classify_source_type(*, domain: str, raw_content: str) -> str:
        haystack = f"{domain} {raw_content}".lower()
        if any(token in haystack for token in ("official", "menu", "nutrition", "product")):
            return "official" if ".gov" not in haystack else "official"
        if any(token in haystack for token in ("forum", "reddit", "ptt", "dcard")):
            return "forum"
        if any(token in haystack for token in ("blog", "medium", "wordpress")):
            return "nutrition_blog"
        return "aggregator"

    @staticmethod
    def _infer_serving_basis(raw_content: str) -> str:
        lowered = raw_content.lower()
        if "per 100g" in lowered or "每100g" in raw_content:
            return "per_100g"
        if "每份" in raw_content or "per serving" in lowered:
            return "per_serving"
        if "每杯" in raw_content or "per cup" in lowered:
            return "per_cup"
        if "套餐" in raw_content or "combo" in lowered:
            return "combo"
        return "unknown"

    @staticmethod
    def _detect_customization_slots(raw_content: str) -> list[str]:
        lowered = raw_content.lower()
        slots: list[str] = []
        if any(token in lowered for token in ("large", "medium", "small")) or any(token in raw_content for token in ("大杯", "中杯", "小杯")):
            slots.append("size")
        if any(token in lowered for token in ("sugar", "sweet")) or any(token in raw_content for token in ("全糖", "半糖", "無糖", "微糖")):
            slots.append("sugar")
        if any(token in lowered for token in ("ice",)) or any(token in raw_content for token in ("去冰", "少冰", "正常冰")):
            slots.append("ice")
        if any(token in lowered for token in ("topping", "pearls", "boba")) or "珍珠" in raw_content:
            slots.append("toppings")
        return slots

    @staticmethod
    def _detect_brand(text: str) -> str:
        lowered = text.lower()
        for token, label in (
            ("7-11", "7-11"),
            ("familymart", "familymart"),
            ("mcdonald", "mcdonalds"),
            ("starbucks", "星巴克"),
            ("coco", "coco"),
            ("50嵐", "50lan"),
            ("八方雲集", "bafang"),
        ):
            if token in lowered or token in text:
                return label
        return ""

    @staticmethod
    def _detect_channel(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("bottle", "bottled", "can", "packaged", "7-11", "familymart")):
            return "packaged_retail"
        if any(token in lowered for token in ("menu", "tea", "shop", "restaurant")) or any(token in text for token in ("手搖", "餐廳", "門市")):
            return "handmade_foodservice"
        return "unknown"

    @staticmethod
    def _detect_nutrition_fields(raw_content: str) -> list[str]:
        lowered = raw_content.lower()
        fields: list[str] = []
        if "kcal" in lowered or "calorie" in lowered or "熱量" in raw_content:
            fields.append("kcal")
        if "protein" in lowered or "蛋白質" in raw_content:
            fields.append("protein")
        if "carb" in lowered or "碳水" in raw_content:
            fields.append("carbs")
        if "fat" in lowered or "脂肪" in raw_content:
            fields.append("fat")
        return fields

    @staticmethod
    def _build_applicability_notes(raw_content: str) -> str:
        notes: list[str] = []
        if "每100g" in raw_content or "per 100g" in raw_content.lower():
            notes.append("requires portion conversion")
        if any(token in raw_content for token in ("全糖", "半糖", "無糖", "去冰", "少冰")):
            notes.append("contains drink customization cues")
        return "; ".join(notes)
