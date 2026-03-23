"""
tests/test_ranking_engine.py
-----------------------------
Tests for the RankingEngine: score computation and result ranking.
"""
import pytest

from backend.models.schemas import ParsedIntent
from backend.services.ranking_engine import RankingEngine
from backend.services.taxonomy_mapper import TaxonomyMapper

ranker = RankingEngine()
mapper = TaxonomyMapper()


def _row(**kwargs):
    defaults = {
        "code": "123",
        "product_name": "Test",
        "categories_tags": "en:snacks",
        "labels_tags": "",
        "nutriscore_grade": "b",
        "nova_group": 2,
        "energy_kcal_100g": 150.0,
        "proteins_100g": 5.0,
        "fat_100g": 5.0,
        "saturated_fat_100g": 2.0,
        "sugars_100g": 4.0,
        "fiber_100g": 3.0,
        "salt_100g": 0.2,
        "carbohydrates_100g": 20.0,
    }
    defaults.update(kwargs)
    return defaults


def test_score_between_zero_and_one():
    score = ranker.score_product(_row())
    assert 0.0 <= score <= 1.0


def test_healthier_product_scores_higher():
    healthy = _row(sugars_100g=2.0, fat_100g=2.0, salt_100g=0.1,
                   proteins_100g=25.0, fiber_100g=8.0, nutriscore_grade="a")
    unhealthy = _row(sugars_100g=30.0, fat_100g=25.0, salt_100g=2.0,
                     proteins_100g=1.0, fiber_100g=0.0, nutriscore_grade="e")
    assert ranker.score_product(healthy) > ranker.score_product(unhealthy)


def test_rank_sorts_by_score_descending():
    rows = [
        _row(code="bad", sugars_100g=40.0, fat_100g=30.0, nutriscore_grade="e"),
        _row(code="good", sugars_100g=2.0, proteins_100g=20.0, nutriscore_grade="a"),
    ]
    intent = ParsedIntent()
    results = ranker.rank(rows, intent, mapper)
    assert results[0].barcode == "good"
    assert results[-1].barcode == "bad"


def test_rank_with_missing_fields():
    row = {"code": "x", "product_name": "No Data"}
    intent = ParsedIntent()
    results = ranker.rank([row], intent, mapper)
    assert len(results) == 1
    assert 0.0 <= results[0].score <= 1.0


def test_score_nutriscore_bonus():
    row_a = _row(nutriscore_grade="a", sugars_100g=5.0, fat_100g=5.0)
    row_e = _row(nutriscore_grade="e", sugars_100g=5.0, fat_100g=5.0)
    assert ranker.score_product(row_a) > ranker.score_product(row_e)
