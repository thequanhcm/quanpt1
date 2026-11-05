"""V17 tests — Causal Reasoning & Counterfactual Memory (20 tests)."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from quan_ai_brain.memory.causal_reasoning import CausalGraph
from quan_ai_brain.memory.counterfactual_memory import CounterfactualMemory, CounterfactualScenario


@pytest.fixture
def causal_db():
    """Create temporary causal graph database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_v17_causal.db"


@pytest.fixture
def counterfactual_db():
    """Create temporary counterfactual database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_v17_counterfactual.db"


class TestCausalGraph:
    """Tests for causal graph."""
    
    def test_add_causal_event(self, causal_db):
        """Add causal event."""
        graph = CausalGraph(str(causal_db))
        result = graph.add_causal_event("event1", "cause", "Initial event", "2024-01-01T00:00:00Z")
        assert result is True
        assert "event1" in graph._nodes
        assert graph._nodes["event1"].event_type == "cause"
        graph.close()
    
    def test_add_causal_link(self, causal_db):
        """Add causal link."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("cause1", "cause", "Cause event", "2024-01-01T00:00:00Z")
        graph.add_causal_event("effect1", "effect", "Effect event", "2024-01-02T00:00:00Z")
        
        result = graph.add_causal_link("cause1", "effect1", "direct", 0.8)
        assert result is True
        assert len(graph._edges) == 1
        graph.close()
    
    def test_find_causes(self, causal_db):
        """Find causes of an event."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("cause1", "cause", "Root cause", "2024-01-01T00:00:00Z")
        graph.add_causal_event("cause2", "cause", "Intermediate", "2024-01-01T12:00:00Z")
        graph.add_causal_event("effect1", "effect", "Final effect", "2024-01-02T00:00:00Z")
        
        graph.add_causal_link("cause1", "cause2", "direct", 0.9)
        graph.add_causal_link("cause2", "effect1", "direct", 0.8)
        
        causes = graph.find_causes("effect1", depth=2)
        assert len(causes) >= 2
        assert any(c['event_id'] == 'cause1' for c in causes)
        graph.close()
    
    def test_find_effects(self, causal_db):
        """Find effects of an event."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("cause1", "cause", "Root cause", "2024-01-01T00:00:00Z")
        graph.add_causal_event("effect1", "effect", "Effect 1", "2024-01-02T00:00:00Z")
        graph.add_causal_event("effect2", "effect", "Effect 2", "2024-01-03T00:00:00Z")
        
        graph.add_causal_link("cause1", "effect1", "direct", 0.8)
        graph.add_causal_link("effect1", "effect2", "indirect", 0.6)
        
        effects = graph.find_effects("cause1", depth=2)
        assert len(effects) >= 2
        graph.close()
    
    def test_find_causal_chain(self, causal_db):
        """Find causal chain between events."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("e1", "cause", "Event 1", "2024-01-01T00:00:00Z")
        graph.add_causal_event("e2", "event", "Event 2", "2024-01-02T00:00:00Z")
        graph.add_causal_event("e3", "effect", "Event 3", "2024-01-03T00:00:00Z")
        graph.add_causal_link("e1", "e2", "direct", 0.9)
        graph.add_causal_link("e2", "e3", "direct", 0.8)

        chain = graph.find_causal_chain("e1", "e3")
        assert chain is not None
        assert chain.chain == ["e1", "e2", "e3"]
        assert 0 < chain.total_strength <= 0.9 * 0.8 + 1e-9
        # Không có đường đi → None
        graph.add_causal_event("lone", "event", "Isolated", "2024-01-04T00:00:00Z")
        assert graph.find_causal_chain("e1", "lone") is None
        # Event không tồn tại → None
        assert graph.find_causal_chain("e1", "ghost") is None
        graph.close()
    
    def test_infer_causality(self, causal_db):
        """Infer causal relationship."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("event1", "cause", "Event 1", "2024-01-01T00:00:00Z")
        graph.add_causal_event("event2", "effect", "Event 2", "2024-01-02T00:00:00Z")
        
        inference = graph.infer_causality("event1", "event2")
        assert inference['causality'] in ['causal', 'possible', 'uncertain', 'reverse_causal']
        assert 'strength' in inference
        assert 'evidence' in inference
        graph.close()
    
    def test_identify_root_cause(self, causal_db):
        """Identify root cause."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("root", "cause", "Root cause", "2024-01-01T00:00:00Z")
        graph.add_causal_event("intermediate", "event", "Intermediate", "2024-01-02T00:00:00Z")
        graph.add_causal_event("final", "effect", "Final effect", "2024-01-03T00:00:00Z")
        
        graph.add_causal_link("root", "intermediate", "direct", 0.9)
        graph.add_causal_link("intermediate", "final", "direct", 0.8)
        
        root_cause = graph.identify_root_cause("final")
        assert root_cause is not None
        assert root_cause['root_cause_id'] == 'root'
        graph.close()
    
    def test_predict_effects(self, causal_db):
        """Predict effects of a cause."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("cause1", "cause", "Cause", "2024-01-01T00:00:00Z")
        graph.add_causal_event("effect1", "effect", "Effect 1", "2024-01-02T00:00:00Z")
        graph.add_causal_event("effect2", "effect", "Effect 2", "2024-01-03T00:00:00Z")
        
        graph.add_causal_link("cause1", "effect1", "direct", 0.8)
        graph.add_causal_link("cause1", "effect2", "indirect", 0.6)
        
        effects = graph.predict_effects("cause1")
        assert len(effects) >= 2
        graph.close()
    
    def test_find_common_patterns(self, causal_db):
        """Find common causal patterns."""
        graph = CausalGraph(str(causal_db))
        
        # Create multiple direct links
        for i in range(3):
            graph.add_causal_event(f"cause{i}", "cause", f"Cause {i}", "2024-01-01T00:00:00Z")
            graph.add_causal_event(f"effect{i}", "effect", f"Effect {i}", "2024-01-02T00:00:00Z")
            graph.add_causal_link(f"cause{i}", f"effect{i}", "direct", 0.8)
        
        patterns = graph.find_common_causal_patterns(min_frequency=2)
        assert len(patterns) >= 1
        assert any(p['pattern_type'] == 'direct' for p in patterns)
        graph.close()
    
    def test_find_confounding_factors(self, causal_db):
        """Find confounding factors."""
        graph = CausalGraph(str(causal_db))
        graph.add_causal_event("confounder", "cause", "Confounder", "2024-01-01T00:00:00Z")
        graph.add_causal_event("cause1", "cause", "Cause", "2024-01-01T12:00:00Z")
        graph.add_causal_event("effect1", "effect", "Effect", "2024-01-02T00:00:00Z")
        
        graph.add_causal_link("confounder", "cause1", "contributory", 0.5)
        graph.add_causal_link("confounder", "effect1", "contributory", 0.6)
        graph.add_causal_link("cause1", "effect1", "direct", 0.8)
        
        confounders = graph.find_confounding_factors("cause1", "effect1")
        assert "confounder" in confounders
        graph.close()


class TestCounterfactualMemory:
    """Tests for counterfactual memory."""
    
    def test_add_counterfactual(self, counterfactual_db):
        """Add counterfactual scenario."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        scenario = CounterfactualScenario(
            scenario_id="cf1",
            base_event_id="event1",
            alternative_action="Take different action",
            predicted_outcome={"success": True, "value": 100},
            actual_outcome=None,
            confidence=0.8
        )
        
        result = memory.add_counterfactual(scenario)
        assert result is True
        
        scenarios = memory.get_counterfactuals("event1")
        assert len(scenarios) == 1
        assert scenarios[0].scenario_id == "cf1"
        memory.close()
    
    def test_get_counterfactuals(self, counterfactual_db):
        """Get counterfactuals for base event."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf1", base_event_id="event1", alternative_action="Action A",
            predicted_outcome={}, actual_outcome=None, confidence=0.8
        ))
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf2", base_event_id="event1", alternative_action="Action B",
            predicted_outcome={}, actual_outcome=None, confidence=0.7
        ))
        
        scenarios = memory.get_counterfactuals("event1")
        assert len(scenarios) == 2
        memory.close()
    
    def test_update_counterfactual(self, counterfactual_db):
        """Update counterfactual with actual outcome."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        scenario = CounterfactualScenario(
            scenario_id="cf1", base_event_id="event1", alternative_action="Action A",
            predicted_outcome={"value": 100}, actual_outcome=None, confidence=0.8
        )
        memory.add_counterfactual(scenario)
        
        updated = memory.update_counterfactual(
            "cf1",
            actual_outcome={"value": 80},
            outcome_difference={"value": -20}
        )
        
        assert updated is not None
        assert updated.actual_outcome == {"value": 80}
        assert updated.outcome_difference == {"value": -20}
        memory.close()
    
    def test_generate_counterfactuals(self, counterfactual_db):
        """Generate counterfactual scenarios."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        actions = ["Action A", "Action B", "Action C"]
        scenarios = memory.generate_counterfactuals("event1", actions)
        
        assert len(scenarios) == 3
        assert all(s.base_event_id == "event1" for s in scenarios)
        memory.close()
    
    def test_evaluate_counterfactual(self, counterfactual_db):
        """Evaluate counterfactual plausibility."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        scenario = CounterfactualScenario(
            scenario_id="cf1", base_event_id="event1", alternative_action="Action A",
            predicted_outcome={"value": 100}, actual_outcome=None, confidence=0.8
        )
        memory.add_counterfactual(scenario)
        
        evaluation = memory.evaluate_counterfactual("cf1")
        assert evaluation['plausibility'] > 0
        assert evaluation['confidence'] == 0.8
        memory.close()
    
    def test_compare_outcomes(self, counterfactual_db):
        """Compare actual vs predicted outcomes."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        scenario = CounterfactualScenario(
            scenario_id="cf1", base_event_id="event1", alternative_action="Action A",
            predicted_outcome={"value": 100}, actual_outcome={"value": 80},
            confidence=0.8, outcome_difference={"value": -20}
        )
        memory.add_counterfactual(scenario)
        
        comparison = memory.compare_outcomes("cf1")
        assert comparison is not None
        assert comparison['predicted'] == {"value": 100}
        assert comparison['actual'] == {"value": 80}
        memory.close()
    
    def test_learn_from_counterfactual(self, counterfactual_db):
        """Learn from counterfactual scenario."""
        memory = CounterfactualMemory(str(counterfactual_db))

        # Chưa có actual outcome → không thể học (fail-honest)
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf_p", base_event_id="event1", alternative_action="Action A",
            predicted_outcome={"value": 100}, actual_outcome=None, confidence=0.8
        ))
        assert memory.learn_from_counterfactual("cf_p") is None

        # Có actual outcome (kém hơn dự đoán) → sinh lesson
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf1", base_event_id="event2", alternative_action="Action B",
            predicted_outcome={"value": 100}, actual_outcome={"value": 60},
            confidence=0.8, outcome_difference={"value": -40}
        ))
        lesson = memory.learn_from_counterfactual("cf1")
        assert lesson is not None
        assert lesson.scenario_ids == ["cf1"] or "cf1" in lesson.scenario_ids
        assert lesson.insight
        assert 0.0 < lesson.confidence <= 1.0
        memory.close()
    
    def test_find_similar_scenarios(self, counterfactual_db):
        """Find similar scenarios."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf1", base_event_id="event1", alternative_action="Action A",
            predicted_outcome={}, actual_outcome=None, confidence=0.8
        ))
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf2", base_event_id="event2", alternative_action="Action B",
            predicted_outcome={}, actual_outcome=None, confidence=0.7
        ))
        
        current = CounterfactualScenario(
            scenario_id="cf3", base_event_id="event3", alternative_action="Action C",
            predicted_outcome={}, actual_outcome=None, confidence=0.6
        )
        
        similar = memory.find_similar_scenarios(current)
        assert len(similar) >= 1
        memory.close()
    
    def test_calculate_opportunity_cost(self, counterfactual_db):
        """Calculate opportunity cost."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        actual = {"revenue": 100, "cost": 50}
        alternative = {"revenue": 120, "cost": 45}
        
        cost = memory.calculate_opportunity_cost("Action A", "Action B", actual, alternative)
        
        assert 'cost_by_metric' in cost
        assert 'total_opportunity_cost' in cost
        assert cost['total_opportunity_cost'] > 0  # Missed opportunity
        memory.close()
    
    def test_identify_missed_opportunities(self, counterfactual_db):
        """Identify missed opportunities."""
        memory = CounterfactualMemory(str(counterfactual_db))
        
        scenario = CounterfactualScenario(
            scenario_id="cf1", base_event_id="event1", alternative_action="Better action",
            predicted_outcome={"value": 100}, actual_outcome={"value": 50},
            confidence=0.8, outcome_difference={"value": -50}
        )
        memory.add_counterfactual(scenario)
        
        missed = memory.identify_missed_opportunities(min_threshold=0.3)
        assert len(missed) >= 1
        assert missed[0]['scenario_id'] == "cf1"
        memory.close()
    
    def test_generate_lessons_learned(self, counterfactual_db):
        """Generate lessons learned."""
        memory = CounterfactualMemory(str(counterfactual_db))

        # Không có scenario nào có actual outcome → 0 lesson
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf_p", base_event_id="event1", alternative_action="Action A",
            predicted_outcome={}, actual_outcome=None, confidence=0.8
        ))
        assert memory.generate_lessons_learned() == []

        # 2 scenario có actual outcome → sinh >= 1 lesson
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf1", base_event_id="event2", alternative_action="Action B",
            predicted_outcome={"value": 100}, actual_outcome={"value": 80},
            confidence=0.8, outcome_difference={"value": -20}
        ))
        memory.add_counterfactual(CounterfactualScenario(
            scenario_id="cf2", base_event_id="event3", alternative_action="Action C",
            predicted_outcome={"value": 50}, actual_outcome={"value": 70},
            confidence=0.7, outcome_difference={"value": 20}
        ))
        lessons = memory.generate_lessons_learned()
        assert len(lessons) >= 1
        assert all(l.insight for l in lessons)
        memory.close()
    
    def test_get_all_lessons(self, counterfactual_db):
        """Get all lessons learned."""
        memory = CounterfactualMemory(str(counterfactual_db))

        # Ban đầu chưa có lesson nào
        assert memory.get_all_lessons() == []

        # Sinh lesson từ 2 scenario có actual outcome
        for sid, alt, diff in [("cf1", "Action A", {"value": -30}),
                               ("cf2", "Action B", {"cost": 15})]:
            memory.add_counterfactual(CounterfactualScenario(
                scenario_id=sid, base_event_id=f"event_{sid}", alternative_action=alt,
                predicted_outcome={"value": 100}, actual_outcome={"value": 70},
                confidence=0.8, outcome_difference=diff
            ))
            memory.learn_from_counterfactual(sid)

        lessons = memory.get_all_lessons()
        assert len(lessons) >= 2
        # Mỗi lesson đầy đủ trường + sắp xếp created_at DESC
        created = [l.created_at for l in lessons]
        assert created == sorted(created, reverse=True)
        assert all(l.lesson_id and l.insight and l.recommendation for l in lessons)
        memory.close()