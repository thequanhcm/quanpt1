"""V12 — Cross-Modal Memory Linking & Contextual Retrieval.

Liên kết tự động tri thức giữa các modal (text/code/documents/meetings) +
retrieval theo ngữ cảnh (project/task/user context).

**Cross-Modal Linking:**
- Entity extraction: person, org, project, date, code_symbol, file_path
- Cross-modal link detection: text↔code, document↔meeting, code↔document
- Context graph: xây dựng graph liên kết KU theo context

**Contextual Retrieval:**
- Context filters: project, task, user, meeting, time_range
- Context-aware ranking: relevance + context match score
- Explainability: giải thích tại sao KU liên quan

**API endpoints:**
- GET /api/memory/context/{current,set,clear}
- POST /api/memory/link/{cross_modal,code_text,doc_meeting}
- GET /api/memory/retrieve/contextual
- POST /api/memory/graph/build

**Tests:** 15 tests covering entity extraction, linking, retrieval, graph.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from collections import defaultdict

from quan_ai_brain.memory.deep_memory import DeepMemoryStore


# ============================================================================
# ENTITY EXTRACTION
# ============================================================================

@dataclass
class Entity:
    """Entity extracted from text."""
    entity_type: str  # 'person', 'org', 'project', 'date', 'code_symbol', 'file_path'
    text: str
    start_pos: int
    end_pos: int
    confidence: float = 0.85


ENTITY_PATTERNS = {
    'person': [
        r'(?:Anh|Chị|Em|Ông|Bà)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b',  # Full name
    ],
    'org': [
        r'\b(Viettel|TPBank|VNG|FPT|Google|Microsoft|Amazon)\b',
        r'\b([A-Z][A-Z]+(?:\s+[A-Z][A-Z]+)*)\b',  # Acronyms
    ],
    'project': [
        r'\b([A-Z][a-z]+(?:-[A-Z][a-z]+)+)\b',  # kebab-case project names
        r'\b(quan-ai-brain|netmind|chatbot|api-gateway)\b',
    ],
    'code_symbol': [
        r'\b(def|class|import|from|return|if|else|for|while)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b',
        r'\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\b',  # method calls
    ],
    'file_path': [
        r'([a-zA-Z0-9_/-]+\.(py|js|ts|md|json|yaml|yml|txt|pdf))',
        r'([a-zA-Z0-9_/-]+/)+[a-zA-Z0-9_.-]+',
    ],
    'date': [
        r'(\d{1,2}/\d{1,2}/\d{2,4})',
        r'(ngày\s+\d{1,2}\s+(?:tháng|tháng)\s+\d{1,2}|\d{1,2}\s+(?:tháng|tháng)\s+\d{2,4})',
    ],
}


def extract_entities(text: str, entity_types: list[str] | None = None) -> list[Entity]:
    """Trích xuất entities từ văn bản.
    
    Args:
        text: Văn bản cần trích xuất
        entity_types: Loại entities cần trích xuất (None = tất cả)
    
    Returns:
        List of Entity objects
    """
    if entity_types is None:
        entity_types = list(ENTITY_PATTERNS.keys())
    
    entities = []
    text_lower = text.lower()
    
    for entity_type in entity_types:
        if entity_type not in ENTITY_PATTERNS:
            continue
        
        for pattern in ENTITY_PATTERNS[entity_type]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity_text = match.group(0)
                # Adjust confidence based on pattern specificity
                confidence = 0.95 if entity_type == 'date' else 0.75
                
                entities.append(Entity(
                    entity_type=entity_type,
                    text=entity_text,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=confidence
                ))
    
    # Remove duplicates (overlapping)
    entities.sort(key=lambda e: e.start_pos)
    filtered = []
    last_end = -1
    for e in entities:
        if e.start_pos >= last_end:
            filtered.append(e)
            last_end = e.end_pos
    
    return filtered


# ============================================================================
# CROSS-MODAL LINKING
# ============================================================================

@dataclass
class CrossModalLink:
    """Liên kết giữa 2 KU từ modal khác nhau."""
    link_id: str
    ku_a: str  # knowledge_id
    ku_b: str
    link_type: str  # 'text_code', 'doc_meeting', 'code_doc', 'person_project'
    confidence: float
    evidence: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CrossModalLinker:
    """Phát hiện và tạo liên kết cross-modal."""
    
    def __init__(self, store: DeepMemoryStore):
        self._store = store
        self._link_cache: dict[tuple[str, str], CrossModalLink] = {}
    
    def find_cross_modal_links(
        self,
        ku_a: str,
        ku_b: str,
        link_types: list[str] | None = None
    ) -> CrossModalLink | None:
        """Phát hiện liên kết giữa 2 KU.
        
        Args:
            ku_a, ku_b: Knowledge unit IDs
            link_types: Loại liên kết cần tìm (None = tất cả)
        
        Returns:
            CrossModalLink nếu tìm thấy, None nếu không
        """
        unit_a = self._store.get_unit(ku_a)
        unit_b = self._store.get_unit(ku_b)
        
        if not unit_a or not unit_b:
            return None
        
        # Trích xuất entities từ cả 2 KU
        entities_a = extract_entities(unit_a['statement'])
        entities_b = extract_entities(unit_b['statement'])
        
        # Tìm entities chung
        common_entities = []
        for ea in entities_a:
            for eb in entities_b:
                if ea.entity_type == eb.entity_type and ea.text.lower() == eb.text.lower():
                    common_entities.append(ea)
        
        if not common_entities:
            return None
        
        # Xác định loại liên kết
        link_type = self._determine_link_type(common_entities, unit_a, unit_b)
        
        if link_types and link_type not in link_types:
            return None
        
        # Tính confidence
        confidence = min(0.95, 0.5 + len(common_entities) * 0.15)
        
        # Tạo evidence
        evidence = f"Chia sẻ entities: {', '.join([e.text for e in common_entities[:3]])}"
        
        link_id = f"l_{ku_a[2:8]}{ku_b[2:8]}"
        
        return CrossModalLink(
            link_id=link_id,
            ku_a=ku_a,
            ku_b=ku_b,
            link_type=link_type,
            confidence=confidence,
            evidence=evidence
        )
    
    def _determine_link_type(
        self,
        entities: list[Entity],
        unit_a: dict,
        unit_b: dict
    ) -> str:
        """Xác định loại liên kết dựa trên entities và nội dung."""
        entity_types = {e.entity_type for e in entities}
        
        if 'code_symbol' in entity_types:
            if 'file_path' in entity_types:
                return 'code_doc'
            return 'text_code'
        
        if 'person' in entity_types and 'project' in entity_types:
            return 'person_project'
        
        if 'date' in entity_types:
            return 'doc_meeting'  # Giả định: có ngày → meeting/document
        
        return 'text_code'  # Mặc định
    
    def link_code_to_text(self, code_symbol: str, text_ku_id: str) -> CrossModalLink | None:
        """Liên kết code symbol với tri thức text.
        
        Args:
            code_symbol: Tên hàm/class biến code
            text_ku_id: ID KU chứa mô tả text
        
        Returns:
            CrossModalLink hoặc None
        """
        # Tìm KU chứa code symbol
        code_ku = None
        for r in self._store._connection.execute(
            "SELECT knowledge_id, statement FROM knowledge_units WHERE statement LIKE ? AND status NOT IN ('SUPERSEDED','ARCHIVED')",
            (f'%{code_symbol}%',)
        ).fetchall():
            code_ku = self._store.get_unit(r[0])
            if code_ku:
                break
        
        if not code_ku:
            return None
        
        return self.find_cross_modal_links(code_ku['knowledge_id'], text_ku_id, ['text_code'])
    
    def link_document_to_meeting(self, doc_ku_id: str, meeting_ku_id: str) -> CrossModalLink | None:
        """Liên kết tài liệu với cuộc họp.
        
        Args:
            doc_ku_id: ID KU tài liệu
            meeting_ku_id: ID KU cuộc họp
        
        Returns:
            CrossModalLink hoặc None
        """
        return self.find_cross_modal_links(doc_ku_id, meeting_ku_id, ['doc_meeting'])
    
    def build_link_graph(self, scope: str | None = None) -> dict[str, list[str]]:
        """Xây dựng graph liên kết giữa các KU.
        
        Returns:
            Adjacency list: {ku_id: [linked_ku_id1, linked_ku_id2, ...]}
        """
        graph: dict[str, list[str]] = defaultdict(list)
        
        # Lấy tất cả KU
        query = "SELECT knowledge_id FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')"
        if scope:
            query += " AND scope = ?"
            rows = self._store._connection.execute(query, (scope,)).fetchall()
        else:
            rows = self._store._connection.execute(query).fetchall()
        
        kus = [r[0] for r in rows]
        
        # Tìm liên kết giữa từng cặp (O(n²) — chấp nhận cho dataset nhỏ)
        for i, ku_a in enumerate(kus[:50]):  # Giới hạn 50 KU để test
            for ku_b in kus[i+1:50]:
                link = self.find_cross_modal_links(ku_a, ku_b)
                if link:
                    graph[ku_a].append(ku_b)
                    graph[ku_b].append(ku_a)
        
        return dict(graph)


# ============================================================================
# CONTEXTUAL RETRIEVAL
# ============================================================================

@dataclass
class ContextFilters:
    """Bộ lọc ngữ cảnh cho retrieval."""
    project: str | None = None
    task: str | None = None
    user: str | None = None
    meeting: str | None = None
    time_range: tuple[datetime, datetime] | None = None
    scope: str | None = None


@dataclass
class ContextualResult:
    """Kết quả retrieval với context."""
    ku_id: str
    statement: str
    relevance_score: float
    context_match_score: float
    combined_score: float
    explanation: str
    entities: list[Entity] = field(default_factory=list)


class ContextualRetriever:
    """Retriever với context filters."""
    
    def __init__(self, store: DeepMemoryStore, context_weight: float = 0.3):
        self._store = store
        self._context_weight = context_weight  # Trọng số context vs relevance
        self._current_context: ContextFilters | None = None
    
    def set_context(self, **kwargs) -> None:
        """Thiết lập ngữ cảnh hiện tại.
        
        Args:
            project, task, user, meeting, time_range, scope
        """
        self._current_context = ContextFilters(**kwargs)
    
    def clear_context(self) -> None:
        """Xóa ngữ cảnh hiện tại."""
        self._current_context = None
    
    def get_current_context(self) -> ContextFilters | None:
        """Lấy ngữ cảnh hiện tại."""
        return self._current_context
    
    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 10,
        context: ContextFilters | None = None
    ) -> list[ContextualResult]:
        """Retrieval với context filters.
        
        Args:
            query: Câu hỏi/truy vấn
            top_k: Số kết quả trả về
            context: Context filters (None = dùng current context)
        
        Returns:
            List of ContextualResult sorted by combined_score
        """
        if context is None:
            context = self._current_context
        
        # 1. Retrieval cơ bản (semantic search hoặc keyword match)
        # Hiện tại dùng keyword match đơn giản
        query_terms = query.lower().split()
        
        candidates = []
        for r in self._store._connection.execute(
            "SELECT knowledge_id, statement, scope, valid_from_utc, valid_until_utc "
            "FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED') "
            "LIMIT 100"
        ).fetchall():
            ku_id, statement, scope, valid_from, valid_until = r
            
            # Tính relevance score (đơn giản: đếm từ trùng)
            statement_lower = statement.lower()
            relevance = sum(1 for term in query_terms if term in statement_lower) / len(query_terms) if query_terms else 0
            
            if relevance == 0:
                continue
            
            # Tính context match score
            context_match = self._calculate_context_match(ku_id, statement, scope, valid_from, valid_until, context)
            
            # Combined score
            combined = (1 - self._context_weight) * relevance + self._context_weight * context_match
            
            # Giải thích
            explanation = self._generate_explanation(ku_id, statement, relevance, context_match, context)
            
            # Extract entities
            entities = extract_entities(statement)
            
            candidates.append(ContextualResult(
                ku_id=ku_id,
                statement=statement[:200],
                relevance_score=round(relevance, 3),
                context_match_score=round(context_match, 3),
                combined_score=round(combined, 3),
                explanation=explanation,
                entities=entities
            ))
        
        # Sort by combined_score
        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        
        return candidates[:top_k]
    
    def _calculate_context_match(
        self,
        ku_id: str,
        statement: str,
        scope: str | None,
        valid_from: str | None,
        valid_until: str | None,
        context: ContextFilters | None
    ) -> float:
        """Tính context match score."""
        if context is None:
            return 0.5  # Trung bình nếu không có context
        
        score = 0.0
        max_score = 0.0
        
        # Project match
        if context.project:
            max_score += 0.3
            if context.project.lower() in statement.lower() or (scope and context.project.lower() in scope.lower()):
                score += 0.3
        
        # Task match
        if context.task:
            max_score += 0.2
            if context.task.lower() in statement.lower():
                score += 0.2
        
        # User match
        if context.user:
            max_score += 0.2
            if context.user.lower() in statement.lower():
                score += 0.2
        
        # Time range match
        if context.time_range:
            max_score += 0.3
            if valid_from:
                try:
                    ku_time = datetime.fromisoformat(valid_from.replace('Z', '+00:00'))
                    if context.time_range[0] <= ku_time <= context.time_range[1]:
                        score += 0.3
                except:
                    pass
        
        return score / max_score if max_score > 0 else 0.5
    
    def _generate_explanation(
        self,
        ku_id: str,
        statement: str,
        relevance: float,
        context_match: float,
        context: ContextFilters | None
    ) -> str:
        """Tạo giải thích tại sao KU liên quan."""
        parts = []
        
        if relevance > 0.7:
            parts.append("Rất liên quan đến truy vấn")
        elif relevance > 0.4:
            parts.append("Khá liên quan đến truy vấn")
        else:
            parts.append("Ít liên quan đến truy vấn")
        
        if context_match > 0.7:
            parts.append("khớp ngữ cảnh tốt")
        elif context_match > 0.4:
            parts.append("khớp ngữ cảnh trung bình")
        else:
            parts.append("ít khớp ngữ cảnh")
        
        if context:
            context_parts = []
            if context.project:
                context_parts.append(f"project={context.project}")
            if context.task:
                context_parts.append(f"task={context.task}")
            if context.user:
                context_parts.append(f"user={context.user}")
            
            if context_parts:
                parts.append(f"({', '.join(context_parts)})")
        
        return " | ".join(parts)
    
    def explain_relevance(
        self,
        ku_id: str,
        query: str,
        context: ContextFilters | None = None
    ) -> dict[str, Any]:
        """Giải thích chi tiết tại sao KU liên quan.
        
        Returns:
            {
                'ku_id': str,
                'relevance_breakdown': {...},
                'context_breakdown': {...},
                'entities_matched': [...],
                'suggestions': [...]
            }
        """
        unit = self._store.get_unit(ku_id)
        if not unit:
            return {'error': 'KU not found'}
        
        # Extract entities
        entities = extract_entities(unit['statement'])
        
        # Calculate scores
        query_terms = query.lower().split()
        relevance = sum(1 for term in query_terms if term in unit['statement'].lower()) / len(query_terms) if query_terms else 0
        
        context_match = self._calculate_context_match(
            ku_id,
            unit['statement'],
            unit.get('scope'),
            unit.get('valid_from_utc'),
            unit.get('valid_until_utc'),
            context
        )
        
        return {
            'ku_id': ku_id,
            'statement': unit['statement'][:200],
            'relevance_score': round(relevance, 3),
            'context_match_score': round(context_match, 3),
            'entities_matched': [e.text for e in entities[:5]],
            'suggestions': [
                "Thêm từ khóa cụ thể hơn" if relevance < 0.5 else "Truy vấn đã tốt",
                "Thiết lập context project/task" if context_match < 0.5 else "Context đã khớp"
            ]
        }