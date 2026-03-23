"""
constraint_extractor.py
-----------------------
High-level helper that merges refinement queries on top of an existing
ParsedIntent (for conversational refinement, e.g. "now only gluten-free").

The refinement is parsed independently and then merged into the base intent:
- New dietary tags are added (union)
- New nutrient constraints override same-field existing ones
- New categories are added (union)
"""
from __future__ import annotations

import copy

from backend.models.schemas import ParsedIntent
from backend.services.intent_parser import IntentParser

_parser = IntentParser()


class ConstraintExtractor:
    """Merges a refinement query into an existing ParsedIntent."""

    def merge_refinement(
        self, base_intent: ParsedIntent, refinement_query: str
    ) -> ParsedIntent:
        """
        Parse the refinement and produce a new merged intent.
        Special patterns like "which has more protein?" trigger a sort directive
        (returned as a synthetic constraint with operator "gt" and value 0).
        """
        refined = copy.deepcopy(base_intent)
        delta = _parser.parse(refinement_query, language_hint=base_intent.language)

        # Merge categories
        for cat in delta.categories:
            if cat not in refined.categories:
                refined.categories.append(cat)

        # Merge dietary tags
        for tag in delta.dietary_tags:
            if tag not in refined.dietary_tags:
                refined.dietary_tags.append(tag)

        # Merge nutrient constraints (override same field)
        existing_fields = {c.field for c in refined.nutrient_constraints}
        for c in delta.nutrient_constraints:
            if c.field in existing_fields:
                # Replace existing constraint for this field
                refined.nutrient_constraints = [
                    nc for nc in refined.nutrient_constraints if nc.field != c.field
                ]
            refined.nutrient_constraints.append(c)

        # Update raw query to reflect the conversation
        refined.raw_query = f"{base_intent.raw_query} | {refinement_query}"

        return refined
