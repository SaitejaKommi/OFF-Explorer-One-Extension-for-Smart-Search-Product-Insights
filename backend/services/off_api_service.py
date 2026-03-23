"""
off_api_service.py
------------------
Fallback product fetcher for Open Food Facts public API.
Used when a product is not found in local DuckDB/parquet data.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class OFFApiService:
    """Small client for OFF product endpoints (no API key required)."""

    _BASE_URLS = (
        "https://ca.openfoodfacts.org",
    )

    def fetch_product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        safe_barcode = "".join(c for c in barcode if c.isdigit())
        if not safe_barcode:
            return None

        payload = self._fetch_raw_payload(safe_barcode)
        if not payload:
            return None

        return self._normalize_product(payload, safe_barcode)

    def _fetch_raw_payload(self, barcode: str) -> dict[str, Any] | None:
        timeout = settings.off_api_timeout
        for base_url in self._BASE_URLS:
            url = f"{base_url}/api/v2/product/{barcode}.json"
            try:
                resp = httpx.get(url, timeout=timeout)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json()
                if int(data.get("status", 0)) == 1 and data.get("product"):
                    return data["product"]
            except Exception as exc:
                logger.warning("OFF API lookup failed for %s (%s): %s", barcode, base_url, exc)
        return None

    def _normalize_product(self, product: dict[str, Any], barcode: str) -> dict[str, Any]:
        nutriments = product.get("nutriments") or {}
        categories_tags = self._as_csv_tags(product.get("categories_tags"))
        labels_tags = self._as_csv_tags(product.get("labels_tags"))
        countries_tags = self._as_csv_tags(product.get("countries_tags"))
        allergens_tags = self._as_csv_tags(product.get("allergens_tags"))

        return {
            "code": str(product.get("code") or barcode),
            "product_name": str(product.get("product_name") or "Unknown product"),
            "categories_tags": categories_tags,
            "labels_tags": labels_tags,
            "nutriscore_grade": product.get("nutriscore_grade"),
            "nova_group": self._as_int(product.get("nova_group")),
            "energy_kcal_100g": self._as_float(
                nutriments.get("energy-kcal_100g")
                if nutriments.get("energy-kcal_100g") is not None
                else nutriments.get("energy-kcal_value")
            ),
            "proteins_100g": self._as_float(nutriments.get("proteins_100g")),
            "fat_100g": self._as_float(nutriments.get("fat_100g")),
            "saturated_fat_100g": self._as_float(nutriments.get("saturated-fat_100g")),
            "sugars_100g": self._as_float(nutriments.get("sugars_100g")),
            "fiber_100g": self._as_float(nutriments.get("fiber_100g")),
            "salt_100g": self._as_float(nutriments.get("salt_100g")),
            "carbohydrates_100g": self._as_float(nutriments.get("carbohydrates_100g")),
            "countries_tags": countries_tags,
            "allergens_tags": allergens_tags,
        }

    @staticmethod
    def _as_csv_tags(value: Any) -> str:
        if isinstance(value, list):
            return ",".join(str(v) for v in value)
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


off_api_service = OFFApiService()
