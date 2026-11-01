"""Session Memory and Continuous Fact Extraction for QUAN AI BRAIN.

Extracts user-provided preferences, owner facts, and procedural rules from
active chat conversations, and ensures every conversational turn is persisted
into Long-Term Memory (episodes & verified/user-provided memories).
"""
from __future__ import annotations

import re
from typing import Any

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.memory.models import MemoryRecord, MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


# Patterns for extracting direct owner facts and preferences
_PATTERNS_IDENTITY = [
    re.compile(r"(?i)\btôi\s+(?:tên\s+là|là)\s+([A-Za-z0-9\u00C0-\u1EF9\s]{2,40})"),
    re.compile(r"(?i)\btên\s+tôi\s+là\s+([A-Za-z0-9\u00C0-\u1EF9\s]{2,40})"),
    re.compile(r"(?i)\bmy\s+name\s+is\s+([A-Za-z0-9\s]{2,40})"),
]

_PATTERNS_PREFERENCE = [
    re.compile(r"(?i)\b(?:sở\s+thích\s+của\s+tôi\s+là|tôi\s+thích|tôi\s+đặc\s+biệt\s+thích)\s+([^,.;\n]{3,120})"),
    re.compile(r"(?i)\b(?:tôi\s+quan\s+tâm\s+đến|tôi\s+ưu\s+tiên)\s+([^,.;\n]{3,120})"),
    re.compile(r"(?i)\b(?:i\s+like|i\s+prefer|my\s+preference\s+is)\s+([^,.;\n]{3,120})"),
]

_PATTERNS_INSTRUCTION = [
    re.compile(r"(?i)\b(?:hãy\s+nhớ\s+rằng|nhớ\s+rằng|lưu\s+ý\s+rằng|quy\s+tắc\s+là)\s+([^;\n]{4,200})"),
    re.compile(r"(?i)\b(?:remember\s+that|please\s+note\s+that)\s+([^;\n]{4,200})"),
]


class SessionMemoryManager:
    """Manages chat turn persistence and fact extraction into MemoryStore."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    @staticmethod
    def extract_user_facts(text: str) -> list[tuple[str, MemoryType, str]]:
        """Extract identity, preferences, and procedural rules from user prompt.
        
        Returns list of (fact_statement, memory_type, tag).
        """
        facts: list[tuple[str, MemoryType, str]] = []
        cleaned = text.strip()

        # 1. Identity
        for pattern in _PATTERNS_IDENTITY:
            m = pattern.search(cleaned)
            if m:
                val = m.group(1).strip()
                if len(val) >= 2 and not any(w in val.lower() for w in ["ai", "gì", "không"]):
                    facts.append((
                        f"Chủ sở hữu tên là: {val}",
                        MemoryType.SEMANTIC,
                        "owner_identity",
                    ))
                    break

        # 2. Preferences
        for pattern in _PATTERNS_PREFERENCE:
            m = pattern.search(cleaned)
            if m:
                val = m.group(1).strip()
                if len(val) >= 3:
                    facts.append((
                        f"Sở thích / Ưu tiên của Chủ sở hữu: {val}",
                        MemoryType.PREFERENCE,
                        "owner_preference",
                    ))
                    break

        # 3. Direct instructions or rules
        for pattern in _PATTERNS_INSTRUCTION:
            m = pattern.search(cleaned)
            if m:
                val = m.group(1).strip()
                if len(val) >= 4:
                    facts.append((
                        f"Quy tắc / Chỉ thị từ Chủ sở hữu: {val}",
                        MemoryType.SEMANTIC,
                        "owner_instruction",
                    ))
                    break

        return facts

    def persist_chat_turn(
        self,
        *,
        session_id: str,
        user_query: str,
        assistant_reply: str,
        model_used: str,
        used_memory_ids: list[str] | None = None,
        project_scope: str = "general",
        system_prompt: str | None = None,  # Sprint 16: optional, NOT stored (memory hygiene)
    ) -> dict[str, Any]:
        """Record the conversational turn and any extracted facts into persistent storage.
        
        Sprint 16 (Memory Hygiene): system_prompt is accepted but NOT stored to prevent
        noise contradictions from raw system instructions. Only user_query + assistant_reply
        are persisted.
        """
        safe_query = redact_text(user_query.strip())
        safe_reply = redact_text(assistant_reply.strip())
        used_ids = used_memory_ids or []

        # 1. Record episode in episodes table (NO system_prompt — memory hygiene)
        summary_text = f"User: {safe_query[:150]} | Assistant: {safe_reply[:150]}"
        episode_id = self.store.add_episode(
            summary=summary_text,
            kind="chat_turn",
            source_ref=f"chat_session:{session_id}",
            metadata={
                "session_id": session_id,
                "user_query": safe_query,
                "assistant_reply": safe_reply,
                "model_used": model_used,
                "used_memory_ids": used_ids,
                # system_prompt intentionally excluded (Sprint 16 memory hygiene)
            },
        )

        # 2. Record episodic interaction in memories table for retrieval by future queries
        chat_content = (
            f"Phiên tương tác [{session_id}] - Người dùng hỏi: \"{safe_query}\" -> "
            f"Trợ lý trả lời: \"{safe_reply}\""
        )
        mem_episode = self.store.store_memory(
            content=chat_content,
            memory_type=MemoryType.EPISODIC,
            source_ref=f"chat_session:{session_id}",
            verification_status=VerificationStatus.OBSERVED,
            confidence_score=1.0,
            project_scope=project_scope,
            tags=["chat_turn", f"session_{session_id}"],
            metadata={"session_id": session_id, "episode_id": episode_id},
        )

        # 3. Extract and store any explicit facts or preferences
        extracted = self.extract_user_facts(user_query)
        new_memory_ids: list[str] = [mem_episode.id]

        for fact_text, mem_type, tag in extracted:
            # Check if similar content already exists to avoid duplicate proliferation
            existing = self.store.search_memories(
                query=fact_text[:40],
                memory_type=mem_type,
                project_scope=project_scope,
                limit=5,
            )
            if not existing:
                rec = self.store.store_memory(
                    content=fact_text,
                    memory_type=mem_type,
                    source_ref=f"user_direct_input:{session_id}",
                    verification_status=VerificationStatus.USER_PROVIDED,
                    confidence_score=0.95,
                    project_scope=project_scope,
                    tags=["user_provided", tag, f"session_{session_id}"],
                    metadata={"extracted_from_query": safe_query},
                )
                new_memory_ids.append(rec.id)

        return {
            "episode_id": episode_id,
            "episodic_memory_id": mem_episode.id,
            "new_memory_ids": new_memory_ids,
            "extracted_facts_count": len(extracted),
        }

    def get_recent_session_history(self, session_id: str, limit: int = 3) -> list[dict[str, Any]]:
        """Retrieve recent chat interactions from this session."""
        episodes = self.store.list_episodes(limit=limit * 3)
        session_turns: list[dict[str, Any]] = []

        for ep in episodes:
            if ep.get("kind") == "chat_turn" and ep.get("source_ref") == f"chat_session:{session_id}":
                session_turns.append(ep)
                if len(session_turns) >= limit:
                    break

        return session_turns
