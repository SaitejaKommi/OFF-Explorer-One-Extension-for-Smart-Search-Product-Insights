"""
context_manager.py
------------------
Maintains per-session conversational context so that:
  - Search → Insight continuity works (pass intent to insight endpoint)
  - Refinement queries accumulate constraints correctly
  - History length is bounded

Storage: in-process dict (replace with Redis for multi-worker deployments).
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from backend.config import settings
from backend.models.schemas import ParsedIntent

_SESSION_TTL_SECONDS = 3600   # 1 hour


class _Session:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self.intent_history: list[ParsedIntent] = []
        self.last_results: list[str] = []   # list of barcodes

    def touch(self) -> None:
        self.updated_at = time.time()

    @property
    def current_intent(self) -> ParsedIntent | None:
        return self.intent_history[-1] if self.intent_history else None

    def push_intent(self, intent: ParsedIntent) -> None:
        self.intent_history.append(intent)
        if len(self.intent_history) > settings.context_max_history:
            self.intent_history.pop(0)
        self.touch()


class ContextManager:
    """Thread-safe (GIL) in-process session store."""

    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = _Session(session_id)
        self._evict_expired()
        return session_id

    def get_or_create(self, session_id: str | None) -> tuple[str, _Session]:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.touch()
            return session_id, session
        new_id = self.create_session()
        return new_id, self._sessions[new_id]

    def update_intent(self, session_id: str, intent: ParsedIntent) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.push_intent(intent)

    def get_current_intent(self, session_id: str) -> ParsedIntent | None:
        session = self._sessions.get(session_id)
        return session.current_intent if session else None

    def set_last_results(self, session_id: str, barcodes: list[str]) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.last_results = barcodes
            session.touch()

    def get_last_results(self, session_id: str) -> list[str]:
        session = self._sessions.get(session_id)
        return session.last_results if session else []

    def get_intent_as_context(self, session_id: str) -> dict[str, Any]:
        intent = self.get_current_intent(session_id)
        if intent is None:
            return {}
        return {
            "nutrient_constraints": [c.model_dump() for c in intent.nutrient_constraints],
            "dietary_tags": intent.dietary_tags,
            "categories": intent.categories,
        }

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.updated_at > _SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._sessions[sid]


# Module-level singleton
context_manager = ContextManager()
