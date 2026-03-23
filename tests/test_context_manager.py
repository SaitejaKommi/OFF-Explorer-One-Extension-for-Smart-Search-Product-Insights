"""
tests/test_context_manager.py
------------------------------
Tests for ContextManager: session lifecycle, intent storage, refinement continuity.
"""
import pytest

from backend.models.schemas import NutrientConstraint, ParsedIntent
from backend.services.context_manager import ContextManager


@pytest.fixture
def cm():
    return ContextManager()


def _intent(**kwargs):
    defaults = {
        "categories": ["en:snacks"],
        "dietary_tags": ["en:vegan"],
        "nutrient_constraints": [NutrientConstraint(field="sugars_100g", operator="lt", value=5.0)],
        "language": "en",
        "raw_query": "low sugar vegan snacks",
    }
    defaults.update(kwargs)
    return ParsedIntent(**defaults)


def test_create_session_returns_string(cm):
    sid = cm.create_session()
    assert isinstance(sid, str)
    assert len(sid) > 0


def test_get_or_create_new_session(cm):
    sid, session = cm.get_or_create(None)
    assert isinstance(sid, str)
    assert session is not None


def test_get_or_create_existing_session(cm):
    sid = cm.create_session()
    sid2, session = cm.get_or_create(sid)
    assert sid2 == sid


def test_update_and_get_intent(cm):
    sid = cm.create_session()
    intent = _intent()
    cm.update_intent(sid, intent)
    retrieved = cm.get_current_intent(sid)
    assert retrieved is not None
    assert retrieved.raw_query == "low sugar vegan snacks"


def test_intent_history_bounded(cm):
    """History should not exceed context_max_history."""
    from backend.config import settings
    sid = cm.create_session()
    for i in range(settings.context_max_history + 5):
        cm.update_intent(sid, _intent(raw_query=f"query {i}"))
    session = cm._sessions[sid]
    assert len(session.intent_history) <= settings.context_max_history


def test_last_results_stored(cm):
    sid = cm.create_session()
    cm.set_last_results(sid, ["111", "222", "333"])
    results = cm.get_last_results(sid)
    assert results == ["111", "222", "333"]


def test_get_intent_as_context(cm):
    sid = cm.create_session()
    intent = _intent()
    cm.update_intent(sid, intent)
    ctx = cm.get_intent_as_context(sid)
    assert "nutrient_constraints" in ctx
    assert len(ctx["nutrient_constraints"]) == 1
    assert ctx["nutrient_constraints"][0]["field"] == "sugars_100g"


def test_get_intent_as_context_no_session(cm):
    ctx = cm.get_intent_as_context("nonexistent")
    assert ctx == {}


def test_get_last_results_empty_session(cm):
    results = cm.get_last_results("nonexistent")
    assert results == []
