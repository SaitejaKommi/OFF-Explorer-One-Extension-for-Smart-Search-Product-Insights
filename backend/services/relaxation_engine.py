"""
relaxation_engine.py
--------------------
Implements stepwise constraint relaxation when a search returns 0 results.

Strategy (in order):
  1. Drop dietary tags one by one (least specific first)
  2. Relax nutrient constraints by ±20 % per step
  3. Drop categories one by one
  4. Return empty if nothing works after max_steps
"""
from __future__ import annotations

import copy
import logging

from backend.config import settings
from backend.models.schemas import NutrientConstraint, ParsedIntent

logger = logging.getLogger(__name__)

RELAXATION_FACTOR = 0.20   # relax numeric constraints by 20 % per step


class RelaxationEngine:
    def relax(self, intent: ParsedIntent) -> tuple[ParsedIntent | None, str]:
        """
        Return (relaxed_intent, description) or (None, "") if no relaxation possible.
        Modifies a *copy* of the intent.
        """
        relaxed = copy.deepcopy(intent)

        # Step 1: drop dietary tags
        if relaxed.dietary_tags:
            dropped = relaxed.dietary_tags.pop()
            desc = f"Removed dietary filter: {dropped}"
            logger.info("Relaxation: %s", desc)
            return relaxed, desc

        # Step 2: relax nutrient constraints
        for i, c in enumerate(relaxed.nutrient_constraints):
            if c.operator in ("lt", "lte"):
                new_val = round(c.value * (1 + RELAXATION_FACTOR), 2)
                relaxed.nutrient_constraints[i] = NutrientConstraint(
                    field=c.field, operator=c.operator, value=new_val
                )
                desc = f"Relaxed {c.field} threshold from {c.value} to {new_val}"
                logger.info("Relaxation: %s", desc)
                return relaxed, desc
            elif c.operator in ("gt", "gte"):
                new_val = round(c.value * (1 - RELAXATION_FACTOR), 2)
                relaxed.nutrient_constraints[i] = NutrientConstraint(
                    field=c.field, operator=c.operator, value=new_val
                )
                desc = f"Relaxed {c.field} minimum from {c.value} to {new_val}"
                logger.info("Relaxation: %s", desc)
                return relaxed, desc

        # Step 3: drop categories
        if relaxed.categories:
            dropped = relaxed.categories.pop()
            desc = f"Removed category filter: {dropped}"
            logger.info("Relaxation: %s", desc)
            return relaxed, desc

        return None, ""

    def apply_with_fallback(
        self,
        intent: ParsedIntent,
        search_fn,
        limit: int,
    ) -> tuple[list, ParsedIntent, bool, str]:
        """
        Try up to settings.max_relaxation_steps relaxations.
        Returns (results, final_intent, relaxation_applied, description).
        """
        for step in range(settings.max_relaxation_steps):
            relaxed_intent, desc = self.relax(intent)
            if relaxed_intent is None:
                break
            results = search_fn(relaxed_intent, limit)
            if results:
                return results, relaxed_intent, True, desc
            intent = relaxed_intent  # continue relaxing from the already-relaxed intent

        return [], intent, False, ""
