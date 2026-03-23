"""Pydantic models shared across the API."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Search                                                                        #
# --------------------------------------------------------------------------- #

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    session_id: str | None = Field(None, description="Session ID for conversational continuity")
    limit: int = Field(20, ge=1, le=100)
    language: str = Field("en", description="Query language hint (en/fr)")


class NutrientConstraint(BaseModel):
    field: str
    operator: str   # "lt", "gt", "lte", "gte", "eq"
    value: float


class ParsedIntent(BaseModel):
    categories: list[str] = []
    dietary_tags: list[str] = []
    nutrient_constraints: list[NutrientConstraint] = []
    language: str = "en"
    raw_query: str = ""


class ProductResult(BaseModel):
    barcode: str
    product_name: str
    categories: str | None = None
    nutriscore_grade: str | None = None
    nova_group: int | None = None
    energy_kcal_100g: float | None = None
    proteins_100g: float | None = None
    fat_100g: float | None = None
    saturated_fat_100g: float | None = None
    sugars_100g: float | None = None
    fiber_100g: float | None = None
    salt_100g: float | None = None
    score: float = 0.0
    explanation: dict[str, Any] = {}


class SearchResponse(BaseModel):
    results: list[ProductResult]
    parsed_intent: ParsedIntent
    session_id: str
    relaxation_applied: bool = False
    relaxation_description: str | None = None
    total: int = 0


# --------------------------------------------------------------------------- #
# Refine                                                                        #
# --------------------------------------------------------------------------- #

class RefineRequest(BaseModel):
    refinement: str = Field(..., min_length=1, max_length=500)
    session_id: str
    limit: int = Field(20, ge=1, le=100)


# --------------------------------------------------------------------------- #
# Product Insights                                                               #
# --------------------------------------------------------------------------- #

class InsightRequest(BaseModel):
    barcode: str
    session_id: str | None = None
    language: str = "en"


class RiskIndicator(BaseModel):
    label: str
    value: str
    level: str   # "high", "medium", "low"


class PositiveIndicator(BaseModel):
    label: str
    value: str


class AlternativeProduct(BaseModel):
    barcode: str
    product_name: str
    score: float
    score_breakdown: dict[str, float] = {}
    nutriscore_grade: str | None = None


class InsightResponse(BaseModel):
    barcode: str
    product_name: str
    language: str = "en"
    health_summary: str
    nutriscore_grade: str | None = None
    nutriscore_explanation: str | None = None
    nova_group: int | None = None
    nova_explanation: str | None = None
    risk_indicators: list[RiskIndicator] = []
    positive_indicators: list[PositiveIndicator] = []
    alternatives: list[AlternativeProduct] = []
    food_pairings: list[str] = []
    daily_recommendations: list[str] = []
    search_context_highlights: dict[str, Any] = {}
    slm_enhanced: bool = False
