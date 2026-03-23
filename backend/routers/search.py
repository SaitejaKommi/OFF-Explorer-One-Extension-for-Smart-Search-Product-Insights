"""
routers/search.py
-----------------
POST /search  – natural language product search
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.config import settings
from backend.models.schemas import SearchRequest, SearchResponse
from backend.services.context_manager import context_manager
from backend.services.duckdb_service import duckdb_service
from backend.services.intent_parser import IntentParser
from backend.services.ranking_engine import RankingEngine
from backend.services.relaxation_engine import RelaxationEngine
from backend.services.taxonomy_mapper import TaxonomyMapper

router = APIRouter()

_parser = IntentParser()
_mapper = TaxonomyMapper()
_ranker = RankingEngine()
_relaxer = RelaxationEngine()


def _do_search(intent, limit: int):
    valid_constraints = _mapper.validate_nutrient_constraints(intent.nutrient_constraints)
    where = (
        _mapper.build_category_conditions(intent.categories)
        + _mapper.build_dietary_conditions(intent.dietary_tags)
        + _mapper.build_nutrient_conditions(valid_constraints)
    )
    return duckdb_service.execute_search(where, limit=limit)


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    session_id, _ = context_manager.get_or_create(req.session_id)

    intent = _parser.parse(req.query, language_hint=req.language)
    context_manager.update_intent(session_id, intent)

    rows = _do_search(intent, req.limit)
    relaxation_applied = False
    relaxation_desc: str | None = None
    response_intent = intent  # Always return the originally parsed intent in the response

    if not rows:
        relaxed_rows, relaxed_intent, relaxation_applied, relaxation_desc = _relaxer.apply_with_fallback(
            intent, _do_search, req.limit
        )
        if relaxation_applied:
            rows = relaxed_rows
            response_intent = relaxed_intent
            context_manager.update_intent(session_id, relaxed_intent)

    results = _ranker.rank(rows, response_intent, _mapper)
    context_manager.set_last_results(session_id, [r.barcode for r in results])

    return SearchResponse(
        results=results,
        parsed_intent=response_intent,
        session_id=session_id,
        relaxation_applied=relaxation_applied,
        relaxation_description=relaxation_desc,
        total=len(results),
    )
