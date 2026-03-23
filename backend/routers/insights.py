"""
routers/insights.py
-------------------
POST /product-insights  – rule-based (+ optional SLM) product insight generation
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.models.schemas import InsightRequest, InsightResponse
from backend.services.context_manager import context_manager
from backend.services.duckdb_service import duckdb_service
from backend.services.insight_engine import InsightEngine
from backend.services.off_api_service import off_api_service
from backend.services.ollama_service import ollama_service

router = APIRouter()

_insight_engine = InsightEngine()


def _extract_primary_category(categories_tags: str | None) -> str:
    if not categories_tags:
        return ""
    parts = [p.strip() for p in categories_tags.split(",")]
    return parts[0] if parts else ""


@router.post("", response_model=InsightResponse)
async def product_insights(req: InsightRequest) -> InsightResponse:
    product = duckdb_service.fetch_product_by_barcode(req.barcode)
    product_source = "duckdb"
    if not product:
        product = off_api_service.fetch_product_by_barcode(req.barcode)
        product_source = "off_api"
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product {req.barcode} not found in local parquet data or OFF API.",
        )

    # Fetch alternatives in the same category
    primary_category = _extract_primary_category(str(product.get("categories_tags", "")))
    alternatives_raw = (
        duckdb_service.fetch_alternatives(
            category_like=primary_category,
            exclude_barcode=req.barcode,
            limit=10,
        )
        if primary_category and product_source == "duckdb"
        else []
    )

    # Pull search context (for highlighting relevant nutrients)
    search_context = context_manager.get_intent_as_context(req.session_id or "") if req.session_id else {}

    # Generate rule-based insights
    insight = _insight_engine.generate(
        product=product,
        alternatives_raw=alternatives_raw,
        language=req.language,
        search_context=search_context,
    )

    # Optional SLM enhancement
    slm_enhanced = False
    if settings.slm_enabled:
        enhanced_summary = ollama_service.enhance_health_summary(
            insight.health_summary, insight.product_name, req.language
        )
        if enhanced_summary != insight.health_summary:
            insight = insight.model_copy(update={"health_summary": enhanced_summary})
            slm_enhanced = True

        slm_pairings = ollama_service.suggest_pairings(
            insight.product_name, primary_category, req.language
        )
        if slm_pairings:
            insight = insight.model_copy(update={"food_pairings": slm_pairings})
            slm_enhanced = True

        nutrient_profile = {
            "proteins_100g": product.get("proteins_100g"),
            "sugars_100g": product.get("sugars_100g"),
            "fiber_100g": product.get("fiber_100g"),
            "fat_100g": product.get("fat_100g"),
        }
        slm_recs = ollama_service.suggest_recommendations(
            insight.product_name, nutrient_profile, req.language
        )
        if slm_recs:
            combined = list(dict.fromkeys(insight.daily_recommendations + slm_recs))
            insight = insight.model_copy(update={"daily_recommendations": combined})
            slm_enhanced = True

        if slm_enhanced:
            insight = insight.model_copy(update={"slm_enhanced": True})

    return insight
