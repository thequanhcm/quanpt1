"""V39.5 Self-Optimization Engine.

Implements self-optimization capabilities:
- Parameter tuning (automatic adjustment based on performance)
- Strategy adaptation (learning from successful approaches)
- Knowledge refinement (pruning, updating, prioritizing)
- Skill prioritization (identifying high-impact skills)
- Performance optimization (resource allocation, caching)
- Continuous improvement loop
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
from datetime import datetime
from collections import defaultdict
import math


class OptimizationTarget(Enum):
    """Optimization targets."""
    SPEED = "speed"
    ACCURACY = "accuracy"
    COST = "cost"
    RESOURCE_USAGE = "resource_usage"
    USER_SATISFACTION = "user_satisfaction"


class AdaptationStrategy(Enum):
    """Adaptation strategies."""
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"
    BALANCED = "balanced"


@dataclass
class ParameterConfig:
    """Parameter configuration."""
    param_name: str
    current_value: Any
    optimal_value: Optional[Any]
    min_value: Any
    max_value: Any
    step_size: Any
    importance: float  # 0-1
    last_optimized: Optional[datetime] = None
    improvement_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "param_name": self.param_name,
            "current_value": str(self.current_value),
            "optimal_value": str(self.optimal_value) if self.optimal_value else None,
            "importance": round(self.importance, 2),
            "improvement_count": self.improvement_count
        }


@dataclass
class SkillProfile:
    """Skill performance profile."""
    skill_id: str
    name: str
    usage_frequency: float
    success_rate: float
    avg_performance: float
    improvement_potential: float
    priority_score: float
    last_used: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "usage_frequency": round(self.usage_frequency, 2),
            "success_rate": round(self.success_rate, 2),
            "priority_score": round(self.priority_score, 2),
            "improvement_potential": round(self.improvement_potential, 2)
        }


@dataclass
class OptimizationResult:
    """Optimization result."""
    optimization_id: str
    target: OptimizationTarget
    before_value: float
    after_value: float
    improvement_pct: float
    parameters_changed: List[str]
    strategy_used: AdaptationStrategy
    timestamp: datetime
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "optimization_id": self.optimization_id,
            "target": self.target.value,
            "before_value": round(self.before_value, 4),
            "after_value": round(self.after_value, 4),
            "improvement_pct": round(self.improvement_pct, 2),
            "parameters_changed": self.parameters_changed,
            "strategy_used": self.strategy_used.value,
            "confidence": round(self.confidence, 2)
        }


@dataclass
class KnowledgeRefinement:
    """Knowledge refinement result."""
    refinement_id: str
    action: str  # prune, update, merge, prioritize
    knowledge_id: str
    reason: str
    impact_score: float
    confidence: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "refinement_id": self.refinement_id,
            "action": self.action,
            "knowledge_id": self.knowledge_id,
            "reason": self.reason,
            "impact_score": round(self.impact_score, 2),
            "confidence": round(self.confidence, 2)
        }


class SelfOptimizer:
    """Self-optimization engine."""
    
    def __init__(self):
        """Initialize self optimizer."""
        self.optimization_counter = 0
        self.refinement_counter = 0
        
        self.parameters: Dict[str, ParameterConfig] = {}
        self.skills: Dict[str, SkillProfile] = {}
        self.optimization_history: List[OptimizationResult] = []
        self.refinements: List[KnowledgeRefinement] = []
        
        self._initialized = True
        
        print("✅ Self-Optimization Engine initialized")
        print(f"   - Parameter tuning: Ready")
        print(f"   - Strategy adaptation: Ready")
        print(f"   - Knowledge refinement: Ready")
        print(f"   - Skill prioritization: Ready")
        print(f"   - Performance optimization: Ready")
    
    def tune_parameters(self,
                       current_params: Dict[str, Any],
                       performance_metrics: Dict[str, float],
                       target: OptimizationTarget = OptimizationTarget.ACCURACY) -> Dict[str, Any]:
        """Automatically tune parameters based on performance.
        
        Args:
            current_params: Current parameter values
            performance_metrics: Current performance metrics
            target: Optimization target
            
        Returns:
            Optimized parameter values
        """
        optimized = current_params.copy()
        
        # Initialize parameter configs if needed
        for param_name, value in current_params.items():
            if param_name not in self.parameters:
                self.parameters[param_name] = ParameterConfig(
                    param_name=param_name,
                    current_value=value,
                    optimal_value=None,
                    min_value=0,
                    max_value=100,
                    step_size=1,
                    importance=0.5
                )
        
        # Analyze which parameters to adjust
        adjustments = self._calculate_parameter_adjustments(
            current_params, performance_metrics, target
        )
        
        # Apply adjustments
        for param_name, adjustment in adjustments.items():
            if param_name in optimized:
                current = optimized[param_name]
                if isinstance(current, (int, float)):
                    new_value = current + adjustment
                    # Clamp to reasonable range
                    new_value = max(0, min(100, new_value))
                    optimized[param_name] = new_value
                    
                    # Update config
                    if param_name in self.parameters:
                        self.parameters[param_name].current_value = new_value
                        self.parameters[param_name].improvement_count += 1
        
        # Record optimization
        self._record_optimization(
            target,
            performance_metrics,
            {k: optimized.get(k, v) for k, v in performance_metrics.items()},
            list(adjustments.keys()),
            AdaptationStrategy.EXPLOITATION
        )
        
        return optimized
    
    def adapt_strategy(self,
                      context: Dict[str, Any],
                      available_strategies: List[AdaptationStrategy],
                      historical_performance: Dict[str, float]) -> AdaptationStrategy:
        """Adapt strategy based on context and history.
        
        Args:
            context: Current context
            available_strategies: Available strategies
            historical_performance: Historical performance by strategy
            
        Returns:
            Recommended strategy
        """
        if not available_strategies:
            return AdaptationStrategy.BALANCED
        
        # Score each strategy
        strategy_scores = {}
        
        for strategy in available_strategies:
            base_score = historical_performance.get(strategy.value, 0.5)
            
            # Adjust based on context
            context_factor = self._calculate_context_factor(context, strategy)
            
            # Exploration-exploitation balance
            if len(self.optimization_history) < 10:
                # More exploration early on
                exploration_bonus = 0.2
            else:
                exploration_bonus = 0.0
            
            strategy_scores[strategy] = base_score * context_factor + exploration_bonus
        
        # Select best strategy
        best_strategy = max(strategy_scores, key=strategy_scores.get)
        
        return best_strategy
    
    def refine_knowledge(self,
                        knowledge_items: List[Dict[str, Any]],
                        usage_patterns: Dict[str, int],
                        quality_scores: Dict[str, float]) -> List[KnowledgeRefinement]:
        """Refine knowledge base based on usage and quality.
        
        Args:
            knowledge_items: List of knowledge items
            usage_patterns: Usage frequency by item
            quality_scores: Quality scores by item
            
        Returns:
            List of refinement actions
        """
        refinements = []
        
        for item in knowledge_items:
            item_id = item.get("id", "unknown")
            usage = usage_patterns.get(item_id, 0)
            quality = quality_scores.get(item_id, 0.5)
            
            # Determine action
            if usage == 0 and quality < 0.3:
                action = "prune"
                reason = "Unused and low quality"
                impact = 0.7
            elif usage > 100 and quality < 0.7:
                action = "update"
                reason = "High usage but quality needs improvement"
                impact = 0.9
            elif usage > 50 and quality > 0.8:
                action = "prioritize"
                reason = "High usage and quality - prioritize"
                impact = 0.8
            else:
                action = "review"
                reason = "Needs manual review"
                impact = 0.5
            
            self.refinement_counter += 1
            
            refinement = KnowledgeRefinement(
                refinement_id=f"REFINE_{self.refinement_counter:04d}",
                action=action,
                knowledge_id=item_id,
                reason=reason,
                impact_score=impact,
                confidence=0.8,
                timestamp=datetime.now()
            )
            
            refinements.append(refinement)
        
        # Sort by impact
        refinements.sort(key=lambda x: x.impact_score, reverse=True)
        
        return refinements
    
    def prioritize_skills(self,
                         skill_usage: Dict[str, int],
                         skill_success_rates: Dict[str, float],
                         business_impact: Dict[str, float]) -> List[SkillProfile]:
        """Prioritize skills based on usage, success, and impact.
        
        Args:
            skill_usage: Usage frequency by skill
            skill_success_rates: Success rate by skill
            business_impact: Business impact score by skill
            
        Returns:
            List of skill profiles sorted by priority
        """
        profiles = []
        
        all_skills = set(skill_usage.keys()) | set(skill_success_rates.keys()) | set(business_impact.keys())
        
        for skill_id in all_skills:
            usage = skill_usage.get(skill_id, 0)
            success = skill_success_rates.get(skill_id, 0.5)
            impact = business_impact.get(skill_id, 0.5)
            
            # Calculate priority score
            # Weighted combination: usage (30%), success (30%), impact (40%)
            priority_score = (
                (min(usage / 100, 1.0) * 0.3) +
                (success * 0.3) +
                (impact * 0.4)
            )
            
            # Calculate improvement potential
            improvement_potential = (1.0 - success) * 0.7 + (1.0 - min(usage / 100, 1.0)) * 0.3
            
            profile = SkillProfile(
                skill_id=skill_id,
                name=skill_id.replace("_", " ").title(),
                usage_frequency=min(usage / 100, 1.0),
                success_rate=success,
                avg_performance=(success + impact) / 2,
                improvement_potential=improvement_potential,
                priority_score=priority_score,
                last_used=datetime.now() if usage > 0 else None
            )
            
            profiles.append(profile)
        
        # Sort by priority
        profiles.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Update internal state
        for profile in profiles:
            self.skills[profile.skill_id] = profile
        
        return profiles
    
    def optimize_performance(self,
                            current_metrics: Dict[str, float],
                            target_metrics: Dict[str, float],
                            constraints: Dict[str, Any]) -> OptimizationResult:
        """Optimize performance to meet targets.
        
        Args:
            current_metrics: Current performance metrics
            target_metrics: Target metrics
            constraints: Optimization constraints
            
        Returns:
            Optimization result
        """
        self.optimization_counter += 1
        
        # Calculate improvement needed
        improvements = {}
        for metric, target in target_metrics.items():
            current = current_metrics.get(metric, 0)
            if current > 0:
                improvements[metric] = (target - current) / current * 100
        
        # Estimate overall improvement
        avg_improvement = sum(improvements.values()) / len(improvements) if improvements else 0
        
        # Determine strategy
        if avg_improvement > 20:
            strategy = AdaptationStrategy.EXPLORATION
        elif avg_improvement > 5:
            strategy = AdaptationStrategy.BALANCED
        else:
            strategy = AdaptationStrategy.EXPLOITATION
        
        # Simulate optimization
        optimized_metrics = {}
        for metric, target in target_metrics.items():
            current = current_metrics.get(metric, 0)
            # Assume 50% of improvement is achieved
            optimized_metrics[metric] = current + (target - current) * 0.5
        
        # Calculate actual improvement
        before = sum(current_metrics.values()) / len(current_metrics) if current_metrics else 0
        after = sum(optimized_metrics.values()) / len(optimized_metrics) if optimized_metrics else 0
        
        improvement_pct = ((after - before) / before * 100) if before > 0 else 0
        
        result = OptimizationResult(
            optimization_id=f"OPT_{self.optimization_counter:04d}",
            target=OptimizationTarget.ACCURACY,  # Default
            before_value=before,
            after_value=after,
            improvement_pct=improvement_pct,
            parameters_changed=list(target_metrics.keys()),
            strategy_used=strategy,
            timestamp=datetime.now(),
            confidence=0.75
        )
        
        self.optimization_history.append(result)
        
        return result
    
    def get_optimization_recommendations(self,
                                        focus_area: str = "all") -> List[Dict[str, Any]]:
        """Get optimization recommendations.
        
        Args:
            focus_area: Area to focus on (all, parameters, skills, knowledge)
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if focus_area in ["all", "parameters"]:
            # Recommend parameter adjustments
            for param_name, config in self.parameters.items():
                if config.improvement_count < 3:
                    recommendations.append({
                        "type": "parameter",
                        "item": param_name,
                        "action": "tune",
                        "reason": f"Only optimized {config.improvement_count} times",
                        "priority": "medium"
                    })
        
        if focus_area in ["all", "skills"]:
            # Recommend skill improvements
            for skill_id, profile in self.skills.items():
                if profile.improvement_potential > 0.5:
                    recommendations.append({
                        "type": "skill",
                        "item": skill_id,
                        "action": "improve",
                        "reason": f"High improvement potential: {profile.improvement_potential:.2f}",
                        "priority": "high" if profile.improvement_potential > 0.7 else "medium"
                    })
        
        if focus_area in ["all", "knowledge"]:
            # Recommend knowledge refinements
            recent_refinements = self.refinements[-10:]
            for refinement in recent_refinements:
                if refinement.action in ["prune", "update"]:
                    recommendations.append({
                        "type": "knowledge",
                        "item": refinement.knowledge_id,
                        "action": refinement.action,
                        "reason": refinement.reason,
                        "priority": "high" if refinement.impact_score > 0.8 else "medium"
                    })
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 2))
        
        return recommendations
    
    def _calculate_parameter_adjustments(self,
                                        params: Dict[str, Any],
                                        metrics: Dict[str, float],
                                        target: OptimizationTarget) -> Dict[str, float]:
        """Calculate parameter adjustments needed."""
        adjustments = {}
        
        # Simple heuristic: adjust parameters that correlate with target metric
        for param_name in params:
            # Simulate correlation analysis
            if target == OptimizationTarget.SPEED:
                if "timeout" in param_name or "delay" in param_name:
                    adjustments[param_name] = -2  # Reduce timeout/delay
                elif "batch" in param_name:
                    adjustments[param_name] = 5  # Increase batch size
            elif target == OptimizationTarget.ACCURACY:
                if "threshold" in param_name:
                    adjustments[param_name] = 1  # Adjust threshold
                elif "confidence" in param_name:
                    adjustments[param_name] = 2  # Increase confidence
            elif target == OptimizationTarget.COST:
                if "retry" in param_name:
                    adjustments[param_name] = -1  # Reduce retries
                elif "parallel" in param_name:
                    adjustments[param_name] = -2  # Reduce parallelism
        
        return adjustments
    
    def _calculate_context_factor(self,
                                 context: Dict[str, Any],
                                 strategy: AdaptationStrategy) -> float:
        """Calculate context factor for strategy selection."""
        factor = 1.0
        
        # Adjust based on context
        if context.get("urgency", "low") == "high":
            if strategy == AdaptationStrategy.EXPLOITATION:
                factor *= 1.2
            else:
                factor *= 0.8
        
        if context.get("complexity", "medium") == "high":
            if strategy == AdaptationStrategy.EXPLORATION:
                factor *= 1.1
            else:
                factor *= 0.9
        
        return factor
    
    def _record_optimization(self,
                            target: OptimizationTarget,
                            before: Dict[str, float],
                            after: Dict[str, float],
                            params_changed: List[str],
                            strategy: AdaptationStrategy):
        """Record optimization result."""
        self.optimization_counter += 1
        
        before_avg = sum(before.values()) / len(before) if before else 0
        after_avg = sum(after.values()) / len(after) if after else 0
        
        improvement = ((after_avg - before_avg) / before_avg * 100) if before_avg > 0 else 0
        
        result = OptimizationResult(
            optimization_id=f"OPT_{self.optimization_counter:04d}",
            target=target,
            before_value=before_avg,
            after_value=after_avg,
            improvement_pct=improvement,
            parameters_changed=params_changed,
            strategy_used=strategy,
            timestamp=datetime.now(),
            confidence=0.8
        )
        
        self.optimization_history.append(result)


# Convenience functions
def tune_system_params(params: Dict[str, Any], metrics: Dict[str, float]) -> Dict[str, Any]:
    """Tune system parameters."""
    optimizer = SelfOptimizer()
    return optimizer.tune_parameters(params, metrics)


def select_strategy(context: Dict[str, Any], strategies: List[str]) -> str:
    """Select best strategy."""
    optimizer = SelfOptimizer()
    strat_objs = [AdaptationStrategy(s) for s in strategies]
    result = optimizer.adapt_strategy(context, strat_objs, {})
    return result.value


def refine_knowledge_base(items: List[Dict[str, Any]]) -> List[KnowledgeRefinement]:
    """Refine knowledge base."""
    optimizer = SelfOptimizer()
    return optimizer.refine_knowledge(items, {}, {})


def prioritize_skill_set(usage: Dict[str, int], success: Dict[str, float]) -> List[SkillProfile]:
    """Prioritize skills."""
    optimizer = SelfOptimizer()
    return optimizer.prioritize_skills(usage, success, {})