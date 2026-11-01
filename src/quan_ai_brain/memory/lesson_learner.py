"""Lesson Learner - Extract and manage lessons from outcomes.

Provides:
- Automatic lesson extraction from success/failure
- Pattern recognition for lessons
- Lesson recommendation engine
- Lesson validation and refinement
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .experience_store import ExperienceStore, Experience, OutcomeType, ExperienceType


class LessonCategory(str, Enum):
    """Category of lesson."""
    BEST_PRACTICE = 'best_practice'
    PITFALL = 'pitfall'
    TIP = 'tip'
    WARNING = 'warning'
    INSIGHT = 'insight'
    PROCEDURE = 'procedure'


@dataclass
class Lesson:
    """Extracted lesson."""
    id: str
    title: str
    content: str
    category: LessonCategory
    source_experience_id: str
    context: str
    applicability: str
    confidence: float
    created_at: str
    verified: bool = False
    tags_json: str = field(default_factory=lambda: '[]')
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Lesson':
        return cls(**data)


class LessonLearner:
    """Extract and manage lessons from experiences."""
    
    def __init__(self, experience_store: ExperienceStore | None = None):
        self.experience_store = experience_store or ExperienceStore()
        self._lessons: dict[str, Lesson] = {}
    
    def extract_lessons_from_experience(self, exp_id: str) -> list[Lesson]:
        """Extract lessons from a single experience."""
        experience = self.experience_store.get_experience(exp_id)
        if not experience:
            raise ValueError(f"Experience {exp_id} not found")
        
        lessons = []
        
        # Extract based on outcome
        if experience.outcome == OutcomeType.SUCCESS:
            lessons.extend(self._extract_success_lessons(experience))
        elif experience.outcome == OutcomeType.FAILURE:
            lessons.extend(self._extract_failure_lessons(experience))
        elif experience.outcome == OutcomeType.PARTIAL:
            lessons.extend(self._extract_partial_lessons(experience))
        
        # Also check if lessons_learned field exists
        if experience.lessons_learned:
            lessons.extend(self._parse_lessons_text(experience))
        
        # Store lessons
        for lesson in lessons:
            self._store_lesson(lesson)
        
        return lessons
    
    def extract_lessons_from_all(self, experience_type: ExperienceType | None = None) -> int:
        """Extract lessons from all experiences."""
        experiences = self.experience_store.search_experiences(
            experience_type=experience_type,
            limit=1000
        )
        
        count = 0
        for exp in experiences:
            lessons = self.extract_lessons_from_experience(exp.id)
            count += len(lessons)
        
        return count
    
    def _extract_success_lessons(self, experience: Experience) -> list[Lesson]:
        """Extract lessons from successful experiences."""
        lessons = []
        
        # Extract best practices
        best_practice = Lesson(
            id=f"lesson_{experience.id}_bp",
            title=f"Best Practice: {experience.title}",
            content=f"Successfully completed {experience.title} by: {experience.action_taken}",
            category=LessonCategory.BEST_PRACTICE,
            source_experience_id=experience.id,
            context=experience.description,
            applicability="Similar tasks with comparable context",
            confidence=0.85,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags_json=experience.tags_json
        )
        lessons.append(best_practice)
        
        # Extract insights
        if experience.outcome_details:
            insight = Lesson(
                id=f"lesson_{experience.id}_insight",
                title=f"Insight: {experience.title}",
                content=f"Key success factor: {experience.outcome_details}",
                category=LessonCategory.INSIGHT,
                source_experience_id=experience.id,
                context=experience.description,
                applicability="When facing similar challenges",
                confidence=0.75,
                created_at=datetime.now(timezone.utc).isoformat(),
                tags_json=experience.tags_json
            )
            lessons.append(insight)
        
        return lessons
    
    def _extract_failure_lessons(self, experience: Experience) -> list[Lesson]:
        """Extract lessons from failed experiences."""
        lessons = []
        
        # Extract pitfalls
        pitfall = Lesson(
            id=f"lesson_{experience.id}_pitfall",
            title=f"Pitfall to Avoid: {experience.title}",
            content=f"Failed when: {experience.outcome_details or 'Unknown reason'}. "
                   f"Action taken: {experience.action_taken}",
            category=LessonCategory.PITFALL,
            source_experience_id=experience.id,
            context=experience.description,
            applicability="Avoid this approach in similar situations",
            confidence=0.90,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags_json=experience.tags_json
        )
        lessons.append(pitfall)
        
        # Extract warnings
        warning = Lesson(
            id=f"lesson_{experience.id}_warning",
            title=f"Warning: {experience.title}",
            content=f"Be cautious: {experience.outcome_details or 'This approach may fail'}",
            category=LessonCategory.WARNING,
            source_experience_id=experience.id,
            context=experience.description,
            applicability="Before attempting similar tasks",
            confidence=0.80,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags_json=experience.tags_json
        )
        lessons.append(warning)
        
        return lessons
    
    def _extract_partial_lessons(self, experience: Experience) -> list[Lesson]:
        """Extract lessons from partial successes."""
        lessons = []
        
        # Extract tips
        tip = Lesson(
            id=f"lesson_{experience.id}_tip",
            title=f"Tip: {experience.title}",
            content=f"Partial success achieved. Consider: {experience.outcome_details or 'Refine the approach'}",
            category=LessonCategory.TIP,
            source_experience_id=experience.id,
            context=experience.description,
            applicability="When initial approach yields partial results",
            confidence=0.70,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags_json=experience.tags_json
        )
        lessons.append(tip)
        
        return lessons
    
    def _parse_lessons_text(self, experience: Experience) -> list[Lesson]:
        """Parse lessons from lessons_learned text field."""
        lessons = []
        
        if not experience.lessons_learned:
            return lessons
        
        # Split by common delimiters
        lesson_texts = re.split(r'\n+|\d+\.\s*|-\s*', experience.lessons_learned)
        
        for i, text in enumerate(lesson_texts[:5]):  # Limit to 5 lessons
            text = text.strip()
            if len(text) < 20:
                continue
            
            lesson = Lesson(
                id=f"lesson_{experience.id}_parsed_{i}",
                title=f"Learned: {text[:50]}...",
                content=text,
                category=LessonCategory.INSIGHT,
                source_experience_id=experience.id,
                context=experience.description,
                applicability="Based on documented experience",
                confidence=0.65,
                created_at=datetime.now(timezone.utc).isoformat(),
                tags_json=experience.tags_json
            )
            lessons.append(lesson)
        
        return lessons
    
    def _store_lesson(self, lesson: Lesson):
        """Store lesson in memory."""
        self._lessons[lesson.id] = lesson
    
    def get_lesson(self, lesson_id: str) -> Lesson | None:
        """Get lesson by ID."""
        return self._lessons.get(lesson_id)
    
    def search_lessons(self, category: LessonCategory | None = None,
                      tags: list[str] | None = None,
                      verified_only: bool = False,
                      limit: int = 50) -> list[Lesson]:
        """Search lessons with filters."""
        lessons = list(self._lessons.values())
        
        if category:
            lessons = [l for l in lessons if l.category == category]
        
        if verified_only:
            lessons = [l for l in lessons if l.verified]
        
        if tags:
            filtered = []
            for lesson in lessons:
                lesson_tags = json.loads(lesson.tags_json)
                if any(tag in lesson_tags for tag in tags):
                    filtered.append(lesson)
            lessons = filtered
        
        return lessons[:limit]
    
    def recommend_lessons(self, context: dict,
                         experience_type: ExperienceType,
                         max_results: int = 5) -> list[Lesson]:
        """Recommend relevant lessons based on context."""
        # Find similar experiences
        similar_exps = self.experience_store.find_similar_experiences(
            context=context,
            experience_type=experience_type,
            max_results=10
        )
        
        # Collect lessons from similar experiences
        recommended = []
        for match in similar_exps:
            exp = match.experience
            for lesson_id, lesson in self._lessons.items():
                if lesson.source_experience_id == exp.id:
                    # Adjust confidence based on similarity
                    lesson.confidence *= match.similarity_score
                    recommended.append(lesson)
        
        # Sort by confidence
        recommended.sort(key=lambda l: l.confidence, reverse=True)
        return recommended[:max_results]
    
    def verify_lesson(self, lesson_id: str, verified: bool = True,
                     verification_note: str = ""):
        """Mark lesson as verified or unverified."""
        lesson = self._lessons.get(lesson_id)
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")
        
        lesson.verified = verified
        
        metadata = json.loads(lesson.metadata_json)
        metadata['verified_at'] = datetime.now(timezone.utc).isoformat()
        metadata['verification_note'] = verification_note
        lesson.metadata_json = json.dumps(metadata)
    
    def get_lesson_statistics(self) -> dict[str, Any]:
        """Get lesson statistics."""
        stats = {
            'total_lessons': len(self._lessons),
            'verified_count': 0,
            'by_category': {},
            'by_source_type': {}
        }
        
        for lesson in self._lessons.values():
            if lesson.verified:
                stats['verified_count'] += 1
            
            category = lesson.category.value
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            source_type = self._lessons[lesson.id].source_experience_id[:10]
            stats['by_source_type'][source_type] = stats['by_source_type'].get(source_type, 0) + 1
        
        return stats
    
    def export_best_practices(self) -> list[dict[str, Any]]:
        """Export all best practices."""
        best_practices = self.search_lessons(
            category=LessonCategory.BEST_PRACTICE,
            verified_only=True,
            limit=100
        )
        
        return [lp.to_dict() for lp in best_practices]
    
    def export_pitfalls(self) -> list[dict[str, Any]]:
        """Export all pitfalls and warnings."""
        pitfalls = self.search_lessons(
            category=LessonCategory.PITFALL,
            limit=100
        )
        warnings = self.search_lessons(
            category=LessonCategory.WARNING,
            limit=100
        )
        
        return [p.to_dict() for p in pitfalls] + [w.to_dict() for w in warnings]