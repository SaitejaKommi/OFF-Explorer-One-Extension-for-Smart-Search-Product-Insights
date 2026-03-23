"""
tests/test_insight_engine.py
-----------------------------
Tests for rule-based InsightEngine: risk/positive indicators, summaries,
NutriScore/NOVA explanations, alternatives ranking, recommendations.
"""
import pytest

from backend.services.insight_engine import InsightEngine

engine = InsightEngine()


def _make_product(**kwargs):
    defaults = {
        "code": "1234567890",
        "product_name": "Test Product",
        "categories_tags": "en:snacks",
        "labels_tags": "en:organic",
        "nutriscore_grade": "b",
        "nova_group": 3,
        "energy_kcal_100g": 200.0,
        "proteins_100g": 5.0,
        "fat_100g": 10.0,
        "saturated_fat_100g": 3.0,
        "sugars_100g": 8.0,
        "fiber_100g": 2.0,
        "salt_100g": 0.5,
        "carbohydrates_100g": 30.0,
    }
    defaults.update(kwargs)
    return defaults


def test_risk_high_sugar():
    p = _make_product(sugars_100g=30.0)
    risks = engine._risk_indicators(p, "en")
    labels = [r.label for r in risks]
    assert "High Sugar" in labels


def test_risk_ultra_processed():
    p = _make_product(nova_group=4)
    risks = engine._risk_indicators(p, "en")
    labels = [r.label for r in risks]
    assert "Ultra-processed" in labels


def test_risk_high_salt():
    p = _make_product(salt_100g=2.5)
    risks = engine._risk_indicators(p, "en")
    labels = [r.label for r in risks]
    assert "High Salt" in labels


def test_risk_french_labels():
    p = _make_product(sugars_100g=30.0, nova_group=4)
    risks = engine._risk_indicators(p, "fr")
    labels = [r.label for r in risks]
    assert "Sucre élevé" in labels
    assert "Ultra-transformé" in labels


def test_positive_high_fiber():
    p = _make_product(fiber_100g=8.0)
    positives = engine._positive_indicators(p, "en")
    labels = [pos.label for pos in positives]
    assert "High Fiber" in labels


def test_positive_high_protein():
    p = _make_product(proteins_100g=25.0)
    positives = engine._positive_indicators(p, "en")
    labels = [pos.label for pos in positives]
    assert "High Protein" in labels


def test_positive_low_salt():
    p = _make_product(salt_100g=0.1)
    positives = engine._positive_indicators(p, "en")
    labels = [pos.label for pos in positives]
    assert "Low Salt" in labels


def test_positive_low_sugar():
    p = _make_product(sugars_100g=2.0)
    positives = engine._positive_indicators(p, "en")
    labels = [pos.label for pos in positives]
    assert "Low Sugar" in labels


def test_nutriscore_explanation_en():
    expl = engine._nutriscore_explanation("a", "en")
    assert expl is not None
    assert "A" in expl


def test_nutriscore_explanation_fr():
    expl = engine._nutriscore_explanation("b", "fr")
    assert expl is not None
    assert "B" in expl


def test_nutriscore_explanation_none():
    expl = engine._nutriscore_explanation(None, "en")
    assert expl is None


def test_nova_explanation_en():
    expl = engine._nova_explanation(4, "en")
    assert expl is not None
    assert "ultra" in expl.lower()


def test_nova_explanation_fr():
    expl = engine._nova_explanation(1, "fr")
    assert expl is not None
    assert "NOVA" in expl


def test_nova_explanation_none():
    expl = engine._nova_explanation(None, "en")
    assert expl is None


def test_health_summary_contains_name():
    p = _make_product()
    risks = engine._risk_indicators(p, "en")
    positives = engine._positive_indicators(p, "en")
    summary = engine._health_summary("Test Product", risks, positives, "b", 3, "en")
    assert "Test Product" in summary


def test_health_summary_french():
    p = _make_product()
    risks = engine._risk_indicators(p, "fr")
    positives = engine._positive_indicators(p, "fr")
    summary = engine._health_summary("Produit Test", risks, positives, "b", 3, "fr")
    assert "Produit Test" in summary
    assert "Nutri-Score" in summary


def test_rank_alternatives():
    alts = [
        _make_product(code="111", product_name="Alt A", sugars_100g=5.0, nutriscore_grade="a"),
        _make_product(code="222", product_name="Alt B", sugars_100g=20.0, nutriscore_grade="d"),
    ]
    ranked = engine._rank_alternatives(alts, exclude_barcode="9999")
    assert len(ranked) == 2
    # Alt A should rank higher (lower sugar, better NutriScore)
    assert ranked[0].barcode == "111"


def test_rank_alternatives_excludes_self():
    alts = [
        _make_product(code="1234567890", product_name="Self"),
        _make_product(code="999", product_name="Other"),
    ]
    ranked = engine._rank_alternatives(alts, exclude_barcode="1234567890")
    assert all(r.barcode != "1234567890" for r in ranked)


def test_food_pairings_known_category():
    p = _make_product(categories_tags="en:yogurts")
    pairings = engine._food_pairings(p)
    assert len(pairings) > 0
    assert "granola" in pairings or "fresh berries" in pairings


def test_food_pairings_unknown_category():
    p = _make_product(categories_tags="en:unknown-category")
    pairings = engine._food_pairings(p)
    assert pairings  # should return default


def test_recommendations_high_protein():
    p = _make_product(proteins_100g=25.0, fiber_100g=2.0, sugars_100g=8.0,
                      energy_kcal_100g=200.0, nova_group=3)
    recs = engine._recommendations(p, "en")
    assert any("post-workout" in r.lower() or "muscle" in r.lower() for r in recs)


def test_recommendations_high_fiber():
    p = _make_product(fiber_100g=8.0)
    recs = engine._recommendations(p, "en")
    assert any("digest" in r.lower() or "satiety" in r.lower() for r in recs)


def test_full_generate_returns_insight_response():
    p = _make_product()
    insight = engine.generate(p, [], "en", {})
    assert insight.barcode == "1234567890"
    assert insight.product_name == "Test Product"
    assert isinstance(insight.health_summary, str)
    assert insight.nutriscore_grade == "b"
    assert insight.nova_group == 3


def test_context_highlights():
    p = _make_product(sugars_100g=4.0)
    search_context = {
        "nutrient_constraints": [{"field": "sugars_100g", "operator": "lt", "value": 10.0}]
    }
    highlights = engine._context_highlights(p, search_context)
    assert "sugars_100g" in highlights
