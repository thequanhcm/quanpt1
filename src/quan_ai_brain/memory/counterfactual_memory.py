"""V17 — Counterfactual Memory & What-If Analysis.

Ghi nhớ và phân tích các kịch bản "what-if" (counterfactual scenarios).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CounterfactualScenario:
    """Counterfactual scenario."""
    scenario_id: str
    base_event_id: str
    alternative_action: str
    predicted_outcome: dict[str, Any]
    actual_outcome: dict[str, Any] | None = None
    confidence: float = 0.7
    outcome_difference: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None


@dataclass
class LessonLearned:
    """Lesson learned from counterfactual analysis."""
    lesson_id: str
    scenario_ids: list[str]
    insight: str
    recommendation: str
    confidence: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CounterfactualMemory:
    """Counterfactual memory storage and reasoning."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()
    
    def _create_schema(self):
        """Create counterfactual schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS counterfactual_scenarios (
                scenario_id TEXT PRIMARY KEY,
                base_event_id TEXT NOT NULL,
                alternative_action TEXT NOT NULL,
                predicted_outcome TEXT NOT NULL,
                actual_outcome TEXT,
                confidence REAL NOT NULL,
                outcome_difference TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS lessons_learned (
                lesson_id TEXT PRIMARY KEY,
                scenario_ids TEXT NOT NULL,
                insight TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_scenarios_base ON counterfactual_scenarios(base_event_id);
            CREATE INDEX IF NOT EXISTS idx_scenarios_confidence ON counterfactual_scenarios(confidence);
        """)
        self._conn.commit()
    
    def add_counterfactual(self, scenario: CounterfactualScenario) -> bool:
        """Add counterfactual scenario."""
        try:
            self._conn.execute(
                """INSERT INTO counterfactual_scenarios 
                   (scenario_id, base_event_id, alternative_action, predicted_outcome, 
                    actual_outcome, confidence, outcome_difference, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scenario.scenario_id,
                    scenario.base_event_id,
                    scenario.alternative_action,
                    json.dumps(scenario.predicted_outcome),
                    json.dumps(scenario.actual_outcome) if scenario.actual_outcome else None,
                    scenario.confidence,
                    json.dumps(scenario.outcome_difference) if scenario.outcome_difference else None,
                    scenario.created_at,
                    scenario.updated_at
                )
            )
            self._conn.commit()
            return True
        except Exception:
            return False
    
    def get_counterfactuals(self, base_event_id: str) -> list[CounterfactualScenario]:
        """Get counterfactuals for a base event."""
        rows = self._conn.execute(
            """SELECT scenario_id, base_event_id, alternative_action, predicted_outcome, 
                      actual_outcome, confidence, outcome_difference, created_at, updated_at
               FROM counterfactual_scenarios 
               WHERE base_event_id = ?
               ORDER BY confidence DESC""",
            (base_event_id,)
        ).fetchall()
        
        scenarios = []
        for row in rows:
            scenarios.append(CounterfactualScenario(
                scenario_id=row[0],
                base_event_id=row[1],
                alternative_action=row[2],
                predicted_outcome=json.loads(row[3]),
                actual_outcome=json.loads(row[4]) if row[4] else None,
                confidence=row[5],
                outcome_difference=json.loads(row[6]) if row[6] else None,
                created_at=row[7],
                updated_at=row[8]
            ))
        
        return scenarios
    
    def update_counterfactual(self, scenario_id: str, actual_outcome: dict[str, Any],
                             outcome_difference: dict[str, Any] | None = None) -> CounterfactualScenario | None:
        """Update counterfactual with actual outcome."""
        row = self._conn.execute(
            "SELECT scenario_id, base_event_id, alternative_action, predicted_outcome, "
            "actual_outcome, confidence, outcome_difference, created_at, updated_at "
            "FROM counterfactual_scenarios WHERE scenario_id = ?",
            (scenario_id,)
        ).fetchone()
        
        if not row:
            return None
        
        scenario = CounterfactualScenario(
            scenario_id=row[0],
            base_event_id=row[1],
            alternative_action=row[2],
            predicted_outcome=json.loads(row[3]),
            actual_outcome=actual_outcome,
            confidence=row[5],
            outcome_difference=outcome_difference or {},
            created_at=row[7],
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
        self._conn.execute(
            """UPDATE counterfactual_scenarios 
               SET actual_outcome = ?, outcome_difference = ?, updated_at = ?
               WHERE scenario_id = ?""",
            (json.dumps(actual_outcome), json.dumps(outcome_difference or {}), 
             scenario.updated_at, scenario_id)
        )
        self._conn.commit()
        
        return scenario
    
    def generate_counterfactuals(self, base_event_id: str, 
                                 alternative_actions: list[str]) -> list[CounterfactualScenario]:
        """Generate counterfactual scenarios from alternative actions."""
        scenarios = []
        
        for i, action in enumerate(alternative_actions):
            scenario_id = f"cf_{base_event_id}_{i}"
            
            # Generate predicted outcome (placeholder - would use causal model)
            predicted_outcome = {
                'action': action,
                'confidence': 0.7,
                'notes': f"Predicted outcome if {action} was taken"
            }
            
            scenario = CounterfactualScenario(
                scenario_id=scenario_id,
                base_event_id=base_event_id,
                alternative_action=action,
                predicted_outcome=predicted_outcome,
                actual_outcome=None,
                confidence=0.7
            )
            
            scenarios.append(scenario)
            self.add_counterfactual(scenario)
        
        return scenarios
    
    def evaluate_counterfactual(self, scenario_id: str) -> dict:
        """Evaluate counterfactual scenario plausibility."""
        scenario = None
        row = self._conn.execute(
            "SELECT scenario_id, base_event_id, alternative_action, predicted_outcome, "
            "actual_outcome, confidence, outcome_difference, created_at, updated_at "
            "FROM counterfactual_scenarios WHERE scenario_id = ?",
            (scenario_id,)
        ).fetchone()
        
        if row:
            scenario = CounterfactualScenario(
                scenario_id=row[0],
                base_event_id=row[1],
                alternative_action=row[2],
                predicted_outcome=json.loads(row[3]),
                actual_outcome=json.loads(row[4]) if row[4] else None,
                confidence=row[5],
                outcome_difference=json.loads(row[6]) if row[6] else None,
                created_at=row[7],
                updated_at=row[8]
            )
        
        if not scenario:
            return {'plausibility': 0.0, 'confidence': 0.0, 'notes': 'Scenario not found'}
        
        # Calculate plausibility
        plausibility = scenario.confidence
        
        # If we have actual outcome, adjust plausibility
        if scenario.actual_outcome:
            # Compare predicted vs actual
            if scenario.outcome_difference:
                # Higher difference = lower plausibility
                diff_score = sum(abs(v) for v in scenario.outcome_difference.values() if isinstance(v, (int, float)))
                plausibility = max(0, plausibility - diff_score * 0.1)
        
        return {
            'plausibility': plausibility,
            'confidence': scenario.confidence,
            'has_actual_outcome': scenario.actual_outcome is not None,
            'notes': 'Evaluated successfully'
        }
    
    def compare_outcomes(self, scenario_id: str) -> dict | None:
        """Compare actual vs predicted outcomes."""
        scenario = None
        row = self._conn.execute(
            "SELECT scenario_id, predicted_outcome, actual_outcome, outcome_difference "
            "FROM counterfactual_scenarios WHERE scenario_id = ?",
            (scenario_id,)
        ).fetchone()
        
        if not row:
            return None
        
        predicted = json.loads(row[1])
        actual = json.loads(row[2]) if row[2] else None
        difference = json.loads(row[3]) if row[3] else None
        
        return {
            'scenario_id': row[0],
            'predicted': predicted,
            'actual': actual,
            'difference': difference,
            'accuracy': 1.0 - (sum(abs(v) for v in (difference or {}).values() if isinstance(v, (int, float)))) if difference else None
        }
    
    def learn_from_counterfactual(self, scenario_id: str) -> LessonLearned | None:
        """Learn from a counterfactual scenario."""
        scenario = None
        row = self._conn.execute(
            "SELECT scenario_id, base_event_id, alternative_action, predicted_outcome, "
            "actual_outcome, confidence, outcome_difference "
            "FROM counterfactual_scenarios WHERE scenario_id = ?",
            (scenario_id,)
        ).fetchone()
        
        if not row:
            return None
        
        predicted = json.loads(row[3])
        actual = json.loads(row[4]) if row[4] else None
        difference = json.loads(row[5]) if row[5] else None
        
        if not actual:
            return None  # Can't learn without actual outcome
        
        # Generate insight
        if difference:
            positive_diff = sum(1 for v in difference.values() if isinstance(v, (int, float)) and v > 0)
            negative_diff = sum(1 for v in difference.values() if isinstance(v, (int, float)) and v < 0)
            
            if positive_diff > negative_diff:
                insight = f"Alternative action '{row[2]}' would have yielded better outcomes"
                recommendation = f"Consider {row[2]} in similar situations"
            elif negative_diff > positive_diff:
                insight = f"Current action was better than alternative '{row[2]}'"
                recommendation = f"Continue with current approach, avoid {row[2]}"
            else:
                insight = f"Alternative action '{row[2]}' had similar outcomes"
                recommendation = f"Both approaches are viable, choose based on other factors"
        else:
            insight = f"Insufficient data to compare outcomes"
            recommendation = "Collect more data before making recommendations"
        
        lesson = LessonLearned(
            lesson_id=f"lesson_{scenario_id}",
            scenario_ids=[scenario_id],
            insight=insight,
            recommendation=recommendation,
            confidence=scenario.confidence if scenario else 0.5
        )
        
        # Save lesson
        self._conn.execute(
            """INSERT INTO lessons_learned (lesson_id, scenario_ids, insight, recommendation, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (lesson.lesson_id, json.dumps(lesson.scenario_ids), lesson.insight, 
             lesson.recommendation, lesson.confidence, lesson.created_at)
        )
        self._conn.commit()
        
        return lesson
    
    def find_similar_scenarios(self, current_scenario: CounterfactualScenario) -> list[CounterfactualScenario]:
        """Find similar counterfactual scenarios."""
        # Simple similarity based on base event type and action
        rows = self._conn.execute(
            """SELECT scenario_id, base_event_id, alternative_action, predicted_outcome, 
                      actual_outcome, confidence, outcome_difference, created_at, updated_at
               FROM counterfactual_scenarios 
               WHERE base_event_id != ?
               ORDER BY confidence DESC
               LIMIT 10""",
            (current_scenario.base_event_id,)
        ).fetchall()
        
        scenarios = []
        for row in rows:
            scenarios.append(CounterfactualScenario(
                scenario_id=row[0],
                base_event_id=row[1],
                alternative_action=row[2],
                predicted_outcome=json.loads(row[3]),
                actual_outcome=json.loads(row[4]) if row[4] else None,
                confidence=row[5],
                outcome_difference=json.loads(row[6]) if row[6] else None,
                created_at=row[7],
                updated_at=row[8]
            ))
        
        return scenarios
    
    def calculate_opportunity_cost(self, actual_action: str, alternative_action: str,
                                  actual_outcome: dict, alternative_outcome: dict) -> dict:
        """Calculate opportunity cost of choosing one action over another."""
        # Simple calculation based on outcome differences
        cost = {}
        
        for key in set(actual_outcome.keys()) | set(alternative_outcome.keys()):
            actual_val = actual_outcome.get(key, 0)
            alt_val = alternative_outcome.get(key, 0)
            
            if isinstance(actual_val, (int, float)) and isinstance(alt_val, (int, float)):
                cost[key] = alt_val - actual_val  # Positive = missed opportunity
        
        total_cost = sum(abs(v) for v in cost.values() if isinstance(v, (int, float)))
        
        return {
            'actual_action': actual_action,
            'alternative_action': alternative_action,
            'cost_by_metric': cost,
            'total_opportunity_cost': total_cost,
            'recommendation': 'Consider alternative' if total_cost > 0.5 else 'Current choice was reasonable'
        }
    
    def identify_missed_opportunities(self, min_threshold: float = 0.3) -> list[dict]:
        """Identify missed opportunities from counterfactuals."""
        rows = self._conn.execute(
            """SELECT scenario_id, base_event_id, alternative_action, predicted_outcome, 
                      actual_outcome, outcome_difference
               FROM counterfactual_scenarios 
               WHERE actual_outcome IS NOT NULL AND outcome_difference IS NOT NULL""",
        ).fetchall()
        
        missed = []
        for row in rows:
            outcome_diff = json.loads(row[5]) if row[5] else {}
            total_diff = sum(abs(v) for v in outcome_diff.values() if isinstance(v, (int, float)))
            
            if total_diff >= min_threshold:
                missed.append({
                    'scenario_id': row[0],
                    'base_event_id': row[1],
                    'alternative_action': row[2],
                    'outcome_difference': outcome_diff,
                    'missed_opportunity_score': total_diff
                })
        
        return sorted(missed, key=lambda x: x['missed_opportunity_score'], reverse=True)
    
    def generate_lessons_learned(self) -> list[LessonLearned]:
        """Generate lessons learned from all counterfactuals with actual outcomes."""
        rows = self._conn.execute(
            """SELECT scenario_id, base_event_id, alternative_action, predicted_outcome, 
                      actual_outcome, outcome_difference, confidence
               FROM counterfactual_scenarios 
               WHERE actual_outcome IS NOT NULL"""
        ).fetchall()
        
        lessons = []
        for row in rows:
            predicted = json.loads(row[3])
            actual = json.loads(row[4]) if row[4] else {}
            difference = json.loads(row[5]) if row[5] else {}
            
            # Generate insight
            if difference:
                positive = sum(1 for v in difference.values() if isinstance(v, (int, float)) and v > 0)
                negative = sum(1 for v in difference.values() if isinstance(v, (int, float)) and v < 0)
                
                if positive > negative:
                    insight = f"Alternative '{row[2]}' would have been better"
                    recommendation = f"Consider {row[2]} in future"
                elif negative > positive:
                    insight = f"Current action was better than '{row[2]}'"
                    recommendation = f"Continue current approach"
                else:
                    insight = f"Both actions had similar outcomes"
                    recommendation = f"Either approach is viable"
            else:
                insight = "Insufficient data"
                recommendation = "Collect more data"
            
            lesson = LessonLearned(
                lesson_id=f"lesson_{row[0]}",
                scenario_ids=[row[0]],
                insight=insight,
                recommendation=recommendation,
                confidence=row[6]
            )
            lessons.append(lesson)
        
        return lessons
    
    def get_all_lessons(self) -> list[LessonLearned]:
        """Get all lessons learned."""
        rows = self._conn.execute(
            "SELECT lesson_id, scenario_ids, insight, recommendation, confidence, created_at "
            "FROM lessons_learned ORDER BY created_at DESC"
        ).fetchall()
        
        lessons = []
        for row in rows:
            lessons.append(LessonLearned(
                lesson_id=row[0],
                scenario_ids=json.loads(row[1]),
                insight=row[2],
                recommendation=row[3],
                confidence=row[4],
                created_at=row[5]
            ))
        
        return lessons
    
    def close(self):
        """Close database connection."""
        self._conn.close()