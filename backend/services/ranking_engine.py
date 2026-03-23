"""
ranking_engine.py
-----------------
Scores and ranks product results based on nutrient profile and search intent.

Default nutrient weights (can be tuned):
  sugars   0.30
  fat      0.20
  salt     0.15
  protein  0.20
  fiber    0.15

A lower nutrient score = healthier product = higher rank.
"""
from __future__ import annotations

from typing import Any

from backend.models.schemas import ParsedIntent, ProductResult

# Default weights for ranking (also used for alternatives)
DEFAULT_WEIGHTS: dict[str, float] = {
    "sugars_100g": 0.30,
    "fat_100g": 0.20,
    "salt_100g": 0.15,
    "proteins_100g": 0.20,   # higher protein → better
    "fiber_100g": 0.15,      # higher fiber → better
}

# Reference max values per 100 g for normalisation
NUTRIENT_MAX: dict[str, float] = {
    "sugars_100g": 100.0,
    "fat_100g": 100.0,
    "salt_100g": 10.0,
    "proteins_100g": 50.0,
    "fiber_100g": 30.0,
}

NUTRISCORE_SCORE: dict[str, float] = {
    "a": 1.0,
    "b": 0.8,
    "c": 0.6,
    "d": 0.4,
    "e": 0.2,
}


class RankingEngine:
    def score_product(self, row: dict[str, Any]) -> float:
        """
        Compute a composite healthiness score in [0, 1].
        Higher = healthier.
        """
        total = 0.0
        weight_sum = 0.0

        for field, weight in DEFAULT_WEIGHTS.items():
            val = row.get(field)
            if val is None:
                continue
            max_val = NUTRIENT_MAX.get(field, 100.0)
            normalised = min(float(val) / max_val, 1.0)
            if field in ("proteins_100g", "fiber_100g"):
                # Higher is better → invert the penalty
                contribution = weight * normalised
            else:
                # Lower is better → penalty
                contribution = weight * (1.0 - normalised)
            total += contribution
            weight_sum += weight

        # Bonus for NutriScore
        grade = str(row.get("nutriscore_grade", "")).lower()
        ns_score = NUTRISCORE_SCORE.get(grade, 0.5)
        total += 0.1 * ns_score
        weight_sum += 0.1

        return round(total / weight_sum if weight_sum > 0 else 0.0, 4)

    def rank(
        self,
        rows: list[dict[str, Any]],
        intent: ParsedIntent,
        mapper,
    ) -> list[ProductResult]:
        """
        Score, sort, and convert raw DB rows to ProductResult objects.
        `mapper` is a TaxonomyMapper instance (injected to avoid circular import).
        """
        results: list[ProductResult] = []
        for row in rows:
            score = self.score_product(row)
            explanation = mapper.explain_constraints(intent, row)
            results.append(
                ProductResult(
                    barcode=str(row.get("code", "")),
                    product_name=str(row.get("product_name", "")),
                    categories=row.get("categories_tags"),
                    nutriscore_grade=row.get("nutriscore_grade"),
                    nova_group=_safe_int(row.get("nova_group")),
                    energy_kcal_100g=_safe_float(row.get("energy_kcal_100g")),
                    proteins_100g=_safe_float(row.get("proteins_100g")),
                    fat_100g=_safe_float(row.get("fat_100g")),
                    saturated_fat_100g=_safe_float(row.get("saturated_fat_100g")),
                    sugars_100g=_safe_float(row.get("sugars_100g")),
                    fiber_100g=_safe_float(row.get("fiber_100g")),
                    salt_100g=_safe_float(row.get("salt_100g")),
                    score=score,
                    explanation=explanation,
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results


def _safe_float(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None
