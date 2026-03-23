"""
tests/test_taxonomy_mapper.py
------------------------------
Tests for TaxonomyMapper: constraint validation, SQL generation, explanation.
"""
import pytest

from backend.models.schemas import NutrientConstraint, ParsedIntent
from backend.services.taxonomy_mapper import TaxonomyMapper

mapper = TaxonomyMapper()


def test_validate_nutrient_constraints_known_field():
    c = NutrientConstraint(field="sugars_100g", operator="lt", value=5.0)
    valid = mapper.validate_nutrient_constraints([c])
    assert len(valid) == 1
    assert valid[0].field == "sugars_100g"


def test_validate_nutrient_constraints_unknown_field():
    c = NutrientConstraint(field="drop_table", operator="lt", value=0)
    valid = mapper.validate_nutrient_constraints([c])
    assert len(valid) == 0


def test_build_nutrient_conditions():
    constraints = [
        NutrientConstraint(field="sugars_100g", operator="lt", value=5.0),
        NutrientConstraint(field="proteins_100g", operator="gt", value=20.0),
    ]
    conds = mapper.build_nutrient_conditions(constraints)
    assert any("sugars_100g < 5.0" in c for c in conds)
    assert any("proteins_100g > 20.0" in c for c in conds)


def test_build_category_conditions():
    conds = mapper.build_category_conditions(["en:snacks"])
    assert len(conds) == 1
    assert "en:snacks" in conds[0]


def test_build_dietary_conditions():
    conds = mapper.build_dietary_conditions(["en:vegan"])
    assert len(conds) == 1
    assert "en:vegan" in conds[0]


def test_explain_constraints_satisfied():
    intent = ParsedIntent(
        nutrient_constraints=[NutrientConstraint(field="sugars_100g", operator="lt", value=10.0)],
        categories=["en:snacks"],
        dietary_tags=[],
    )
    row = {"sugars_100g": 3.0, "categories_tags": "en:snacks,en:biscuits", "labels_tags": ""}
    explanation = mapper.explain_constraints(intent, row)
    assert "✓" in explanation.get("sugars_100g", "")
    assert "✓" in explanation.get("category:en:snacks", "")


def test_explain_constraints_not_satisfied():
    intent = ParsedIntent(
        nutrient_constraints=[NutrientConstraint(field="sugars_100g", operator="lt", value=2.0)],
        categories=[],
        dietary_tags=[],
    )
    row = {"sugars_100g": 15.0, "categories_tags": "", "labels_tags": ""}
    explanation = mapper.explain_constraints(intent, row)
    assert "✗" in explanation.get("sugars_100g", "")


def test_explain_constraints_missing_value():
    intent = ParsedIntent(
        nutrient_constraints=[NutrientConstraint(field="fiber_100g", operator="gt", value=6.0)],
        categories=[],
        dietary_tags=[],
    )
    row = {"categories_tags": "", "labels_tags": ""}
    explanation = mapper.explain_constraints(intent, row)
    assert explanation.get("fiber_100g") == "N/A"
