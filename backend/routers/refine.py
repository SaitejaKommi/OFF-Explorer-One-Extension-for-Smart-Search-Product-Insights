"""
routers/refine.py
-----------------
POST /refine  – conversational constraint refinement
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.schemas import RefineRequest, SearchResponse
from backend.services.constraint_extractor import ConstraintExtractor
from backend.services.context_manager import context_manager
from backend.services.duckdb_service import duckdb_service
from backend.services.ranking_engine import RankingEngine
from backend.services.relaxation_engine import RelaxationEngine
from backend.services.taxonomy_mapper import TaxonomyMapper

router = APIRouter()

_extractor = ConstraintExtractor()
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
async def refine(req: RefineRequest) -> SearchResponse:
    base_intent = context_manager.get_current_intent(req.session_id)
    if base_intent is None:
        raise HTTPException(status_code=404, detail="Session not found. Start a new search.")

    merged_intent = _extractor.merge_refinement(base_intent, req.refinement)
    context_manager.update_intent(req.session_id, merged_intent)

    rows = _do_search(merged_intent, req.limit)
    relaxation_applied = False
    relaxation_desc: str | None = None
    response_intent = merged_intent

    if not rows:
        relaxed_rows, relaxed_intent, relaxation_applied, relaxation_desc = _relaxer.apply_with_fallback(
            merged_intent, _do_search, req.limit
        )
        if relaxation_applied:
            rows = relaxed_rows
            response_intent = relaxed_intent

    results = _ranker.rank(rows, response_intent, _mapper)
    context_manager.set_last_results(req.session_id, [r.barcode for r in results])

    return SearchResponse(
        results=results,
        parsed_intent=response_intent,
        session_id=req.session_id,
        relaxation_applied=relaxation_applied,
        relaxation_description=relaxation_desc,
        total=len(results),
    )
