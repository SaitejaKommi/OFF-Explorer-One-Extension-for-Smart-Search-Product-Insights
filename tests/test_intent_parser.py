"""
tests/test_intent_parser.py
---------------------------
Unit tests for the rule-based IntentParser.
Covers English queries, French queries, and edge cases.
"""
import pytest

from backend.services.intent_parser import IntentParser

parser = IntentParser()


# --------------------------------------------------------------------------- #
# English tests                                                                  #
# --------------------------------------------------------------------------- #

def test_parse_low_sugar_vegan_snacks():
    intent = parser.parse("low sugar vegan snacks under 200 calories")
    assert "en:snacks" in intent.categories
    assert "en:vegan" in intent.dietary_tags
    # Constraint: sugars < 5g
    sugar_c = next((c for c in intent.nutrient_constraints if c.field == "sugars_100g"), None)
    assert sugar_c is not None
    assert sugar_c.operator == "lt"
    assert sugar_c.value == 5.0
    # Constraint: calories < 200
    cal_c = next((c for c in intent.nutrient_constraints if c.field == "energy_kcal_100g"), None)
    assert cal_c is not None
    assert cal_c.operator == "lt"
    assert cal_c.value == 200.0


def test_parse_high_protein_gluten_free():
    intent = parser.parse("high protein gluten-free cereal")
    assert "en:cereals" in intent.categories
    assert "en:gluten-free" in intent.dietary_tags
    prot_c = next((c for c in intent.nutrient_constraints if c.field == "proteins_100g"), None)
    assert prot_c is not None
    assert prot_c.operator == "gt"


def test_parse_low_fat_organic():
    intent = parser.parse("low fat organic yogurt")
    assert "en:yogurts" in intent.categories
    assert "en:organic" in intent.dietary_tags
    fat_c = next((c for c in intent.nutrient_constraints if c.field == "fat_100g"), None)
    assert fat_c is not None
    assert fat_c.operator == "lt"


def test_parse_calorie_at_least():
    intent = parser.parse("at least 300 calories")
    cal_c = next((c for c in intent.nutrient_constraints if c.field == "energy_kcal_100g"), None)
    assert cal_c is not None
    assert cal_c.operator == "gte"
    assert cal_c.value == 300.0


def test_parse_generic_nutrient_pattern():
    intent = parser.parse("protein > 15g bread")
    assert "en:breads" in intent.categories
    prot_c = next((c for c in intent.nutrient_constraints if c.field == "proteins_100g"), None)
    assert prot_c is not None
    assert prot_c.operator == "gt"
    assert prot_c.value == 15.0


def test_parse_no_sugar_vegan():
    intent = parser.parse("no sugar vegan chocolate")
    assert "en:chocolates" in intent.categories
    assert "en:vegan" in intent.dietary_tags
    sugar_c = next((c for c in intent.nutrient_constraints if c.field == "sugars_100g"), None)
    assert sugar_c is not None
    assert sugar_c.operator == "lte"
    assert sugar_c.value == 0.5


def test_parse_high_fiber():
    intent = parser.parse("high fiber cereal for breakfast")
    fiber_c = next((c for c in intent.nutrient_constraints if c.field == "fiber_100g"), None)
    assert fiber_c is not None
    assert fiber_c.operator == "gt"


def test_parse_multiple_categories_picks_one():
    intent = parser.parse("low sodium soup")
    assert "en:soups" in intent.categories
    salt_c = next((c for c in intent.nutrient_constraints if c.field == "salt_100g"), None)
    assert salt_c is not None
    assert salt_c.operator == "lt"


def test_parse_no_constraints_plain_query():
    intent = parser.parse("chocolate biscuits")
    # Categories detected
    assert len(intent.categories) >= 1
    # No nutrient constraints needed
    assert isinstance(intent.nutrient_constraints, list)


def test_parse_ice_cream_multi_word():
    intent = parser.parse("low fat ice cream")
    assert "en:ice-creams" in intent.categories


# --------------------------------------------------------------------------- #
# French tests                                                                   #
# --------------------------------------------------------------------------- #

def test_parse_french_low_sugar_vegan_snacks():
    intent = parser.parse("collations véganes à faible teneur en sucre moins de 200 calories")
    assert "en:snacks" in intent.categories
    assert "en:vegan" in intent.dietary_tags
    sugar_c = next((c for c in intent.nutrient_constraints if c.field == "sugars_100g"), None)
    assert sugar_c is not None
    assert sugar_c.operator == "lt"
    cal_c = next((c for c in intent.nutrient_constraints if c.field == "energy_kcal_100g"), None)
    assert cal_c is not None
    assert cal_c.value == 200.0


def test_parse_french_high_protein():
    intent = parser.parse("riche en protéines sans gluten")
    prot_c = next((c for c in intent.nutrient_constraints if c.field == "proteins_100g"), None)
    assert prot_c is not None
    assert prot_c.operator == "gt"
    assert "en:gluten-free" in intent.dietary_tags


def test_parse_french_less_than_calories():
    intent = parser.parse("moins de 150 calories par 100g")
    cal_c = next((c for c in intent.nutrient_constraints if c.field == "energy_kcal_100g"), None)
    assert cal_c is not None
    assert cal_c.operator == "lt"
    assert cal_c.value == 150.0


def test_language_detection_french():
    intent = parser.parse("collations véganes faible sucre")
    assert intent.language == "fr"


def test_language_detection_english():
    intent = parser.parse("low sugar vegan snacks")
    assert intent.language == "en"


# --------------------------------------------------------------------------- #
# Edge cases                                                                     #
# --------------------------------------------------------------------------- #

def test_parse_empty_like_query():
    intent = parser.parse("food")
    assert isinstance(intent.categories, list)
    assert isinstance(intent.dietary_tags, list)
    assert isinstance(intent.nutrient_constraints, list)


def test_parse_only_calories():
    intent = parser.parse("less than 100 calories")
    cal_c = next((c for c in intent.nutrient_constraints if c.field == "energy_kcal_100g"), None)
    assert cal_c is not None
    assert cal_c.operator == "lt"
    assert cal_c.value == 100.0


def test_parse_multiple_dietary_tags():
    intent = parser.parse("vegan gluten-free organic snack")
    assert "en:vegan" in intent.dietary_tags
    assert "en:gluten-free" in intent.dietary_tags
    assert "en:organic" in intent.dietary_tags


def test_no_injection_in_query():
    """Ensure quotes and SQL-like content in query don't cause exceptions."""
    intent = parser.parse("'; DROP TABLE products; --")
    assert isinstance(intent, object)


def test_parse_halal_kosher():
    intent = parser.parse("halal snacks")
    assert "en:halal" in intent.dietary_tags

    intent2 = parser.parse("kosher bread")
    assert "en:kosher" in intent2.dietary_tags
