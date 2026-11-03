"""V39.4 Innovation Engine.

Implements innovation capabilities:
- Cross-domain synthesis (combining ideas from different fields)
- Analogical reasoning (finding parallels between domains)
- Constraint relaxation (removing assumptions)
- Novelty detection (identifying truly new ideas)
- Innovation scoring (measuring innovation potential)
- Trend analysis (identifying emerging patterns)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
import re
from collections import defaultdict
import math


class InnovationLevel(Enum):
    """Levels of innovation."""
    INCREMENTAL = "incremental"
    MODERATE = "moderate"
    RADICAL = "radical"
    DISRUPTIVE = "disruptive"


class TrendDirection(Enum):
    """Trend directions."""
    EMERGING = "emerging"
    GROWING = "growing"
    MATURING = "maturing"
    DECLINING = "declining"


@dataclass
class InnovationOpportunity:
    """Innovation opportunity identification."""
    opportunity_id: str
    title: str
    description: str
    domain: str
    innovation_level: InnovationLevel
    market_potential: float  # 0-10
    technical_feasibility: float  # 0-10
    timing_score: float  # 0-10
    competitive_advantage: float  # 0-10
    risk_level: str
    estimated_impact: float
    required_capabilities: List[str]
    related_trends: List[str]
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "domain": self.domain,
            "innovation_level": self.innovation_level.value,
            "market_potential": round(self.market_potential, 2),
            "technical_feasibility": round(self.technical_feasibility, 2),
            "timing_score": round(self.timing_score, 2),
            "competitive_advantage": round(self.competitive_advantage, 2),
            "risk_level": self.risk_level,
            "estimated_impact": round(self.estimated_impact, 2),
            "score": round(self.score, 2)
        }


@dataclass
class Analogy:
    """Analogical reasoning result."""
    source_domain: str
    target_domain: str
    similarity_score: float
    shared_principles: List[str]
    transferred_ideas: List[str]
    validity_score: float
    novelty_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "similarity_score": round(self.similarity_score, 2),
            "shared_principles_count": len(self.shared_principles),
            "transferred_ideas_count": len(self.transferred_ideas),
            "validity_score": round(self.validity_score, 2),
            "novelty_score": round(self.novelty_score, 2)
        }


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    trend_name: str
    direction: TrendDirection
    strength: float  # 0-10
    growth_rate: float
    maturity_stage: str
    key_drivers: List[str]
    potential_impact: float
    time_horizon: str
    related_domains: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trend_name": self.trend_name,
            "direction": self.direction.value,
            "strength": round(self.strength, 2),
            "growth_rate": round(self.growth_rate, 2),
            "maturity_stage": self.maturity_stage,
            "key_drivers_count": len(self.key_drivers),
            "potential_impact": round(self.potential_impact, 2),
            "time_horizon": self.time_horizon
        }


@dataclass
class InnovationMetrics:
    """Innovation metrics for evaluation."""
    novelty_index: float  # How new is the idea
    feasibility_index: float  # How feasible to implement
    impact_index: float  # Potential impact
    differentiation_index: float  # How different from existing
    scalability_index: float  # How scalable
    sustainability_index: float  # Long-term viability
    overall_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "novelty_index": round(self.novelty_index, 2),
            "feasibility_index": round(self.feasibility_index, 2),
            "impact_index": round(self.impact_index, 2),
            "differentiation_index": round(self.differentiation_index, 2),
            "scalability_index": round(self.scalability_index, 2),
            "sustainability_index": round(self.sustainability_index, 2),
            "overall_score": round(self.overall_score, 2)
        }


class InnovationEngine:
    """Innovation engine for generating and evaluating innovative ideas."""
    
    def __init__(self):
        """Initialize innovation engine."""
        self.opportunity_counter = 0
        self._initialized = True
        
        print("✅ Innovation Engine initialized")
        print(f"   - Cross-domain synthesis: Ready")
        print(f"   - Analogical reasoning: Ready")
        print(f"   - Constraint relaxation: Ready")
        print(f"   - Novelty detection: Ready")
        print(f"   - Trend analysis: Ready")
        print(f"   - Innovation scoring: Ready")
    
    def synthesize_domains(self, domains: List[str],
                          focus_area: str = None) -> List[InnovationOpportunity]:
        """Synthesize ideas from multiple domains.
        
        Args:
            domains: List of domains to synthesize
            focus_area: Specific area to focus on
            
        Returns:
            List of innovation opportunities
        """
        opportunities = []
        
        # Generate cross-domain combinations
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                domain1 = domains[i]
                domain2 = domains[j]
                
                opportunity = self._create_cross_domain_opportunity(
                    domain1, domain2, focus_area
                )
                opportunities.append(opportunity)
        
        # Evaluate and score
        for opp in opportunities:
            opp.score = self._evaluate_opportunity(opp)
        
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        return opportunities
    
    def find_analogies(self, problem_domain: str,
                      source_domains: List[str]) -> List[Analogy]:
        """Find analogies from other domains.
        
        Args:
            problem_domain: Domain with the problem
            source_domains: Domains to search for analogies
            
        Returns:
            List of analogies
        """
        analogies = []
        
        for source in source_domains:
            analogy = self._create_analogy(problem_domain, source)
            analogies.append(analogy)
        
        # Sort by validity and novelty
        analogies.sort(
            key=lambda a: (a.validity_score * 0.6 + a.novelty_score * 0.4),
            reverse=True
        )
        
        return analogies
    
    def relax_constraints(self, problem: str,
                        current_constraints: List[str]) -> List[str]:
        """Relax constraints to find innovative solutions.
        
        Args:
            problem: Problem description
            current_constraints: Current constraints
            
        Returns:
            List of relaxed constraint scenarios
        """
        relaxed_scenarios = []
        
        # Relax each constraint individually
        for constraint in current_constraints:
            scenario = f"Without constraint: {constraint}"
            relaxed_scenarios.append(scenario)
        
        # Relax multiple constraints
        if len(current_constraints) >= 2:
            scenario = f"Without constraints: {', '.join(current_constraints[:2])}"
            relaxed_scenarios.append(scenario)
        
        # Complete constraint removal
        scenario = "No constraints - think completely freely"
        relaxed_scenarios.append(scenario)
        
        return relaxed_scenarios
    
    def detect_novelty(self, idea_description: str,
                      existing_ideas: List[str]) -> Tuple[bool, float]:
        """Detect if an idea is truly novel.
        
        Args:
            idea_description: Description of the new idea
            existing_ideas: List of existing idea descriptions
            
        Returns:
            Tuple of (is_novel, novelty_score)
        """
        # Simple similarity check (in production, would use NLP)
        max_similarity = 0.0
        
        idea_words = set(idea_description.lower().split())
        
        for existing in existing_ideas:
            existing_words = set(existing.lower().split())
            
            # Jaccard similarity
            intersection = len(idea_words & existing_words)
            union = len(idea_words | existing_words)
            
            if union > 0:
                similarity = intersection / union
                max_similarity = max(max_similarity, similarity)
        
        # Novelty score (inverse of similarity)
        novelty_score = 1.0 - max_similarity
        
        # Threshold for novelty (70% different)
        is_novel = novelty_score > 0.7
        
        return is_novel, novelty_score
    
    def analyze_trends(self, domain: str,
                      time_period: str = "current") -> List[TrendAnalysis]:
        """Analyze trends in a domain.
        
        Args:
            domain: Domain to analyze
            time_period: Time period for analysis
            
        Returns:
            List of trend analyses
        """
        trends = []
        
        # Sample trends (in production, would use real data)
        sample_trends = [
            {
                "name": "AI Integration",
                "direction": TrendDirection.GROWING,
                "strength": 8.5,
                "growth_rate": 0.25,
                "stage": "growth",
                "drivers": ["Technology advancement", "Cost reduction", "Proven ROI"],
                "impact": 9.0,
                "horizon": "1-3 years"
            },
            {
                "name": "Automation",
                "direction": TrendDirection.EMERGING,
                "strength": 7.0,
                "growth_rate": 0.35,
                "stage": "emerging",
                "drivers": ["Labor costs", "Efficiency gains", "24/7 operation"],
                "impact": 8.5,
                "horizon": "2-5 years"
            },
            {
                "name": "Sustainability",
                "direction": TrendDirection.GROWING,
                "strength": 8.0,
                "growth_rate": 0.20,
                "stage": "growth",
                "drivers": ["Regulation", "Consumer demand", "Cost savings"],
                "impact": 8.0,
                "horizon": "1-3 years"
            }
        ]
        
        for trend_data in sample_trends:
            trend = TrendAnalysis(
                trend_name=trend_data["name"],
                direction=trend_data["direction"],
                strength=trend_data["strength"],
                growth_rate=trend_data["growth_rate"],
                maturity_stage=trend_data["stage"],
                key_drivers=trend_data["drivers"],
                potential_impact=trend_data["impact"],
                time_horizon=trend_data["horizon"],
                related_domains=[domain, "technology", "business"]
            )
            trends.append(trend)
        
        return trends
    
    def calculate_innovation_metrics(self, idea: Dict[str, Any]) -> InnovationMetrics:
        """Calculate comprehensive innovation metrics.
        
        Args:
            idea: Idea data dictionary
            
        Returns:
            InnovationMetrics with all indices
        """
        # Extract values (with defaults)
        novelty = idea.get("novelty", 5.0)
        feasibility = idea.get("feasibility", 5.0)
        impact = idea.get("impact", 5.0)
        differentiation = idea.get("differentiation", 5.0)
        scalability = idea.get("scalability", 5.0)
        sustainability = idea.get("sustainability", 5.0)
        
        # Calculate overall score (weighted)
        overall = (
            novelty * 0.25 +
            feasibility * 0.20 +
            impact * 0.25 +
            differentiation * 0.15 +
            scalability * 0.10 +
            sustainability * 0.05
        )
        
        return InnovationMetrics(
            novelty_index=novelty,
            feasibility_index=feasibility,
            impact_index=impact,
            differentiation_index=differentiation,
            scalability_index=scalability,
            sustainability_index=sustainability,
            overall_score=overall
        )
    
    def identify_opportunities(self, market_data: Dict[str, Any],
                              capabilities: List[str]) -> List[InnovationOpportunity]:
        """Identify innovation opportunities from market data.
        
        Args:
            market_data: Market analysis data
            capabilities: Organization capabilities
            
        Returns:
            List of innovation opportunities
        """
        opportunities = []
        
        # Sample opportunity generation
        opportunity_templates = [
            {
                "title": "AI-Powered Solution",
                "description": "Leverage AI to solve market pain points",
                "domain": "Artificial Intelligence",
                "level": InnovationLevel.RADICAL,
                "market": 8.0,
                "technical": 7.0,
                "timing": 8.5,
                "advantage": 7.5,
                "risk": "Medium",
                "impact": 8.5,
                "capabilities": ["AI/ML", "Data Science", "Software Development"],
                "trends": ["AI Integration", "Automation"]
            },
            {
                "title": "Platform Ecosystem",
                "description": "Build interconnected platform ecosystem",
                "domain": "Platform Strategy",
                "level": InnovationLevel.MODERATE,
                "market": 7.5,
                "technical": 6.5,
                "timing": 7.0,
                "advantage": 8.0,
                "risk": "Medium-High",
                "impact": 8.0,
                "capabilities": ["Platform Development", "API Design", "Partnership"],
                "trends": ["Ecosystem Growth", "API Economy"]
            }
        ]
        
        for template in opportunity_templates:
            self.opportunity_counter += 1
            
            # Check capability match
            matched_caps = [
                cap for cap in template["capabilities"]
                if any(cap.lower() in c.lower() for c in capabilities)
            ]
            
            opportunity = InnovationOpportunity(
                opportunity_id=f"OPP_{self.opportunity_counter:04d}",
                title=template["title"],
                description=template["description"],
                domain=template["domain"],
                innovation_level=template["level"],
                market_potential=template["market"],
                technical_feasibility=template["technical"],
                timing_score=template["timing"],
                competitive_advantage=template["advantage"],
                risk_level=template["risk"],
                estimated_impact=template["impact"],
                required_capabilities=template["capabilities"],
                related_trends=template["trends"]
            )
            
            # Adjust score based on capability match
            if len(matched_caps) >= len(template["capabilities"]) * 0.7:
                opportunity.score = self._evaluate_opportunity(opportunity) * 1.1
            else:
                opportunity.score = self._evaluate_opportunity(opportunity) * 0.8
            
            opportunities.append(opportunity)
        
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        return opportunities
    
    def _create_cross_domain_opportunity(self, domain1: str,
                                        domain2: str,
                                        focus: str = None) -> InnovationOpportunity:
        """Create cross-domain innovation opportunity."""
        self.opportunity_counter += 1
        
        title = f"{domain1.title()} + {domain2.title()} Integration"
        
        opportunity = InnovationOpportunity(
            opportunity_id=f"OPP_{self.opportunity_counter:04d}",
            title=title,
            description=f"Combine {domain1} and {domain2} to create innovative solution",
            domain=f"{domain1}-{domain2}",
            innovation_level=InnovationLevel.RADICAL,
            market_potential=7.5,
            technical_feasibility=6.0,
            timing_score=7.0,
            competitive_advantage=8.0,
            risk_level="Medium-High",
            estimated_impact=8.0,
            required_capabilities=["Cross-domain expertise", "Integration skills"],
            related_trends=["Convergence", "Interdisciplinary"]
        )
        
        return opportunity
    
    def _create_analogy(self, source: str, target: str) -> Analogy:
        """Create analogy between domains."""
        # Sample shared principles
        shared_principles = [
            "System optimization",
            "Resource allocation",
            "Feedback loops",
            "Scalability patterns"
        ]
        
        # Sample transferred ideas
        transferred_ideas = [
            f"Apply {source} efficiency methods to {target}",
            f"Adapt {source} architecture for {target}",
            f"Use {source} metrics in {target} context"
        ]
        
        # Calculate similarity (random for demo)
        similarity = 0.4 + (hash(source + target) % 40) / 100
        validity = 0.5 + (hash(source) % 30) / 100
        novelty = 0.6 + (hash(target) % 30) / 100
        
        return Analogy(
            source_domain=source,
            target_domain=target,
            similarity_score=similarity,
            shared_principles=shared_principles,
            transferred_ideas=transferred_ideas,
            validity_score=validity,
            novelty_score=novelty
        )
    
    def _evaluate_opportunity(self, opportunity: InnovationOpportunity) -> float:
        """Evaluate innovation opportunity."""
        score = (
            opportunity.market_potential * 0.25 +
            opportunity.technical_feasibility * 0.20 +
            opportunity.timing_score * 0.20 +
            opportunity.competitive_advantage * 0.20 +
            opportunity.estimated_impact * 0.15
        )
        
        # Adjust for risk
        risk_multipliers = {
            "Low": 1.1,
            "Medium": 1.0,
            "Medium-High": 0.9,
            "High": 0.8
        }
        
        score *= risk_multipliers.get(opportunity.risk_level, 1.0)
        
        return min(max(score, 0), 10)
    
    def _generate_random_inputs(self) -> List[str]:
        """Generate random input words."""
        return ["innovation", "disruption", "efficiency", "growth", "sustainability"]


# Convenience functions
def synthesize(domains: List[str], focus: str = None) -> List[InnovationOpportunity]:
    """Synthesize cross-domain opportunities."""
    engine = InnovationEngine()
    return engine.synthesize_domains(domains, focus)


def find_analogies(problem: str, sources: List[str]) -> List[Analogy]:
    """Find analogies for problem solving."""
    engine = InnovationEngine()
    return engine.find_analogies(problem, sources)


def check_novelty(idea: str, existing: List[str]) -> Tuple[bool, float]:
    """Check if idea is novel."""
    engine = InnovationEngine()
    return engine.detect_novelty(idea, existing)


def analyze_domain_trends(domain: str) -> List[TrendAnalysis]:
    """Analyze trends in domain."""
    engine = InnovationEngine()
    return engine.analyze_trends(domain)


def score_innovation(idea: Dict[str, Any]) -> InnovationMetrics:
    """Score innovation potential."""
    engine = InnovationEngine()
    return engine.calculate_innovation_metrics(idea)