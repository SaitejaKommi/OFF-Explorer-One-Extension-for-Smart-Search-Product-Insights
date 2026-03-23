"""
intent_parser.py
----------------
Rule-based natural language parser for food search queries.
Supports English and French.  No external API required.

Example inputs:
  EN: "low sugar vegan snacks under 200 calories"
  FR: "collations véganes à faible teneur en sucre moins de 200 calories"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.models.schemas import NutrientConstraint, ParsedIntent

# --------------------------------------------------------------------------- #
# Vocabulary maps                                                                #
# --------------------------------------------------------------------------- #

# dietary tag keywords → canonical OFF tags
DIETARY_KEYWORDS: dict[str, list[str]] = {
    "vegan": ["en:vegan", "fr:végane", "fr:vegan", "fr:véganes", "fr:végans"],
    "vegetarian": ["en:vegetarian", "fr:végétarien", "fr:végétariens", "fr:végétarienne"],
    "gluten-free": ["en:gluten-free", "fr:sans-gluten", "fr:sans gluten", "fr:sans-gluten"],
    "organic": ["en:organic", "fr:bio", "fr:biologique"],
    "lactose-free": ["en:lactose-free", "fr:sans-lactose", "fr:sans lactose"],
    "kosher": ["en:kosher", "fr:casher"],
    "halal": ["en:halal"],
    "palm-oil-free": ["en:no-palm-oil", "fr:sans-huile-de-palme"],
}

# keyword → OFF field + operator
NUTRIENT_KEYWORDS: dict[str, dict] = {
    # sugar
    r"low[\s-]sugar": {"field": "sugars_100g", "operator": "lt", "value": 5.0},
    r"no[\s-]sugar": {"field": "sugars_100g", "operator": "lte", "value": 0.5},
    r"high[\s-]sugar": {"field": "sugars_100g", "operator": "gt", "value": 20.0},
    # fat
    r"low[\s-]fat": {"field": "fat_100g", "operator": "lt", "value": 3.0},
    r"no[\s-]fat|fat[\s-]free": {"field": "fat_100g", "operator": "lte", "value": 0.5},
    # sodium / salt
    r"low[\s-]sodium|low[\s-]salt": {"field": "salt_100g", "operator": "lt", "value": 0.3},
    # protein
    r"high[\s-]protein": {"field": "proteins_100g", "operator": "gt", "value": 20.0},
    # fiber
    r"high[\s-]fiber|high[\s-]fibre": {"field": "fiber_100g", "operator": "gt", "value": 6.0},
    # French variants
    r"faible[\s-]en[\s-]sucre|peu[\s-]sucr[ée]|faible[\s\w]*en[\s-]sucre": {"field": "sugars_100g", "operator": "lt", "value": 5.0},
    r"faible[\s-]en[\s-]gras|peu[\s-]gras": {"field": "fat_100g", "operator": "lt", "value": 3.0},
    r"riche[\s-]en[\s-]prot[ée]ines?": {"field": "proteins_100g", "operator": "gt", "value": 20.0},
    r"riche[\s-]en[\s-]fibres?": {"field": "fiber_100g", "operator": "gt", "value": 6.0},
}

# calorie constraint patterns  (en + fr)
CALORIE_PATTERNS: list[tuple[str, str]] = [
    (r"under\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "lt"),
    (r"less\s+than\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "lt"),
    (r"below\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "lt"),
    (r"(\d+)\s*(?:cal(?:orie)?s?|kcal)\s+or\s+less", "lte"),
    (r"at\s+least\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "gte"),
    (r"more\s+than\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "gt"),
    # French
    (r"moins\s+de\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "lt"),
    (r"au[\s-]moins\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "gte"),
    (r"plus\s+de\s+(\d+)\s*(?:cal(?:orie)?s?|kcal)", "gt"),
]

# generic nutrient-value patterns  e.g. "protein > 15g", "sugar < 5 g"
GENERIC_NUTRIENT_PATTERN = re.compile(
    r"(\w+(?:[\s_]\w+)?)\s*([<>]=?|less than|more than|under|over)\s*(\d+(?:\.\d+)?)\s*g?",
    re.IGNORECASE,
)
NUTRIENT_ALIAS: dict[str, str] = {
    "sugar": "sugars_100g",
    "sugars": "sugars_100g",
    "protein": "proteins_100g",
    "proteins": "proteins_100g",
    "fat": "fat_100g",
    "fats": "fat_100g",
    "salt": "salt_100g",
    "sodium": "salt_100g",
    "fiber": "fiber_100g",
    "fibre": "fiber_100g",
    "carbs": "carbohydrates_100g",
    "carbohydrates": "carbohydrates_100g",
    # French
    "sucre": "sugars_100g",
    "sucres": "sugars_100g",
    "protéine": "proteins_100g",
    "protéines": "proteins_100g",
    "graisse": "fat_100g",
    "sel": "salt_100g",
    "fibre": "fiber_100g",
    "fibres": "fiber_100g",
}
OPERATOR_ALIAS: dict[str, str] = {
    "<": "lt", "<=": "lte", ">": "gt", ">=": "gte",
    "less than": "lt", "under": "lt", "more than": "gt", "over": "gt",
}

# category keywords (simplified mapping to OFF categories_tags values)
CATEGORY_KEYWORDS: dict[str, str] = {
    "snack": "en:snacks",
    "snacks": "en:snacks",
    "breakfast": "en:breakfasts",
    "cereal": "en:cereals",
    "cereals": "en:cereals",
    "bread": "en:breads",
    "beverage": "en:beverages",
    "beverages": "en:beverages",
    "drink": "en:beverages",
    "drinks": "en:beverages",
    "juice": "en:fruit-juices",
    "yogurt": "en:yogurts",
    "yoghurt": "en:yogurts",
    "cheese": "en:cheeses",
    "meat": "en:meats",
    "fish": "en:fish",
    "pasta": "en:pastas",
    "biscuit": "en:biscuits",
    "biscuits": "en:biscuits",
    "cookie": "en:cookies",
    "cookies": "en:cookies",
    "chocolate": "en:chocolates",
    "dairy": "en:dairies",
    "fruit": "en:fruits",
    "fruits": "en:fruits",
    "vegetable": "en:vegetables",
    "vegetables": "en:vegetables",
    "sauce": "en:sauces",
    "sauces": "en:sauces",
    "oil": "en:oils",
    "oils": "en:oils",
    "soup": "en:soups",
    "soups": "en:soups",
    "ice cream": "en:ice-creams",
    # French
    "collation": "en:snacks",
    "collations": "en:snacks",
    "petit-déjeuner": "en:breakfasts",
    "pain": "en:breads",
    "boisson": "en:beverages",
    "boissons": "en:beverages",
    "jus": "en:fruit-juices",
    "yaourt": "en:yogurts",
    "fromage": "en:cheeses",
    "viande": "en:meats",
    "poisson": "en:fish",
    "pâtes": "en:pastas",
    "biscuit": "en:biscuits",
    "gâteau": "en:cakes",
    "chocolat": "en:chocolates",
    "légumes": "en:vegetables",
    "fruits": "en:fruits",
    "soupe": "en:soups",
    "glace": "en:ice-creams",
}

# Language detection
FR_WORDS = {
    "végane", "vegan", "végétarien", "faible", "riche", "sucre", "sucres", "calories",
    "moins", "plus", "de", "en", "gras", "protéines", "fibres", "collation", "collations",
    "boisson", "boissons", "pain", "fromage", "viande", "poisson", "légumes", "soupe",
    "jus", "yaourt", "glace", "sel", "graisse", "bio", "biologique", "sans",
}


def _detect_language(query: str) -> str:
    tokens = set(re.findall(r"[a-zàâçéèêëîïôûùüÿœæ]+", query.lower()))
    overlap = tokens & FR_WORDS
    return "fr" if len(overlap) >= 2 else "en"


# --------------------------------------------------------------------------- #
# Parser                                                                        #
# --------------------------------------------------------------------------- #

class IntentParser:
    """
    Rule-based intent parser.  Returns a ParsedIntent with categories,
    dietary_tags, and nutrient_constraints extracted from a free-text query.
    """

    def parse(self, query: str, language_hint: str = "auto") -> ParsedIntent:
        q = query.strip()
        language = language_hint if language_hint in ("en", "fr") else _detect_language(q)
        q_lower = q.lower()

        categories = self._extract_categories(q_lower)
        dietary_tags = self._extract_dietary_tags(q_lower)
        nutrient_constraints = self._extract_nutrient_constraints(q_lower)

        return ParsedIntent(
            categories=categories,
            dietary_tags=dietary_tags,
            nutrient_constraints=nutrient_constraints,
            language=language,
            raw_query=q,
        )

    def _extract_categories(self, q: str) -> list[str]:
        found: list[str] = []
        # longest match first to handle "ice cream" before "cream"
        for kw in sorted(CATEGORY_KEYWORDS.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(kw) + r"\b", q) and CATEGORY_KEYWORDS[kw] not in found:
                found.append(CATEGORY_KEYWORDS[kw])
        return found

    def _extract_dietary_tags(self, q: str) -> list[str]:
        found: list[str] = []
        for canonical, patterns in DIETARY_KEYWORDS.items():
            # check canonical keyword itself and all language variants
            all_kws = [canonical] + [p.split(":", 1)[1] for p in patterns]
            for kw in all_kws:
                if re.search(r"\b" + re.escape(kw) + r"\b", q):
                    # Append the first OFF tag for this dietary label
                    tag = next(p for p in DIETARY_KEYWORDS[canonical] if p.startswith("en:"))
                    if tag not in found:
                        found.append(tag)
                    break
        return found

    def _extract_nutrient_constraints(self, q: str) -> list[NutrientConstraint]:
        constraints: list[NutrientConstraint] = []
        seen_fields: set[str] = set()

        # 1. Named keyword patterns (e.g. "low sugar", "high protein")
        for pattern, spec in NUTRIENT_KEYWORDS.items():
            if re.search(pattern, q, re.IGNORECASE):
                field = spec["field"]
                if field not in seen_fields:
                    constraints.append(NutrientConstraint(**spec))
                    seen_fields.add(field)

        # 2. Calorie patterns
        if "energy_kcal_100g" not in seen_fields:
            for pat, op in CALORIE_PATTERNS:
                m = re.search(pat, q, re.IGNORECASE)
                if m:
                    constraints.append(NutrientConstraint(
                        field="energy_kcal_100g",
                        operator=op,
                        value=float(m.group(1)),
                    ))
                    seen_fields.add("energy_kcal_100g")
                    break

        # 3. Generic "nutrient OP value" patterns  (e.g. "protein > 15g")
        for m in GENERIC_NUTRIENT_PATTERN.finditer(q):
            raw_nutrient = m.group(1).strip().lower()
            raw_op = m.group(2).strip().lower()
            raw_val = float(m.group(3))
            field = NUTRIENT_ALIAS.get(raw_nutrient)
            operator = OPERATOR_ALIAS.get(raw_op)
            if field and operator and field not in seen_fields:
                constraints.append(NutrientConstraint(field=field, operator=operator, value=raw_val))
                seen_fields.add(field)

        return constraints
