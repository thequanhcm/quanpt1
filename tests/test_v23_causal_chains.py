"""
Tests for Advanced Causal Chain Discovery Module (V23.1)

Tests cover:
- Causal chain discovery (forward, backward, bidirectional)
- Chain validation
- Counterfactual simulation
- Intervention planning
- Lessons learned extraction
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from quan_ai_brain.memory.causal_chains import (
    CausalLink,
    CausalChain,
    CounterfactualScenario,
    InterventionPlan,
    LessonLearned,
    ChainDirection,
    ChainValidationStatus,
    CausalChainDiscoverer,
    CounterfactualEngine,
    InterventionPlanner,
    LessonsLearnedExtractor
)


class TestCausalLink:
    """Test CausalLink dataclass"""

    def test_create_link(self):
        """Test creating a causal link"""
        link = CausalLink(
            source_id="event_a",
            target_id="event_b",
            link_type="CAUSES",
            confidence=0.85,
            strength=0.7
        )

        assert link.source_id == "event_a"
        assert link.target_id == "event_b"
        assert link.link_type == "CAUSES"
        assert link.confidence == 0.85
        assert link.strength == 0.7

    def test_link_to_dict(self):
        """Test converting link to dictionary"""
        link = CausalLink(
            source_id="a",
            target_id="b",
            link_type="ENABLES",
            confidence=0.9,
            evidence=["evidence1", "evidence2"],
            temporal_delay=3600
        )

        data = link.to_dict()

        assert data['source_id'] == "a"
        assert data['target_id'] == "b"
        assert data['link_type'] == "ENABLES"
        assert data['confidence'] == 0.9
        assert len(data['evidence']) == 2
        assert data['temporal_delay'] == 3600

    def test_link_from_dict(self):
        """Test creating link from dictionary"""
        data = {
            'source_id': "x",
            'target_id': "y",
            'link_type': "INHIBITS",
            'confidence': 0.75,
            'evidence': [],
            'strength': 0.6,
            'temporal_delay': None,
            'metadata': {}
        }

        link = CausalLink.from_dict(data)

        assert link.source_id == "x"
        assert link.target_id == "y"
        assert link.link_type == "INHIBITS"
        assert link.confidence == 0.75


class TestCausalChain:
    """Test CausalChain dataclass"""

    def test_create_chain(self):
        """Test creating a causal chain"""
        link1 = CausalLink("a", "b", "CAUSES", 0.9)
        link2 = CausalLink("b", "c", "CAUSES", 0.8)

        chain = CausalChain(
            chain_id="test_chain",
            events=["a", "b", "c"],
            links=[link1, link2],
            overall_confidence=0.85,
            chain_type="INDIRECT",
            depth=2
        )

        assert chain.chain_id == "test_chain"
        assert len(chain.events) == 3
        assert chain.depth == 2
        assert chain.overall_confidence == 0.85

    def test_chain_validation_valid(self):
        """Test validation of a valid chain"""
        link1 = CausalLink("a", "b", "CAUSES", 0.9, evidence=["e1"])
        link2 = CausalLink("b", "c", "CAUSES", 0.8, evidence=["e2"])

        chain = CausalChain(
            chain_id="valid",
            events=["a", "b", "c"],
            links=[link1, link2],
            overall_confidence=0.85,
            chain_type="INDIRECT",
            depth=2
        )

        status, message = chain.validate()

        assert status == ChainValidationStatus.VALID
        assert message == "Chain is valid"

    def test_chain_validation_circular(self):
        """Test validation detects circular reference"""
        link = CausalLink("a", "b", "CAUSES", 0.9)

        chain = CausalChain(
            chain_id="circular",
            events=["a", "b", "a"],  # Circular
            links=[link, link],
            overall_confidence=0.9,
            chain_type="DIRECT",
            depth=2
        )

        status, message = chain.validate()

        assert status == ChainValidationStatus.CIRCULAR
        assert "Circular" in message

    def test_chain_validation_weak_confidence(self):
        """Test validation detects weak confidence"""
        link = CausalLink("a", "b", "CAUSES", 0.3)

        chain = CausalChain(
            chain_id="weak",
            events=["a", "b"],
            links=[link],
            overall_confidence=0.3,
            chain_type="DIRECT",
            depth=1
        )

        status, message = chain.validate()

        assert status == ChainValidationStatus.WEAK_CONFIDENCE
        assert "Low confidence" in message

    def test_chain_to_dict_and_from_dict(self):
        """Test serialization and deserialization"""
        link = CausalLink("a", "b", "CAUSES", 0.9)
        chain = CausalChain(
            chain_id="test",
            events=["a", "b"],
            links=[link],
            overall_confidence=0.9,
            chain_type="DIRECT",
            depth=1,
            created_at=datetime(2024, 10, 28)
        )

        data = chain.to_dict()
        restored = CausalChain.from_dict(data)

        assert restored.chain_id == chain.chain_id
        assert restored.events == chain.events
        assert restored.overall_confidence == chain.overall_confidence
        assert restored.depth == chain.depth


class TestCounterfactualScenario:
    """Test CounterfactualScenario dataclass"""

    def test_create_scenario(self):
        """Test creating a counterfactual scenario"""
        scenario = CounterfactualScenario(
            scenario_id="cf_001",
            base_event="event_a",
            modification={"break_link": True}
        )

        assert scenario.scenario_id == "cf_001"
        assert scenario.base_event == "event_a"
        assert scenario.modification == {"break_link": True}

    def test_scenario_serialization(self):
        """Test scenario serialization"""
        scenario = CounterfactualScenario(
            scenario_id="cf_002",
            base_event="event_b",
            modification={"modify": "value"},
            alternative_outcome="different_result",
            confidence=0.75
        )

        data = scenario.to_dict()

        assert data['scenario_id'] == "cf_002"
        assert data['alternative_outcome'] == "different_result"
        assert data['confidence'] == 0.75


class TestInterventionPlan:
    """Test InterventionPlan dataclass"""

    def test_create_plan(self):
        """Test creating an intervention plan"""
        plan = InterventionPlan(
            plan_id="int_001",
            goal="prevent_failure",
            interventions=[{"target": "event_a", "action": "modify"}],
            predicted_outcome="success",
            success_probability=0.85
        )

        assert plan.plan_id == "int_001"
        assert plan.goal == "prevent_failure"
        assert plan.success_probability == 0.85

    def test_plan_with_side_effects(self):
        """Test plan with side effects"""
        plan = InterventionPlan(
            plan_id="int_002",
            goal="optimize",
            interventions=[{"target": "x"}],
            predicted_outcome="better",
            success_probability=0.7,
            side_effects=[
                {"effect": "delay", "severity": "low"},
                {"effect": "cost", "severity": "medium"}
            ]
        )

        assert len(plan.side_effects) == 2
        assert plan.side_effects[0]['effect'] == "delay"


class TestLessonLearned:
    """Test LessonLearned dataclass"""

    def test_create_lesson(self):
        """Test creating a lesson learned"""
        lesson = LessonLearned(
            lesson_id="lesson_001",
            event_ids=["event_a", "event_b"],
            cause="event_a",
            effect="event_b",
            lesson_text="A causes B",
            recommendations=["Monitor A", "Prepare for B"],
            confidence=0.9,
            category="TECHNICAL"
        )

        assert lesson.lesson_id == "lesson_001"
        assert lesson.cause == "event_a"
        assert lesson.category == "TECHNICAL"


class TestCausalChainDiscoverer:
    """Test CausalChainDiscoverer class"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = Mock()
        db.get_all_relations = Mock(return_value=[])
        return db

    def test_discoverer_initialization(self, mock_db):
        """Test discoverer initialization"""
        discoverer = CausalChainDiscoverer(mock_db)

        assert discoverer.db == mock_db
        assert discoverer.graph is not None

    def test_discover_chains_empty_graph(self, mock_db):
        """Test chain discovery with empty graph"""
        discoverer = CausalChainDiscoverer(mock_db)

        chains = discoverer.discover_chains("start_event")

        assert len(chains) == 0

    def test_validate_chain(self, mock_db):
        """Test chain validation"""
        discoverer = CausalChainDiscoverer(mock_db)

        link = CausalLink("a", "b", "CAUSES", 0.9, evidence=["e1"])
        chain = CausalChain(
            chain_id="test",
            events=["a", "b"],
            links=[link],
            overall_confidence=0.9,
            chain_type="DIRECT",
            depth=1
        )

        is_valid, message = discoverer.validate_chain(chain)

        assert is_valid is True
        assert message == "Chain is valid"

    def test_get_chain_statistics_empty(self, mock_db):
        """Test statistics with no chains"""
        discoverer = CausalChainDiscoverer(mock_db)

        stats = discoverer.get_chain_statistics()

        assert stats['total_chains'] == 0
        assert stats['avg_depth'] == 0


class TestCounterfactualEngine:
    """Test CounterfactualEngine class"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = Mock()
        return db

    def test_engine_initialization(self, mock_db):
        """Test engine initialization"""
        engine = CounterfactualEngine(mock_db)

        assert engine.db == mock_db
        assert engine.discoverer is not None

    def test_simulate_scenario_no_chains(self, mock_db):
        """Test simulation with no causal chains"""
        engine = CounterfactualEngine(mock_db)

        scenario = CounterfactualScenario(
            scenario_id="test",
            base_event="nonexistent",
            modification={"break": True}
        )

        result = engine.simulate_scenario(scenario)

        assert result.confidence == 0.0
        assert 'error' in result.simulation_results

    def test_analyze_modification_impact(self, mock_db):
        """Test modification impact analysis"""
        engine = CounterfactualEngine(mock_db)

        link = CausalLink("a", "b", "CAUSES", 0.9)
        chain = CausalChain(
            chain_id="test",
            events=["a", "b"],
            links=[link],
            overall_confidence=0.9,
            chain_type="DIRECT",
            depth=1
        )

        impact = engine._analyze_modification_impact(
            {"affects_source": True},
            chain
        )

        assert impact['num_affected'] == 1
        assert impact['confidence'] < chain.overall_confidence


class TestInterventionPlanner:
    """Test InterventionPlanner class"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = Mock()
        return db

    def test_planner_initialization(self, mock_db):
        """Test planner initialization"""
        planner = InterventionPlanner(mock_db)

        assert planner.db == mock_db
        assert planner.discoverer is not None

    def test_plan_interventions_no_chains(self, mock_db):
        """Test planning with no chains"""
        planner = InterventionPlanner(mock_db)

        plans = planner.plan_interventions("unreachable_goal")

        assert len(plans) == 0

    def test_optimize_strategy(self, mock_db):
        """Test strategy optimization"""
        planner = InterventionPlanner(mock_db)

        plan1 = InterventionPlan(
            plan_id="p1",
            goal="test",
            interventions=[],
            predicted_outcome="ok",
            success_probability=0.7,
            side_effects=[]
        )

        plan2 = InterventionPlan(
            plan_id="p2",
            goal="test",
            interventions=[],
            predicted_outcome="ok",
            success_probability=0.9,
            side_effects=[{"effect": "minor"}]
        )

        best = planner.optimize_strategy([plan1, plan2])

        assert best.plan_id == "p2"


class TestLessonsLearnedExtractor:
    """Test LessonsLearnedExtractor class"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = Mock()
        return db

    def test_extractor_initialization(self, mock_db):
        """Test extractor initialization"""
        extractor = LessonsLearnedExtractor(mock_db)

        assert extractor.db == mock_db
        assert extractor.discoverer is not None

    def test_extract_lessons_no_chains(self, mock_db):
        """Test extraction with no chains"""
        extractor = LessonsLearnedExtractor(mock_db)

        lessons = extractor.extract_lessons(["nonexistent"])

        assert len(lessons) == 0

    def test_generate_lesson_text_direct(self, mock_db):
        """Test lesson text generation for direct chain"""
        extractor = LessonsLearnedExtractor(mock_db)

        link = CausalLink("a", "b", "CAUSES", 0.9)
        chain = CausalChain(
            chain_id="test",
            events=["a", "b"],
            links=[link],
            overall_confidence=0.9,
            chain_type="DIRECT",
            depth=1
        )

        text = extractor._generate_lesson_text(chain)

        assert "Direct causal relationship" in text
        assert "a → b" in text

    def test_generate_recommendations_weak_confidence(self, mock_db):
        """Test recommendation generation for weak confidence"""
        extractor = LessonsLearnedExtractor(mock_db)

        link = CausalLink("a", "b", "CAUSES", 0.5)
        chain = CausalChain(
            chain_id="test",
            events=["a", "b"],
            links=[link],
            overall_confidence=0.5,
            chain_type="DIRECT",
            depth=1
        )

        recs = extractor._generate_recommendations(chain)

        assert any("Investigate" in r for r in recs)

    def test_get_lessons_summary_empty(self, mock_db):
        """Test summary with no lessons"""
        extractor = LessonsLearnedExtractor(mock_db)

        summary = extractor.get_lessons_summary()

        assert summary['total'] == 0


class TestChainDirection:
    """Test chain direction enum"""

    def test_direction_values(self):
        """Test direction enum values"""
        assert ChainDirection.FORWARD.value == "forward"
        assert ChainDirection.BACKWARD.value == "backward"
        assert ChainDirection.BOTH.value == "both"


class TestChainValidationStatus:
    """Test validation status enum"""

    def test_status_values(self):
        """Test status enum values"""
        assert ChainValidationStatus.VALID.value == "valid"
        assert ChainValidationStatus.WEAK_CONFIDENCE.value == "weak_confidence"
        assert ChainValidationStatus.CIRCULAR.value == "circular"


class TestIntegration:
    """Integration tests for causal chain module"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = Mock()
        db.get_all_relations = Mock(return_value=[])
        return db

    def test_full_chain_discovery_workflow(self, mock_db):
        """Test complete chain discovery workflow"""
        discoverer = CausalChainDiscoverer(mock_db)

        # Discover chains
        chains = discoverer.discover_chains(
            "start",
            direction=ChainDirection.FORWARD,
            max_depth=3,
            min_confidence=0.5
        )

        # Should return empty list for empty graph
        assert isinstance(chains, list)

        # Get statistics
        stats = discoverer.get_chain_statistics()
        assert 'total_chains' in stats

    def test_counterfactual_workflow(self, mock_db):
        """Test complete counterfactual workflow"""
        engine = CounterfactualEngine(mock_db)

        scenario = CounterfactualScenario(
            scenario_id="workflow_test",
            base_event="event_x",
            modification={"change": "value"}
        )

        result = engine.simulate_scenario(scenario)

        assert result.scenario_id == "workflow_test"
        assert 'simulation_results' in result.to_dict()

    def test_intervention_workflow(self, mock_db):
        """Test complete intervention planning workflow"""
        planner = InterventionPlanner(mock_db)

        plans = planner.plan_interventions("achieve_success")

        assert isinstance(plans, list)

        if plans:
            best = planner.optimize_strategy(plans)
            assert best is not None

    def test_lessons_extraction_workflow(self, mock_db):
        """Test complete lessons extraction workflow"""
        extractor = LessonsLearnedExtractor(mock_db)

        lessons = extractor.extract_lessons(["event_1", "event_2"])

        assert isinstance(lessons, list)

        summary = extractor.get_lessons_summary()
        assert 'total' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])