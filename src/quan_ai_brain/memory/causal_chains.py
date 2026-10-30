"""
Advanced Causal Chain Discovery Module

This module implements advanced causal reasoning capabilities including:
- Causal chain discovery (A → B → C → D)
- Counterfactual analysis and simulation
- Intervention planning
- Lessons learned extraction

Version: V23.1
Author: QUAN AI BRAIN Team
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import json

from quan_ai_brain.memory.deep_memory import DeepMemoryStore
from quan_ai_brain.cognition.causal_reasoning import CausalGraph, CausalInferenceEngine

logger = logging.getLogger(__name__)


class ChainDirection(Enum):
    """Direction of causal chain traversal"""
    FORWARD = "forward"  # Causes → Effects
    BACKWARD = "backward"  # Effects → Causes
    BOTH = "both"  # Bidirectional


class ChainValidationStatus(Enum):
    """Validation status for causal chains"""
    VALID = "valid"
    WEAK_CONFIDENCE = "weak_confidence"
    MISSING_LINKS = "missing_links"
    CIRCULAR = "circular"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class CausalLink:
    """Represents a single causal link between two events"""
    source_id: str
    target_id: str
    link_type: str  # CAUSES, ENABLES, INHIBITS, CORRELATES
    confidence: float  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    strength: float = 0.0  # Causal strength (0-1)
    temporal_delay: Optional[float] = None  # Delay in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'link_type': self.link_type,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'strength': self.strength,
            'temporal_delay': self.temporal_delay,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CausalLink':
        return cls(
            source_id=data['source_id'],
            target_id=data['target_id'],
            link_type=data['link_type'],
            confidence=data['confidence'],
            evidence=data.get('evidence', []),
            strength=data.get('strength', 0.0),
            temporal_delay=data.get('temporal_delay'),
            metadata=data.get('metadata', {})
        )


@dataclass
class CausalChain:
    """Represents a causal chain of events"""
    chain_id: str
    events: List[str]  # Ordered list of event IDs
    links: List[CausalLink]
    overall_confidence: float
    chain_type: str  # DIRECT, INDIRECT, COMPLEX
    depth: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chain_id': self.chain_id,
            'events': self.events,
            'links': [link.to_dict() for link in self.links],
            'overall_confidence': self.overall_confidence,
            'chain_type': self.chain_type,
            'depth': self.depth,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CausalChain':
        return cls(
            chain_id=data['chain_id'],
            events=data['events'],
            links=[CausalLink.from_dict(l) for l in data['links']],
            overall_confidence=data['overall_confidence'],
            chain_type=data['chain_type'],
            depth=data['depth'],
            created_at=datetime.fromisoformat(data['created_at']),
            metadata=data.get('metadata', {})
        )

    def validate(self) -> Tuple[ChainValidationStatus, str]:
        """Validate the causal chain"""
        # Check for circular references
        if len(self.events) != len(set(self.events)):
            return ChainValidationStatus.CIRCULAR, "Circular reference detected"

        # Check confidence threshold
        if self.overall_confidence < 0.5:
            return ChainValidationStatus.WEAK_CONFIDENCE, f"Low confidence: {self.overall_confidence}"

        # Check link completeness
        expected_links = len(self.events) - 1
        if len(self.links) != expected_links:
            return ChainValidationStatus.MISSING_LINKS, f"Missing links: {expected_links - len(self.links)}"

        # Check for sufficient evidence
        total_evidence = sum(len(link.evidence) for link in self.links)
        if total_evidence < len(self.links):
            return ChainValidationStatus.INSUFFICIENT_EVIDENCE, "Insufficient evidence for some links"

        return ChainValidationStatus.VALID, "Chain is valid"


@dataclass
class CounterfactualScenario:
    """Represents a what-if counterfactual scenario"""
    scenario_id: str
    base_event: str
    modification: Dict[str, Any]  # What changed
    alternative_outcome: Optional[str] = None
    confidence: float = 0.0
    simulation_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_id': self.scenario_id,
            'base_event': self.base_event,
            'modification': self.modification,
            'alternative_outcome': self.alternative_outcome,
            'confidence': self.confidence,
            'simulation_results': self.simulation_results,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class InterventionPlan:
    """Represents a plan to intervene in a causal chain"""
    plan_id: str
    goal: str
    interventions: List[Dict[str, Any]]
    predicted_outcome: str
    success_probability: float
    side_effects: List[Dict[str, Any]] = field(default_factory=list)
    cost_estimate: Optional[float] = None
    timeline: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan_id': self.plan_id,
            'goal': self.goal,
            'interventions': self.interventions,
            'predicted_outcome': self.predicted_outcome,
            'success_probability': self.success_probability,
            'side_effects': self.side_effects,
            'cost_estimate': self.cost_estimate,
            'timeline': self.timeline
        }


@dataclass
class LessonLearned:
    """Represents a lesson learned from events"""
    lesson_id: str
    event_ids: List[str]
    cause: str
    effect: str
    lesson_text: str
    recommendations: List[str]
    confidence: float
    category: str  # TECHNICAL, PROCESS, HUMAN, SYSTEM
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'lesson_id': self.lesson_id,
            'event_ids': self.event_ids,
            'cause': self.cause,
            'effect': self.effect,
            'lesson_text': self.lesson_text,
            'recommendations': self.recommendations,
            'confidence': self.confidence,
            'category': self.category,
            'created_at': self.created_at.isoformat()
        }


class CausalChainDiscoverer:
    """Discovers and analyzes causal chains from knowledge base"""

    def __init__(self, db: DeepMemoryStore):
        self.db = db
        self.graph = CausalGraph()
        self.inference_engine = CausalInferenceEngine(db)
        self._load_causal_relations()

    def _load_causal_relations(self) -> None:
        """Load all causal relations from database"""
        try:
            relations = self.db.get_all_relations()
            for rel in relations:
                if rel.relation_type in ['CAUSES', 'ENABLES', 'INHIBITS', 'LEADS_TO']:
                    self.graph.add_edge(
                        rel.source_ku_id,
                        rel.target_ku_id,
                        rel.relation_type,
                        rel.confidence
                    )
            logger.info(f"Loaded {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
        except Exception as e:
            logger.error(f"Error loading causal relations: {e}")

    def discover_chains(
        self,
        start_event: str,
        direction: ChainDirection = ChainDirection.FORWARD,
        max_depth: int = 5,
        min_confidence: float = 0.5
    ) -> List[CausalChain]:
        """
        Discover causal chains starting from a given event

        Args:
            start_event: Starting event ID
            direction: Direction to traverse (forward/backward/both)
            max_depth: Maximum chain depth
            min_confidence: Minimum confidence threshold

        Returns:
            List of discovered causal chains
        """
        chains = []

        if direction in [ChainDirection.FORWARD, ChainDirection.BOTH]:
            forward_chains = self._discover_forward_chains(
                start_event, max_depth, min_confidence
            )
            chains.extend(forward_chains)

        if direction in [ChainDirection.BACKWARD, ChainDirection.BOTH]:
            backward_chains = self._discover_backward_chains(
                start_event, max_depth, min_confidence
            )
            chains.extend(backward_chains)

        # Sort by overall confidence
        chains.sort(key=lambda c: c.overall_confidence, reverse=True)

        logger.info(f"Discovered {len(chains)} chains from {start_event}")
        return chains

    def _discover_forward_chains(
        self,
        start: str,
        max_depth: int,
        min_confidence: float
    ) -> List[CausalChain]:
        """Discover forward causal chains using DFS"""
        chains = []
        visited = set()

        def dfs(current: str, path: List[str], links: List[CausalLink], depth: int):
            if depth > max_depth:
                return

            # Calculate chain confidence
            if links:
                confidence = min(link.confidence for link in links)
                if confidence < min_confidence:
                    return
            else:
                confidence = 1.0

            # Found a complete chain (length >= 2)
            if len(path) >= 2:
                chain_id = f"chain_{'_'.join(path)}"
                chain = CausalChain(
                    chain_id=chain_id,
                    events=path.copy(),
                    links=links.copy(),
                    overall_confidence=confidence,
                    chain_type=self._classify_chain(path, links),
                    depth=len(path) - 1
                )
                chains.append(chain)

            # Explore neighbors
            if current in visited and depth > 0:
                return
            visited.add(current)

            for neighbor, link_data in self.graph.get_successors(current).items():
                new_link = CausalLink(
                    source_id=current,
                    target_id=neighbor,
                    link_type=link_data['type'],
                    confidence=link_data['confidence'],
                    strength=link_data.get('strength', 0.0)
                )
                dfs(neighbor, path + [neighbor], links + [new_link], depth + 1)

            visited.discard(current)

        dfs(start, [start], [], 0)
        return chains

    def _discover_backward_chains(
        self,
        end: str,
        max_depth: int,
        min_confidence: float
    ) -> List[CausalChain]:
        """Discover backward causal chains (find causes)"""
        chains = []
        visited = set()

        def dfs(current: str, path: List[str], links: List[CausalLink], depth: int):
            if depth > max_depth:
                return

            if links:
                confidence = min(link.confidence for link in links)
                if confidence < min_confidence:
                    return
            else:
                confidence = 1.0

            if len(path) >= 2:
                chain_id = f"chain_{'_'.join(reversed(path))}"
                chain = CausalChain(
                    chain_id=chain_id,
                    events=path[::-1].copy(),  # Reverse for causal order
                    links=links[::-1].copy(),
                    overall_confidence=confidence,
                    chain_type=self._classify_chain(path[::-1], links[::-1]),
                    depth=len(path) - 1
                )
                chains.append(chain)

            if current in visited and depth > 0:
                return
            visited.add(current)

            for predecessor, link_data in self.graph.get_predecessors(current).items():
                new_link = CausalLink(
                    source_id=predecessor,
                    target_id=current,
                    link_type=link_data['type'],
                    confidence=link_data['confidence'],
                    strength=link_data.get('strength', 0.0)
                )
                dfs(predecessor, path + [predecessor], [new_link] + links, depth + 1)

            visited.discard(current)

        dfs(end, [end], [], 0)
        return chains

    def _classify_chain(self, events: List[str], links: List[CausalLink]) -> str:
        """Classify chain type based on structure"""
        if len(links) == 1:
            return "DIRECT"
        elif len(links) <= 3:
            return "INDIRECT"
        else:
            # Check for complexity (multiple branches, etc.)
            return "COMPLEX"

    def validate_chain(self, chain: CausalChain) -> Tuple[bool, str]:
        """Validate a causal chain"""
        status, message = chain.validate()
        return status == ChainValidationStatus.VALID, message

    def get_chain_statistics(self) -> Dict[str, Any]:
        """Get statistics about discovered chains"""
        all_chains = self.discover_chains(
            start_event=None,  # Get all
            direction=ChainDirection.BOTH,
            max_depth=10
        )

        if not all_chains:
            return {
                'total_chains': 0,
                'avg_depth': 0,
                'avg_confidence': 0,
                'max_depth': 0
            }

        depths = [c.depth for c in all_chains]
        confidences = [c.overall_confidence for c in all_chains]

        return {
            'total_chains': len(all_chains),
            'avg_depth': sum(depths) / len(depths),
            'avg_confidence': sum(confidences) / len(confidences),
            'max_depth': max(depths),
            'min_confidence': min(confidences),
            'chain_types': {
                'direct': sum(1 for c in all_chains if c.chain_type == 'DIRECT'),
                'indirect': sum(1 for c in all_chains if c.chain_type == 'INDIRECT'),
                'complex': sum(1 for c in all_chains if c.chain_type == 'COMPLEX')
            }
        }


class CounterfactualEngine:
    """Engine for counterfactual analysis and simulation"""

    def __init__(self, db: DeepMemoryStore):
        self.db = db
        self.discoverer = CausalChainDiscoverer(db)

    def simulate_scenario(
        self,
        scenario: CounterfactualScenario
    ) -> CounterfactualScenario:
        """Simulate a counterfactual scenario"""
        # Get the base event and its causal chain
        chains = self.discoverer.discover_chains(
            scenario.base_event,
            direction=ChainDirection.FORWARD,
            max_depth=5
        )

        if not chains:
            scenario.confidence = 0.0
            scenario.simulation_results = {'error': 'No causal chains found'}
            return scenario

        # Analyze impact of modification
        primary_chain = chains[0]
        impact_analysis = self._analyze_modification_impact(
            scenario.modification,
            primary_chain
        )

        # Predict alternative outcome
        alternative_outcome = self._predict_alternative_outcome(
            scenario.base_event,
            scenario.modification,
            impact_analysis
        )

        scenario.alternative_outcome = alternative_outcome
        scenario.confidence = impact_analysis['confidence']
        scenario.simulation_results = {
            'impact_analysis': impact_analysis,
            'affected_chains': len(chains),
            'confidence_breakdown': self._calculate_confidence_breakdown(
                scenario.modification,
                primary_chain
            )
        }

        return scenario

    def _analyze_modification_impact(
        self,
        modification: Dict[str, Any],
        chain: CausalChain
    ) -> Dict[str, Any]:
        """Analyze the impact of a modification on a causal chain"""
        # Check which links are affected
        affected_links = []
        for link in chain.links:
            if self._link_affected_by_modification(link, modification):
                affected_links.append(link.to_dict())

        # Calculate confidence reduction
        confidence_reduction = len(affected_links) * 0.1
        final_confidence = max(0.0, chain.overall_confidence - confidence_reduction)

        return {
            'affected_links': affected_links,
            'num_affected': len(affected_links),
            'confidence_reduction': confidence_reduction,
            'confidence': final_confidence
        }

    def _link_affected_by_modification(
        self,
        link: CausalLink,
        modification: Dict[str, Any]
    ) -> bool:
        """Check if a link is affected by the modification"""
        # Simple heuristic: check if modification affects source or target
        return (
            modification.get('affects_source', False) or
            modification.get('affects_target', False) or
            modification.get('breaks_link', False)
        )

    def _predict_alternative_outcome(
        self,
        base_event: str,
        modification: Dict[str, Any],
        impact_analysis: Dict[str, Any]
    ) -> str:
        """Predict the alternative outcome"""
        if impact_analysis['num_affected'] == 0:
            return "No significant change predicted"

        confidence = impact_analysis['confidence']
        if confidence > 0.8:
            return f"Significantly different outcome (confidence: {confidence:.2f})"
        elif confidence > 0.5:
            return f"Moderately different outcome (confidence: {confidence:.2f})"
        else:
            return f"Uncertain outcome (confidence: {confidence:.2f})"

    def _calculate_confidence_breakdown(
        self,
        modification: Dict[str, Any],
        chain: CausalChain
    ) -> Dict[str, Any]:
        """Calculate confidence breakdown for the simulation"""
        return {
            'base_confidence': chain.overall_confidence,
            'modification_uncertainty': modification.get('uncertainty', 0.1),
            'chain_complexity_factor': 1.0 / (1 + chain.depth * 0.1)
        }

    def compare_outcomes(
        self,
        actual_event: str,
        counterfactual_event: str
    ) -> Dict[str, Any]:
        """Compare actual vs counterfactual outcomes"""
        actual_chains = self.discoverer.discover_chains(actual_event)
        cf_chains = self.discoverer.discover_chains(counterfactual_event)

        return {
            'actual_chains': len(actual_chains),
            'counterfactual_chains': len(cf_chains),
            'difference': len(actual_chains) - len(cf_chains),
            'actual_avg_confidence': (
                sum(c.overall_confidence for c in actual_chains) / len(actual_chains)
                if actual_chains else 0
            ),
            'cf_avg_confidence': (
                sum(c.overall_confidence for c in cf_chains) / len(cf_chains)
                if cf_chains else 0
            )
        }


class InterventionPlanner:
    """Plans interventions to achieve desired outcomes"""

    def __init__(self, db: DeepMemoryStore):
        self.db = db
        self.discoverer = CausalChainDiscoverer(db)
        self.counterfactual = CounterfactualEngine(db)

    def plan_interventions(
        self,
        goal: str,
        constraints: Optional[List[str]] = None
    ) -> List[InterventionPlan]:
        """Generate intervention plans to achieve a goal"""
        # Find chains that lead to the goal
        goal_chains = self.discoverer.discover_chains(
            goal,
            direction=ChainDirection.BACKWARD,
            max_depth=5
        )

        if not goal_chains:
            return []

        plans = []
        for chain in goal_chains[:5]:  # Top 5 chains
            plan = self._create_intervention_plan(chain, goal, constraints)
            if plan:
                plans.append(plan)

        # Sort by success probability
        plans.sort(key=lambda p: p.success_probability, reverse=True)

        return plans

    def _create_intervention_plan(
        self,
        chain: CausalChain,
        goal: str,
        constraints: Optional[List[str]]
    ) -> Optional[InterventionPlan]:
        """Create an intervention plan for a chain"""
        if not chain.events or len(chain.events) < 2:
            return None

        # Identify intervention points
        interventions = []
        for i, event in enumerate(chain.events[:-1]):
            intervention = {
                'target': event,
                'action': 'modify',
                'priority': i + 1,
                'confidence': chain.links[i].confidence if i < len(chain.links) else 0.5
            }
            interventions.append(intervention)

        # Calculate success probability
        success_prob = chain.overall_confidence * 0.8  # Reduce for intervention uncertainty

        # Predict side effects
        side_effects = self._predict_side_effects(chain)

        plan_id = f"intervention_{'_'.join(chain.events[:3])}"
        return InterventionPlan(
            plan_id=plan_id,
            goal=goal,
            interventions=interventions,
            predicted_outcome=goal,
            success_probability=success_prob,
            side_effects=side_effects,
            timeline=f"{chain.depth} steps"
        )

    def _predict_side_effects(
        self,
        chain: CausalChain
    ) -> List[Dict[str, Any]]:
        """Predict potential side effects of intervention"""
        side_effects = []

        # Check for alternative paths
        for event in chain.events:
            alt_chains = self.discoverer.discover_chains(
                event,
                direction=ChainDirection.FORWARD,
                max_depth=3
            )
            # Filter out the main chain
            alt_chains = [c for c in alt_chains if c.chain_id != chain.chain_id]

            if alt_chains:
                side_effects.append({
                    'event': event,
                    'alternative_outcomes': len(alt_chains),
                    'risk': 'medium' if len(alt_chains) > 2 else 'low'
                })

        return side_effects

    def optimize_strategy(
        self,
        plans: List[InterventionPlan]
    ) -> InterventionPlan:
        """Select the best intervention plan"""
        if not plans:
            raise ValueError("No plans to optimize")

        # Score plans by success probability and side effects
        best_plan = max(
            plans,
            key=lambda p: (
                p.success_probability -
                len(p.side_effects) * 0.1  # Penalty for side effects
            )
        )

        return best_plan


class LessonsLearnedExtractor:
    """Extracts lessons learned from causal chains"""

    def __init__(self, db: DeepMemoryStore):
        self.db = db
        self.discoverer = CausalChainDiscoverer(db)

    def extract_lessons(
        self,
        event_ids: List[str],
        category: Optional[str] = None
    ) -> List[LessonLearned]:
        """Extract lessons from a set of events"""
        lessons = []

        for event_id in event_ids:
            # Find causal chains involving this event
            chains = self.discoverer.discover_chains(
                event_id,
                direction=ChainDirection.BOTH,
                max_depth=3
            )

            for chain in chains[:3]:  # Top 3 chains per event
                lesson = self._extract_lesson_from_chain(chain, category)
                if lesson:
                    lessons.append(lesson)

        return lessons

    def _extract_lesson_from_chain(
        self,
        chain: CausalChain,
        category: Optional[str]
    ) -> Optional[LessonLearned]:
        """Extract a lesson from a causal chain"""
        if len(chain.events) < 2:
            return None

        # Get event details
        cause_event = chain.events[0]
        effect_event = chain.events[-1]

        # Generate lesson text
        lesson_text = self._generate_lesson_text(chain)

        # Generate recommendations
        recommendations = self._generate_recommendations(chain)

        # Determine category
        if category is None:
            category = self._classify_lesson_category(chain)

        lesson_id = f"lesson_{cause_event}_{effect_event}"
        return LessonLearned(
            lesson_id=lesson_id,
            event_ids=chain.events,
            cause=cause_event,
            effect=effect_event,
            lesson_text=lesson_text,
            recommendations=recommendations,
            confidence=chain.overall_confidence,
            category=category
        )

    def _generate_lesson_text(self, chain: CausalChain) -> str:
        """Generate lesson text from chain"""
        if chain.depth == 1:
            return f"Direct causal relationship: {chain.events[0]} → {chain.events[1]}"
        else:
            chain_str = " → ".join(chain.events)
            return f"Causal chain observed: {chain_str} (depth: {chain.depth})"

    def _generate_recommendations(self, chain: CausalChain) -> List[str]:
        """Generate recommendations based on chain"""
        recommendations = []

        if chain.overall_confidence < 0.7:
            recommendations.append("Investigate causal relationship further")

        if chain.depth > 3:
            recommendations.append("Consider intermediate factors in the chain")

        # Add specific recommendations based on link types
        for link in chain.links:
            if link.link_type == 'INHIBITS':
                recommendations.append(f"Monitor {link.source_id} to prevent {link.target_id}")

        if not recommendations:
            recommendations.append("Continue monitoring this causal pattern")

        return recommendations

    def _classify_lesson_category(self, chain: CausalChain) -> str:
        """Classify lesson into category"""
        # Simple heuristic based on chain characteristics
        if chain.depth > 4:
            return "SYSTEM"
        elif chain.overall_confidence < 0.6:
            return "HUMAN"
        else:
            return "TECHNICAL"

    def get_lessons_summary(self) -> Dict[str, Any]:
        """Get summary of all extracted lessons"""
        all_lessons = self.extract_lessons(
            event_ids=[],  # Get all
            category=None
        )

        if not all_lessons:
            return {'total': 0}

        categories = {}
        for lesson in all_lessons:
            categories[lesson.category] = categories.get(lesson.category, 0) + 1

        return {
            'total': len(all_lessons),
            'by_category': categories,
            'avg_confidence': sum(l.confidence for l in all_lessons) / len(all_lessons)
        }


# API Handler Functions
async def handle_discover_chains(
    db: DeepMemoryStore,
    start_event: str,
    direction: str = "forward",
    max_depth: int = 5,
    min_confidence: float = 0.5
) -> Dict[str, Any]:
    """API handler for chain discovery"""
    discoverer = CausalChainDiscoverer(db)

    dir_map = {
        "forward": ChainDirection.FORWARD,
        "backward": ChainDirection.BACKWARD,
        "both": ChainDirection.BOTH
    }

    chains = discoverer.discover_chains(
        start_event,
        direction=dir_map.get(direction, ChainDirection.FORWARD),
        max_depth=max_depth,
        min_confidence=min_confidence
    )

    return {
        'chains': [c.to_dict() for c in chains],
        'count': len(chains),
        'statistics': discoverer.get_chain_statistics()
    }


async def handle_simulate_counterfactual(
    db: DeepMemoryStore,
    scenario: Dict[str, Any]
) -> Dict[str, Any]:
    """API handler for counterfactual simulation"""
    engine = CounterfactualEngine(db)

    cf_scenario = CounterfactualScenario(
        scenario_id=scenario.get('scenario_id', 'temp'),
        base_event=scenario['base_event'],
        modification=scenario['modification']
    )

    result = engine.simulate_scenario(cf_scenario)
    return result.to_dict()


async def handle_plan_intervention(
    db: DeepMemoryStore,
    goal: str,
    constraints: Optional[List[str]] = None
) -> Dict[str, Any]:
    """API handler for intervention planning"""
    planner = InterventionPlanner(db)

    plans = planner.plan_interventions(goal, constraints)
    best = planner.optimize_strategy(plans) if plans else None

    return {
        'plans': [p.to_dict() for p in plans],
        'best_plan': best.to_dict() if best else None,
        'count': len(plans)
    }


async def handle_extract_lessons(
    db: DeepMemoryStore,
    event_ids: List[str],
    category: Optional[str] = None
) -> Dict[str, Any]:
    """API handler for lesson extraction"""
    extractor = LessonsLearnedExtractor(db)

    lessons = extractor.extract_lessons(event_ids, category)
    summary = extractor.get_lessons_summary()

    return {
        'lessons': [l.to_dict() for l in lessons],
        'summary': summary,
        'count': len(lessons)
    }