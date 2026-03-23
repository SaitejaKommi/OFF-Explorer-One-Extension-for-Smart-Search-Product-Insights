"""
taxonomy_mapper.py
------------------
Maps parsed intent tokens to canonical Open Food Facts field names and values.
Acts as the bridge between NLP output and DuckDB query construction.
"""
from __future__ import annotations

from backend.models.schemas import NutrientConstraint, ParsedIntent

# Operator → SQL fragment
OPERATOR_SQL: dict[str, str] = {
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "eq": "=",
}

# Dietary tag → OFF field containing label/tag lists
DIETARY_TAG_FIELD = "labels_tags"
CATEGORY_FIELD = "categories_tags"

# OFF numeric fields available in the parquet export
VALID_NUMERIC_FIELDS = {
    "energy_kcal_100g",
    "proteins_100g",
    "fat_100g",
    "saturated_fat_100g",
    "sugars_100g",
    "fiber_100g",
    "salt_100g",
    "carbohydrates_100g",
    "sodium_100g",
}


class TaxonomyMapper:
    """
    Validates and maps ParsedIntent → SQL-ready structures.
    Filters out any unknown fields to prevent injection.
    """

    def validate_nutrient_constraints(
        self, constraints: list[NutrientConstraint]
    ) -> list[NutrientConstraint]:
        """Return only constraints whose field is a known OFF numeric column."""
        return [c for c in constraints if c.field in VALID_NUMERIC_FIELDS]

    def build_nutrient_conditions(
        self, constraints: list[NutrientConstraint]
    ) -> list[str]:
        """Convert NutrientConstraint list to SQL WHERE clause fragments."""
        parts: list[str] = []
        for c in constraints:
            sql_op = OPERATOR_SQL.get(c.operator, "=")
            # Safe: field is already validated against the whitelist
            parts.append(f"{c.field} {sql_op} {c.value}")
        return parts

    def build_category_conditions(self, categories: list[str]) -> list[str]:
        """
        DuckDB: categories_tags is stored as a comma-separated string or list.
        We use LIKE for broad compatibility with both representations.
        """
        conditions = []
        for cat in categories:
            safe_cat = cat.replace("'", "''")
            conditions.append(f"({CATEGORY_FIELD} LIKE '%{safe_cat}%')")
        return conditions

    def build_dietary_conditions(self, dietary_tags: list[str]) -> list[str]:
        """Build conditions for dietary labels (labels_tags field)."""
        conditions = []
        for tag in dietary_tags:
            safe_tag = tag.replace("'", "''")
            conditions.append(f"({DIETARY_TAG_FIELD} LIKE '%{safe_tag}%')")
        return conditions

    def explain_constraints(self, intent: ParsedIntent, row: dict) -> dict[str, str]:
        """
        Build a human-readable explanation dict showing which constraints
        the product satisfies.  Used for explainable results.
        """
        explanation: dict[str, str] = {}

        for c in intent.nutrient_constraints:
            actual = row.get(c.field)
            if actual is None:
                explanation[c.field] = "N/A"
                continue
            actual_f = float(actual)
            op = OPERATOR_SQL.get(c.operator, "=")
            satisfied = eval(f"{actual_f} {op} {c.value}")  # noqa: S307 – controlled inputs
            tick = "✓" if satisfied else "✗"
            explanation[c.field] = f"{actual_f:.1f} / {c.value} {tick}"

        for cat in intent.categories:
            cats_str = str(row.get("categories_tags", ""))
            explanation[f"category:{cat}"] = "✓" if cat in cats_str else "✗"

        for tag in intent.dietary_tags:
            labels_str = str(row.get("labels_tags", ""))
            explanation[f"label:{tag}"] = "✓" if tag in labels_str else "✗"

        return explanation
