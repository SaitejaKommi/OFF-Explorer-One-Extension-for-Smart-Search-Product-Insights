"""
tests/test_relaxation_engine.py
--------------------------------
Tests for RelaxationEngine: constraint relaxation logic.
"""
import pytest

from backend.models.schemas import NutrientConstraint, ParsedIntent
from backend.services.relaxation_engine import RelaxationEngine, RELAXATION_FACTOR

engine = RelaxationEngine()


def _intent(**kwargs):
    defaults = {
        "categories": ["en:snacks"],
        "dietary_tags": ["en:vegan", "en:gluten-free"],
        "nutrient_constraints": [
            NutrientConstraint(field="sugars_100g", operator="lt", value=5.0),
            NutrientConstraint(field="proteins_100g", operator="gt", value=20.0),
        ],
        "language": "en",
        "raw_query": "test",
    }
    defaults.update(kwargs)
    return ParsedIntent(**defaults)


def test_relax_drops_dietary_tag_first():
    intent = _intent()
    original_tags = list(intent.dietary_tags)
    relaxed, desc = engine.relax(intent)
    assert relaxed is not None
    # One dietary tag removed
    assert len(relaxed.dietary_tags) == len(original_tags) - 1
    assert "dietary" in desc.lower() or "removed" in desc.lower()


def test_relax_increases_lt_threshold():
    intent = _intent(dietary_tags=[])  # no dietary tags to drop first
    sugar_c = NutrientConstraint(field="sugars_100g", operator="lt", value=5.0)
    intent = _intent(dietary_tags=[], nutrient_constraints=[sugar_c])
    relaxed, desc = engine.relax(intent)
    assert relaxed is not None
    new_c = next(c for c in relaxed.nutrient_constraints if c.field == "sugars_100g")
    assert new_c.value > 5.0
    expected = round(5.0 * (1 + RELAXATION_FACTOR), 2)
    assert abs(new_c.value - expected) < 0.01


def test_relax_decreases_gt_threshold():
    intent = _intent(
        dietary_tags=[],
        nutrient_constraints=[NutrientConstraint(field="proteins_100g", operator="gt", value=20.0)],
    )
    relaxed, desc = engine.relax(intent)
    assert relaxed is not None
    new_c = next(c for c in relaxed.nutrient_constraints if c.field == "proteins_100g")
    assert new_c.value < 20.0


def test_relax_drops_category_last():
    intent = _intent(
        dietary_tags=[],
        nutrient_constraints=[],
        categories=["en:snacks"],
    )
    relaxed, desc = engine.relax(intent)
    assert relaxed is not None
    assert len(relaxed.categories) == 0


def test_relax_nothing_to_relax():
    intent = _intent(dietary_tags=[], nutrient_constraints=[], categories=[])
    relaxed, desc = engine.relax(intent)
    assert relaxed is None
    assert desc == ""


def test_original_intent_not_mutated():
    """relax() must not modify the original intent."""
    intent = _intent()
    original_tags = list(intent.dietary_tags)
    engine.relax(intent)
    assert intent.dietary_tags == original_tags
