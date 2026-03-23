"""
FastAPI application entry point.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import insights, refine, search

app = FastAPI(
    title="Unified Intelligent Food Discovery System",
    description=(
        "Backend for the OFF Explorer browser extension. "
        "Provides semantic product search and rule-based nutritional insights "
        "over Open Food Facts parquet datasets via DuckDB."
    ),
    version="1.0.0",
)

# CORS – extension origin is a chrome-extension:// URL; allow all in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(refine.router, prefix="/refine", tags=["Refine"])
app.include_router(insights.router, prefix="/product-insights", tags=["Insights"])


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "slm_enabled": settings.slm_enabled}
