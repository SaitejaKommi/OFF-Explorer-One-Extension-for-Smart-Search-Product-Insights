"""
insight_engine.py
-----------------
Rule-based product insight generation (health summary, risk/positive indicators,
NutriScore/NOVA explanations, alternatives ranking, food pairings).

No external API required.  Optional SLM enhancement applied on top.
"""
from __future__ import annotations

from typing import Any

from backend.models.schemas import (
    AlternativeProduct,
    InsightResponse,
    PositiveIndicator,
    RiskIndicator,
)
from backend.services.ranking_engine import RankingEngine, _safe_float, _safe_int

_ranking = RankingEngine()

# --------------------------------------------------------------------------- #
# Threshold definitions                                                          #
# --------------------------------------------------------------------------- #

# Per 100 g thresholds (UK/EU traffic-light style)
HIGH_SUGAR_G = 22.5
HIGH_FAT_G = 17.5
HIGH_SAT_FAT_G = 5.0
HIGH_SALT_G = 1.5
HIGH_FIBER_G = 6.0
HIGH_PROTEIN_G = 20.0
LOW_SODIUM_SALT_G = 0.3    # "low salt"

NUTRISCORE_EXPLANATIONS: dict[str, str] = {
    "a": "Nutri-Score A – Excellent nutritional quality. High in beneficial nutrients, low in sugar, fat, and salt.",
    "b": "Nutri-Score B – Good nutritional quality. Generally well-balanced.",
    "c": "Nutri-Score C – Average nutritional quality. Consume in moderation.",
    "d": "Nutri-Score D – Poor nutritional quality. High in unfavourable nutrients.",
    "e": "Nutri-Score E – Very poor nutritional quality. Limit consumption.",
}
NUTRISCORE_EXPLANATIONS_FR: dict[str, str] = {
    "a": "Nutri-Score A – Excellente qualité nutritionnelle.",
    "b": "Nutri-Score B – Bonne qualité nutritionnelle.",
    "c": "Nutri-Score C – Qualité nutritionnelle moyenne. À consommer avec modération.",
    "d": "Nutri-Score D – Mauvaise qualité nutritionnelle.",
    "e": "Nutri-Score E – Très mauvaise qualité nutritionnelle. À limiter.",
}

NOVA_EXPLANATIONS: dict[int, str] = {
    1: "NOVA 1 – Unprocessed or minimally processed food. Best choice.",
    2: "NOVA 2 – Processed culinary ingredient (e.g. oil, butter). Use in cooking.",
    3: "NOVA 3 – Processed food. Contains added salt, sugar, or fat.",
    4: "NOVA 4 – Ultra-processed food. Contains additives not used in home cooking. Limit consumption.",
}
NOVA_EXPLANATIONS_FR: dict[int, str] = {
    1: "NOVA 1 – Aliment non transformé ou peu transformé. Meilleur choix.",
    2: "NOVA 2 – Ingrédient culinaire transformé (ex. huile, beurre).",
    3: "NOVA 3 – Aliment transformé. Contient du sel, sucre ou graisses ajoutés.",
    4: "NOVA 4 – Aliment ultra-transformé. Contient des additifs. À limiter.",
}

# Simple rule-based food pairings by category keyword
FOOD_PAIRINGS: dict[str, list[str]] = {
    "en:yogurts": ["fresh berries", "granola", "honey", "banana"],
    "en:cereals": ["low-fat milk", "fresh fruit", "nuts"],
    "en:breads": ["avocado", "nut butter", "hummus", "eggs"],
    "en:cheeses": ["whole-grain crackers", "grapes", "walnuts", "apple slices"],
    "en:snacks": ["water", "fruit", "vegetable sticks"],
    "en:chocolates": ["almonds", "fresh strawberries", "herbal tea"],
    "en:fruits": ["yogurt", "nuts", "cheese"],
    "en:vegetables": ["olive oil", "hummus", "whole-grain bread"],
    "en:fish": ["brown rice", "steamed vegetables", "lemon"],
    "en:meats": ["roasted vegetables", "salad", "whole-grain side"],
    "en:pastas": ["tomato sauce", "olive oil", "lean protein", "vegetables"],
    "en:ice-creams": ["fresh fruit", "dark chocolate shavings"],
    "default": ["water", "fresh fruit", "vegetables"],
}

# Recommendations by health profile
RECOMMENDATION_RULES: list[tuple[dict, list[str]]] = [
    (
        {"proteins_100g": ("gt", HIGH_PROTEIN_G)},
        ["Good post-workout recovery snack", "Supports muscle repair"],
    ),
    (
        {"fiber_100g": ("gt", HIGH_FIBER_G)},
        ["Supports digestive health", "Good for satiety"],
    ),
    (
        {"sugars_100g": ("lt", 5.0), "energy_kcal_100g": ("lt", 150.0)},
        ["Good low-sugar snack option", "Suitable for weight management"],
    ),
    (
        {"nova_group": ("lte", 2)},
        ["Minimally processed – great everyday choice"],
    ),
]


# --------------------------------------------------------------------------- #
# Engine                                                                         #
# --------------------------------------------------------------------------- #

class InsightEngine:
    def generate(
        self,
        product: dict[str, Any],
        alternatives_raw: list[dict[str, Any]],
        language: str = "en",
        search_context: dict | None = None,
    ) -> InsightResponse:
        barcode = str(product.get("code", ""))
        name = str(product.get("product_name", "Unknown product"))
        ns_grade = str(product.get("nutriscore_grade", "") or "").lower() or None
        nova = _safe_int(product.get("nova_group"))

        risks = self._risk_indicators(product, language)
        positives = self._positive_indicators(product, language)
        health_summary = self._health_summary(name, risks, positives, ns_grade, nova, language)
        ns_expl = self._nutriscore_explanation(ns_grade, language)
        nova_expl = self._nova_explanation(nova, language)
        alternatives = self._rank_alternatives(alternatives_raw, barcode)
        pairings = self._food_pairings(product)
        recommendations = self._recommendations(product, language)
        context_highlights = self._context_highlights(product, search_context or {})

        return InsightResponse(
            barcode=barcode,
            product_name=name,
            language=language,
            health_summary=health_summary,
            nutriscore_grade=ns_grade,
            nutriscore_explanation=ns_expl,
            nova_group=nova,
            nova_explanation=nova_expl,
            risk_indicators=risks,
            positive_indicators=positives,
            alternatives=alternatives,
            food_pairings=pairings,
            daily_recommendations=recommendations,
            search_context_highlights=context_highlights,
            slm_enhanced=False,
        )

    # ----------------------------------------------------------------------- #
    def _risk_indicators(self, p: dict, lang: str) -> list[RiskIndicator]:
        risks: list[RiskIndicator] = []
        labels = {
            "en": {"high_sugar": "High Sugar", "high_fat": "High Fat",
                   "high_sat_fat": "High Saturated Fat", "high_salt": "High Salt",
                   "ultra_processed": "Ultra-processed"},
            "fr": {"high_sugar": "Sucre élevé", "high_fat": "Matières grasses élevées",
                   "high_sat_fat": "Graisses saturées élevées", "high_salt": "Sel élevé",
                   "ultra_processed": "Ultra-transformé"},
        }
        lbl = labels.get(lang, labels["en"])

        sugars = _safe_float(p.get("sugars_100g"))
        if sugars is not None and sugars > HIGH_SUGAR_G:
            risks.append(RiskIndicator(label=lbl["high_sugar"], value=f"{sugars:.1f} g/100g", level="high"))

        fat = _safe_float(p.get("fat_100g"))
        if fat is not None and fat > HIGH_FAT_G:
            risks.append(RiskIndicator(label=lbl["high_fat"], value=f"{fat:.1f} g/100g", level="high"))

        sat_fat = _safe_float(p.get("saturated_fat_100g"))
        if sat_fat is not None and sat_fat > HIGH_SAT_FAT_G:
            risks.append(RiskIndicator(label=lbl["high_sat_fat"], value=f"{sat_fat:.1f} g/100g", level="medium"))

        salt = _safe_float(p.get("salt_100g"))
        if salt is not None and salt > HIGH_SALT_G:
            risks.append(RiskIndicator(label=lbl["high_salt"], value=f"{salt:.1f} g/100g", level="high"))

        nova = _safe_int(p.get("nova_group"))
        if nova == 4:
            risks.append(RiskIndicator(label=lbl["ultra_processed"], value="NOVA 4", level="high"))

        return risks

    def _positive_indicators(self, p: dict, lang: str) -> list[PositiveIndicator]:
        positives: list[PositiveIndicator] = []
        labels = {
            "en": {"high_fiber": "High Fiber", "high_protein": "High Protein",
                   "low_salt": "Low Salt", "low_sugar": "Low Sugar"},
            "fr": {"high_fiber": "Riche en fibres", "high_protein": "Riche en protéines",
                   "low_salt": "Faible en sel", "low_sugar": "Faible en sucre"},
        }
        lbl = labels.get(lang, labels["en"])

        fiber = _safe_float(p.get("fiber_100g"))
        if fiber is not None and fiber >= HIGH_FIBER_G:
            positives.append(PositiveIndicator(label=lbl["high_fiber"], value=f"{fiber:.1f} g/100g"))

        protein = _safe_float(p.get("proteins_100g"))
        if protein is not None and protein >= HIGH_PROTEIN_G:
            positives.append(PositiveIndicator(label=lbl["high_protein"], value=f"{protein:.1f} g/100g"))

        salt = _safe_float(p.get("salt_100g"))
        if salt is not None and salt < LOW_SODIUM_SALT_G:
            positives.append(PositiveIndicator(label=lbl["low_salt"], value=f"{salt:.1f} g/100g"))

        sugars = _safe_float(p.get("sugars_100g"))
        if sugars is not None and sugars < 5.0:
            positives.append(PositiveIndicator(label=lbl["low_sugar"], value=f"{sugars:.1f} g/100g"))

        return positives

    def _health_summary(
        self,
        name: str,
        risks: list[RiskIndicator],
        positives: list[PositiveIndicator],
        ns_grade: str | None,
        nova: int | None,
        lang: str,
    ) -> str:
        risk_labels = [r.label for r in risks]
        positive_labels = [p.label for p in positives]

        if lang == "fr":
            summary_parts = [f"{name} :"]
            if positive_labels:
                summary_parts.append(f"Points positifs : {', '.join(positive_labels)}.")
            if risk_labels:
                summary_parts.append(f"Points d'attention : {', '.join(risk_labels)}.")
            if ns_grade:
                summary_parts.append(f"Nutri-Score {ns_grade.upper()}.")
            if nova:
                summary_parts.append(f"NOVA {nova}.")
        else:
            summary_parts = [f"{name}:"]
            if positive_labels:
                summary_parts.append(f"Positives: {', '.join(positive_labels)}.")
            if risk_labels:
                summary_parts.append(f"Concerns: {', '.join(risk_labels)}.")
            if ns_grade:
                summary_parts.append(f"Nutri-Score {ns_grade.upper()}.")
            if nova:
                summary_parts.append(f"NOVA group {nova}.")

        if not risk_labels and not positive_labels:
            summary_parts.append("Nutritional data is limited for this product." if lang == "en"
                                  else "Les données nutritionnelles sont limitées pour ce produit.")

        return " ".join(summary_parts)

    def _nutriscore_explanation(self, grade: str | None, lang: str) -> str | None:
        if not grade:
            return None
        expl_map = NUTRISCORE_EXPLANATIONS_FR if lang == "fr" else NUTRISCORE_EXPLANATIONS
        return expl_map.get(grade.lower())

    def _nova_explanation(self, nova: int | None, lang: str) -> str | None:
        if nova is None:
            return None
        expl_map = NOVA_EXPLANATIONS_FR if lang == "fr" else NOVA_EXPLANATIONS
        return expl_map.get(nova)

    def _rank_alternatives(
        self, rows: list[dict[str, Any]], exclude_barcode: str
    ) -> list[AlternativeProduct]:
        scored: list[tuple[float, dict]] = []
        for row in rows:
            if str(row.get("code", "")) == exclude_barcode:
                continue
            score = _ranking.score_product(row)
            breakdown = {
                k: _safe_float(row.get(k)) or 0.0
                for k in ["sugars_100g", "fat_100g", "salt_100g", "proteins_100g", "fiber_100g"]
            }
            scored.append((score, row, breakdown))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            AlternativeProduct(
                barcode=str(row.get("code", "")),
                product_name=str(row.get("product_name", "")),
                score=round(score, 4),
                score_breakdown=breakdown,
                nutriscore_grade=row.get("nutriscore_grade"),
            )
            for score, row, breakdown in scored[:5]
        ]

    def _food_pairings(self, product: dict[str, Any]) -> list[str]:
        cats = str(product.get("categories_tags", ""))
        for cat_key, pairings in FOOD_PAIRINGS.items():
            if cat_key in cats:
                return pairings
        return FOOD_PAIRINGS["default"]

    def _recommendations(self, product: dict[str, Any], lang: str) -> list[str]:
        recs: list[str] = []
        for conditions, messages in RECOMMENDATION_RULES:
            match = True
            for field, (op, threshold) in conditions.items():
                val = _safe_float(product.get(field)) or _safe_int(product.get(field))
                if val is None:
                    match = False
                    break
                ops = {"gt": val > threshold, "lt": val < threshold,
                       "gte": val >= threshold, "lte": val <= threshold}
                if not ops.get(op, False):
                    match = False
                    break
            if match:
                recs.extend(messages)
        return list(dict.fromkeys(recs))  # deduplicate preserving order

    def _context_highlights(
        self, product: dict[str, Any], search_context: dict
    ) -> dict[str, str]:
        """Highlight nutrients relevant to the original search intent."""
        highlights: dict[str, str] = {}
        nutrient_constraints = search_context.get("nutrient_constraints", [])
        for c in nutrient_constraints:
            field = c.get("field") if isinstance(c, dict) else getattr(c, "field", None)
            if field:
                val = _safe_float(product.get(field))
                if val is not None:
                    highlights[field] = f"{val:.1f} g/100g"
        return highlights
