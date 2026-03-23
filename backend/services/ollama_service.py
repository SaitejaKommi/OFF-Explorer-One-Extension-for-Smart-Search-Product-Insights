"""
ollama_service.py
-----------------
Optional SLM (Phi-3-mini via Ollama) integration.
All calls are guarded by the `slm_enabled` feature flag.
Falls back gracefully to rule-based output if Ollama is unavailable.
"""
from __future__ import annotations

import json
import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Thin HTTP client for the Ollama REST API.
    Only used when settings.slm_enabled == True.
    """

    def _generate(self, prompt: str) -> str | None:
        """Call Ollama /api/generate and return the response text or None on failure."""
        if not settings.slm_enabled:
            return None
        try:
            resp = httpx.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.slm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 200},
                },
                timeout=settings.ollama_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except Exception as exc:
            logger.warning("Ollama call failed (%s). Falling back to rule-based output.", exc)
            return None

    def enhance_health_summary(
        self, rule_summary: str, product_name: str, language: str = "en"
    ) -> str:
        """Optionally enrich the rule-based health summary with SLM prose."""
        if not settings.slm_enabled:
            return rule_summary
        lang_instruction = "Respond in French." if language == "fr" else "Respond in English."
        prompt = (
            f"{lang_instruction}\n"
            f"You are a concise nutrition assistant. Given this food product summary, "
            f"rewrite it in 2 sentences that are friendly and informative. "
            f"Do not add any information not present in the summary.\n\n"
            f"Product: {product_name}\n"
            f"Summary: {rule_summary}\n\n"
            f"Rewritten summary:"
        )
        enhanced = self._generate(prompt)
        return enhanced if enhanced else rule_summary

    def suggest_pairings(
        self, product_name: str, category: str, language: str = "en"
    ) -> list[str]:
        """
        Use SLM to suggest food pairings.
        Returns a list of strings or falls back to empty list (caller uses rule-based).
        """
        if not settings.slm_enabled:
            return []
        lang_instruction = "Respond in French." if language == "fr" else "Respond in English."
        prompt = (
            f"{lang_instruction}\n"
            f"Suggest 4 healthy food pairings for '{product_name}' (category: {category}). "
            f"Return ONLY a JSON array of short strings, e.g. [\"apple\", \"water\"]. "
            f"No explanation."
        )
        raw = self._generate(prompt)
        if not raw:
            return []
        try:
            # Extract JSON array from response
            start = raw.index("[")
            end = raw.rindex("]") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            return []

    def suggest_recommendations(
        self, product_name: str, nutrient_profile: dict, language: str = "en"
    ) -> list[str]:
        """Generate daily-use recommendations via SLM."""
        if not settings.slm_enabled:
            return []
        lang_instruction = "Respond in French." if language == "fr" else "Respond in English."
        profile_str = ", ".join(f"{k}: {v}" for k, v in nutrient_profile.items())
        prompt = (
            f"{lang_instruction}\n"
            f"Given this product '{product_name}' with nutrients ({profile_str}), "
            f"suggest 3 practical daily-use tips (e.g. 'good post-workout'). "
            f"Return ONLY a JSON array of short strings. No explanation."
        )
        raw = self._generate(prompt)
        if not raw:
            return []
        try:
            start = raw.index("[")
            end = raw.rindex("]") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            return []


# Module-level singleton
ollama_service = OllamaService()
