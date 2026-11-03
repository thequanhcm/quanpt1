"""V39.4 Creative Thinking Engine.

Implements creative thinking capabilities:
- Brainstorming techniques (classic, reverse, worst idea)
- Lateral thinking (random input, challenge assumptions)
- SCAMPER method (Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse)
- Mind mapping (hierarchical idea organization)
- Idea evaluation (feasibility, impact, novelty)
- Cross-pollination (combining unrelated concepts)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
import random
import re
from collections import defaultdict


class BrainstormingTechnique(Enum):
    """Brainstorming techniques."""
    CLASSIC = "classic"
    REVERSE = "reverse"
    WORST_IDEA = "worst_idea"
    ROUND_ROBIN = "round_robin"
    brainwriting = "brainwriting"


class SCAMPERAction(Enum):
    """SCAMPER actions."""
    SUBSTITUTE = "substitute"
    COMBINE = "combine"
    ADAPT = "adapt"
    MODIFY = "modify"
    PUT_TO_OTHER_USES = "put_to_other_uses"
    ELIMINATE = "eliminate"
    REVERSE = "reverse"


@dataclass
class Idea:
    """Idea representation."""
    idea_id: str
    title: str
    description: str
    category: str
    technique_used: str
    feasibility: float  # 0-10
    impact: float  # 0-10
    novelty: float  # 0-10
    effort: float  # 0-10 (lower is easier)
    pros: List[str]
    cons: List[str]
    dependencies: List[str]
    tags: List[str]
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "idea_id": self.idea_id,
            "title": self.title,
            "category": self.category,
            "technique_used": self.technique_used,
            "feasibility": round(self.feasibility, 2),
            "impact": round(self.impact, 2),
            "novelty": round(self.novelty, 2),
            "score": round(self.score, 2),
            "pros_count": len(self.pros),
            "cons_count": len(self.cons),
            "tags": self.tags
        }


@dataclass
class MindMapNode:
    """Mind map node."""
    node_id: str
    title: str
    description: str
    parent_id: Optional[str]
    children: List['MindMapNode'] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    color: str = "blue"
    icon: str = "•"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "title": self.title,
            "description": self.description,
            "parent_id": self.parent_id,
            "children_count": len(self.children),
            "tags": self.tags
        }


@dataclass
class BrainstormingSession:
    """Brainstorming session results."""
    session_id: str
    topic: str
    technique: BrainstormingTechnique
    ideas: List[Idea]
    duration_minutes: int
    participant_count: int
    total_ideas: int
    top_ideas: List[Idea]
    themes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "technique": self.technique.value,
            "total_ideas": self.total_ideas,
            "top_ideas_count": len(self.top_ideas),
            "themes": self.themes
        }


class IdeaGenerator:
    """Idea generation engine."""
    
    def __init__(self, seed: int = 42):
        """Initialize idea generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        random.seed(seed)
        self.idea_counter = 0
        self._initialized = True
        
        print("✅ Idea Generator initialized")
        print(f"   - Brainstorming: Ready")
        print(f"   - Lateral thinking: Ready")
        print(f"   - SCAMPER method: Ready")
        print(f"   - Mind mapping: Ready")
        print(f"   - Idea evaluation: Ready")
    
    def brainstorm(self, topic: str,
                  technique: BrainstormingTechnique = BrainstormingTechnique.CLASSIC,
                  num_ideas: int = 10,
                  context: Dict[str, Any] = None) -> BrainstormingSession:
        """Generate ideas using brainstorming technique.
        
        Args:
            topic: Brainstorming topic
            technique: Brainstorming technique to use
            num_ideas: Number of ideas to generate
            context: Additional context
            
        Returns:
            BrainstormingSession with generated ideas
        """
        self.idea_counter += 1
        session_id = f"BS_{self.idea_counter:04d}"
        
        # Generate ideas based on technique
        if technique == BrainstormingTechnique.CLASSIC:
            ideas = self._classic_brainstorm(topic, num_ideas, context)
        elif technique == BrainstormingTechnique.REVERSE:
            ideas = self._reverse_brainstorm(topic, num_ideas, context)
        elif technique == BrainstormingTechnique.WORST_IDEA:
            ideas = self._worst_idea_brainstorm(topic, num_ideas, context)
        else:
            ideas = self._classic_brainstorm(topic, num_ideas, context)
        
        # Evaluate and score ideas
        for idea in ideas:
            idea.score = self._evaluate_idea(idea)
        
        # Sort by score
        ideas.sort(key=lambda x: x.score, reverse=True)
        
        # Identify themes
        themes = self._extract_themes(ideas)
        
        # Select top ideas
        top_ideas = ideas[:min(5, len(ideas))]
        
        return BrainstormingSession(
            session_id=session_id,
            topic=topic,
            technique=technique,
            ideas=ideas,
            duration_minutes=30,
            participant_count=1,
            total_ideas=len(ideas),
            top_ideas=top_ideas,
            themes=themes
        )
    
    def lateral_thinking(self, topic: str,
                        random_inputs: List[str] = None,
                        num_ideas: int = 8) -> List[Idea]:
        """Generate ideas using lateral thinking.
        
        Args:
            topic: Problem topic
            random_inputs: Random words/concepts to stimulate thinking
            num_ideas: Number of ideas to generate
            
        Returns:
            List of creative ideas
        """
        self.idea_counter += 1
        
        if not random_inputs:
            random_inputs = self._generate_random_inputs()
        
        ideas = []
        
        # Force connections between topic and random inputs
        for i, random_input in enumerate(random_inputs[:num_ideas]):
            idea = self._create_lateral_connection(topic, random_input)
            idea.idea_id = f"LT_{self.idea_counter:04d}_{i}"
            ideas.append(idea)
        
        # Challenge assumptions
        assumption_challenges = self._challenge_assumptions(topic)
        for i, challenge in enumerate(assumption_challenges[:2]):
            idea = self._create_challenge_idea(topic, challenge)
            idea.idea_id = f"LT_{self.idea_counter:04d}_C{i}"
            ideas.append(idea)
        
        # Evaluate ideas
        for idea in ideas:
            idea.score = self._evaluate_idea(idea)
        
        ideas.sort(key=lambda x: x.score, reverse=True)
        
        return ideas
    
    def scamper(self, topic: str,
               existing_solution: str,
               actions: List[SCAMPERAction] = None) -> List[Idea]:
        """Apply SCAMPER method to improve existing solution.
        
        Args:
            topic: Topic/problem area
            existing_solution: Current solution description
            actions: SCAMPER actions to apply (default: all)
            
        Returns:
            List of improved ideas
        """
        self.idea_counter += 0
        
        if actions is None:
            actions = list(SCAMPERAction)
        
        ideas = []
        
        for action in actions:
            improved_idea = self._apply_scamper_action(
                topic, existing_solution, action
            )
            improved_idea.idea_id = f"SCAMPER_{action.value.upper()}"
            ideas.append(improved_idea)
        
        # Evaluate ideas
        for idea in ideas:
            idea.score = self._evaluate_idea(idea)
        
        ideas.sort(key=lambda x: x.score, reverse=True)
        
        return ideas
    
    def create_mind_map(self, central_topic: str,
                       branches: List[Dict[str, Any]] = None) -> MindMapNode:
        """Create a mind map for idea organization.
        
        Args:
            central_topic: Central topic of the mind map
            branches: List of branch definitions
            
        Returns:
            Root MindMapNode with complete structure
        """
        self.idea_counter += 0
        
        root = MindMapNode(
            node_id="ROOT",
            title=central_topic,
            description=f"Mind map for {central_topic}",
            parent_id=None,
            color="red",
            icon="★"
        )
        
        if branches:
            for branch_def in branches:
                branch_node = MindMapNode(
                    node_id=f"BRANCH_{len(root.children)+1}",
                    title=branch_def.get("title", "Branch"),
                    description=branch_def.get("description", ""),
                    parent_id=root.node_id,
                    tags=branch_def.get("tags", []),
                    color=self._get_branch_color(len(root.children))
                )
                
                # Add sub-branches
                for sub_def in branch_def.get("sub_branches", []):
                    sub_node = MindMapNode(
                        node_id=f"SUB_{len(branch_node.children)+1}",
                        title=sub_def.get("title", "Sub-branch"),
                        description=sub_def.get("description", ""),
                        parent_id=branch_node.node_id,
                        tags=sub_def.get("tags", [])
                    )
                    branch_node.children.append(sub_node)
                
                root.children.append(branch_node)
        
        return root
    
    def evaluate_idea(self, idea: Idea,
                     criteria: Dict[str, float] = None) -> float:
        """Evaluate an idea based on multiple criteria.
        
        Args:
            idea: Idea to evaluate
            criteria: Weights for evaluation criteria
            
        Returns:
            Overall score (0-10)
        """
        if criteria is None:
            criteria = {
                "feasibility": 0.3,
                "impact": 0.4,
                "novelty": 0.2,
                "effort": -0.1  # Negative weight (lower effort is better)
            }
        
        score = (
            idea.feasibility * criteria.get("feasibility", 0.3) +
            idea.impact * criteria.get("impact", 0.4) +
            idea.novelty * criteria.get("novelty", 0.2) +
            (10 - idea.effort) * criteria.get("effort", -0.1)
        )
        
        return min(max(score, 0), 10)
    
    def cross_pollinate(self, concepts: List[str],
                       domain: str = "general") -> List[Idea]:
        """Combine unrelated concepts to generate innovative ideas.
        
        Args:
            concepts: List of unrelated concepts
            domain: Target domain for application
            
        Returns:
            List of cross-pollinated ideas
        """
        self.idea_counter += 0
        
        if len(concepts) < 2:
            return []
        
        ideas = []
        
        # Combine concepts in pairs
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                idea = self._combine_concepts(concepts[i], concepts[j], domain)
                idea.idea_id = f"CP_{i}_{j}"
                ideas.append(idea)
        
        # Evaluate ideas
        for idea in ideas:
            idea.score = self._evaluate_idea(idea)
        
        ideas.sort(key=lambda x: x.score, reverse=True)
        
        return ideas
    
    def _classic_brainstorm(self, topic: str,
                           num_ideas: int,
                           context: Dict[str, Any] = None) -> List[Idea]:
        """Classic brainstorming - generate diverse ideas."""
        ideas = []
        
        # Idea templates
        templates = [
            f"Implement AI-powered {topic.lower()} solution",
            f"Create automated {topic.lower()} system",
            f"Develop mobile app for {topic.lower()}",
            f"Build cloud-based {topic.lower()} platform",
            f"Design collaborative {topic.lower()} tool",
            f"Create gamified {topic.lower()} experience",
            f"Implement real-time {topic.lower()} monitoring",
            f"Develop predictive {topic.lower()} analytics",
            f"Create personalized {topic.lower()} recommendations",
            f"Build open-source {topic.lower()} framework"
        ]
        
        for i in range(min(num_ideas, len(templates))):
            self.idea_counter += 1
            idea = Idea(
                idea_id=f"IDEA_{self.idea_counter:04d}",
                title=templates[i],
                description=f"Classic brainstorming idea for {topic}",
                category="Technology",
                technique_used="classic_brainstorming",
                feasibility=random.uniform(5, 9),
                impact=random.uniform(5, 9),
                novelty=random.uniform(4, 8),
                effort=random.uniform(3, 8),
                pros=[f"Addresses {topic}", "Proven approach", "Scalable"],
                cons=["Requires development", "Maintenance overhead"],
                dependencies=[],
                tags=[topic.lower(), "innovation", "technology"]
            )
            ideas.append(idea)
        
        return ideas
    
    def _reverse_brainstorm(self, topic: str,
                           num_ideas: int,
                           context: Dict[str, Any] = None) -> List[Idea]:
        """Reverse brainstorming - think about how to cause the problem, then reverse."""
        ideas = []
        
        # How to make the problem worse
        negative_ideas = [
            f"Ignore {topic} completely",
            f"Make {topic} more complex",
            f"Remove all {topic} safeguards",
            f"Centralize all {topic} control",
            f"Eliminate {topic} automation"
        ]
        
        # Reverse them
        for i, negative in enumerate(negative_ideas[:num_ideas]):
            self.idea_counter += 1
            positive = negative.replace("Ignore", "Prioritize").replace(
                "more complex", "simpler"
            ).replace("Remove", "Add").replace(
                "Centralize", "Distribute"
            ).replace("Eliminate", "Increase")
            
            idea = Idea(
                idea_id=f"IDEA_{self.idea_counter:04d}",
                title=positive,
                description=f"Reversed from: {negative}",
                category="Strategy",
                technique_used="reverse_brainstorming",
                feasibility=random.uniform(6, 9),
                impact=random.uniform(6, 9),
                novelty=random.uniform(7, 9),
                effort=random.uniform(4, 7),
                pros=["Counter-intuitive", "Fresh perspective"],
                cons=["May require culture change"],
                dependencies=[],
                tags=[topic.lower(), "reverse-thinking", "strategy"]
            )
            ideas.append(idea)
        
        return ideas
    
    def _worst_idea_brainstorm(self, topic: str,
                               num_ideas: int,
                               context: Dict[str, Any] = None) -> List[Idea]:
        """Worst idea brainstorming - generate terrible ideas, then improve them."""
        ideas = []
        
        # Terrible ideas
        terrible_ideas = [
            f"Charge users $1000 to use {topic}",
            f"Make {topic} only available at 3 AM",
            f"Require manual approval for every {topic} action",
            f"Send {topic} results via snail mail",
            f"Make {topic} require 100 clicks"
        ]
        
        # Improve them
        for i, terrible in enumerate(terrible_ideas[:num_ideas]):
            self.idea_counter += 1
            
            # Flip to positive
            improved = terrible.replace("$1000", "free").replace(
                "3 AM", "anytime"
            ).replace("manual approval", "automation").replace(
                "snail mail", "instant delivery"
            ).replace("100 clicks", "1 click")
            
            idea = Idea(
                idea_id=f"IDEA_{self.idea_counter:04d}",
                title=improved,
                description=f"Improved from worst idea: {terrible}",
                category="Innovation",
                technique_used="worst_idea",
                feasibility=random.uniform(7, 9),
                impact=random.uniform(6, 8),
                novelty=random.uniform(8, 10),
                effort=random.uniform(3, 6),
                pros=["User-friendly", "Cost-effective", "Fast"],
                cons=["May need user education"],
                dependencies=[],
                tags=[topic.lower(), "worst-idea", "innovation"]
            )
            ideas.append(idea)
        
        return ideas
    
    def _create_lateral_connection(self, topic: str,
                                   random_input: str) -> Idea:
        """Create connection between topic and random input."""
        self.idea_counter += 1
        
        idea = Idea(
            idea_id=f"LT_{self.idea_counter:04d}",
            title=f"Combine {topic} with {random_input}",
            description=f"Use {random_input} principles to solve {topic}",
            category="Lateral Thinking",
            technique_used="lateral_thinking",
            feasibility=random.uniform(4, 7),
            impact=random.uniform(5, 8),
            novelty=random.uniform(8, 10),
            effort=random.uniform(5, 8),
            pros=["Highly creative", "Unique approach"],
            cons=["Unproven", "May need validation"],
            dependencies=[],
            tags=[topic.lower(), random_input.lower(), "lateral"]
        )
        
        return idea
    
    def _challenge_assumptions(self, topic: str) -> List[str]:
        """Challenge common assumptions about topic."""
        assumptions = [
            f"{topic} must be done manually",
            f"{topic} requires expensive tools",
            f"{topic} takes a long time",
            f"{topic} needs specialized skills",
            f"{topic} can only work one way"
        ]
        
        return assumptions
    
    def _create_challenge_idea(self, topic: str,
                               challenge: str) -> Idea:
        """Create idea that challenges an assumption."""
        self.idea_counter += 1
        
        # Remove "must", "requires", etc.
        challenge_positive = challenge.replace("must", "doesn't have to").replace(
            "requires", "can work without"
        ).replace("takes a long time", "can be done quickly").replace(
            "needs", "doesn't require"
        ).replace("only work one way", "can work multiple ways")
        
        idea = Idea(
            idea_id=f"CHALLENGE_{self.idea_counter:04d}",
            title=challenge_positive,
            description=f"Challenging assumption: {challenge}",
            category="Challenge",
            technique_used="assumption_challenging",
            feasibility=random.uniform(6, 8),
            impact=random.uniform(7, 9),
            novelty=random.uniform(7, 9),
            effort=random.uniform(4, 7),
            pros=["Breaks mental barriers", "Opens new possibilities"],
            cons=["May face resistance"],
            dependencies=[],
            tags=[topic.lower(), "challenge", "innovation"]
        )
        
        return idea
    
    def _apply_scamper_action(self, topic: str,
                             existing_solution: str,
                             action: SCAMPERAction) -> Idea:
        """Apply a SCAMPER action to existing solution."""
        self.idea_counter += 1
        
        action_descriptions = {
            SCAMPERAction.SUBSTITUTE: "Replace components with alternatives",
            SCAMPERAction.COMBINE: "Merge with other solutions",
            SCAMPERAction.ADAPT: "Adjust for different context",
            SCAMPERAction.MODIFY: "Change attributes or features",
            SCAMPERAction.PUT_TO_OTHER_USES: "Use in new applications",
            SCAMPERAction.ELIMINATE: "Remove unnecessary parts",
            SCAMPERAction.REVERSE: "Flip the approach"
        }
        
        idea = Idea(
            idea_id=f"SCAMPER_{action.value}",
            title=f"{action.value.title()}: {topic}",
            description=f"{action_descriptions[action]} - {existing_solution}",
            category="SCAMPER",
            technique_used=f"scamper_{action.value}",
            feasibility=random.uniform(6, 9),
            impact=random.uniform(5, 8),
            novelty=random.uniform(6, 8),
            effort=random.uniform(4, 7),
            pros=[f"Builds on existing solution", f"{action.value.title()} approach"],
            cons=["May need testing", "Could miss opportunities"],
            dependencies=[],
            tags=[topic.lower(), "scamper", action.value]
        )
        
        return idea
    
    def _combine_concepts(self, concept1: str,
                         concept2: str,
                         domain: str) -> Idea:
        """Combine two concepts into innovative idea."""
        self.idea_counter += 1
        
        idea = Idea(
            idea_id=f"CP_{self.idea_counter:04d}",
            title=f"{concept1.title()} + {concept2.title()}",
            description=f"Cross-pollination: Apply {concept1} principles to {concept2} in {domain}",
            category="Cross-Pollination",
            technique_used="cross_pollination",
            feasibility=random.uniform(4, 7),
            impact=random.uniform(6, 9),
            novelty=random.uniform(9, 10),
            effort=random.uniform(6, 9),
            pros=["Highly innovative", "Unique value proposition"],
            cons=["Unproven combination", "Higher risk"],
            dependencies=[],
            tags=[concept1.lower(), concept2.lower(), domain.lower(), "cross-pollination"]
        )
        
        return idea
    
    def _evaluate_idea(self, idea: Idea) -> float:
        """Evaluate and score an idea."""
        # Weighted scoring
        score = (
            idea.feasibility * 0.3 +
            idea.impact * 0.4 +
            idea.novelty * 0.2 +
            (10 - idea.effort) * 0.1
        )
        
        return min(max(score, 0), 10)
    
    def _extract_themes(self, ideas: List[Idea]) -> List[str]:
        """Extract common themes from ideas."""
        tag_counts = defaultdict(int)
        
        for idea in ideas:
            for tag in idea.tags:
                tag_counts[tag] += 1
        
        # Get top themes
        themes = sorted(tag_counts.keys(), key=lambda x: tag_counts[x], reverse=True)
        
        return themes[:5]
    
    def _generate_random_inputs(self) -> List[str]:
        """Generate random input words for lateral thinking."""
        words = [
            "ocean", "robot", "bicycle", "cloud", "tree",
            "music", "fire", "water", "diamond", "rocket",
            "butterfly", "computer", "garden", "mountain", "river"
        ]
        
        return random.sample(words, 5)
    
    def _get_branch_color(self, index: int) -> str:
        """Get color for mind map branch."""
        colors = ["green", "orange", "purple", "brown", "pink", "cyan"]
        return colors[index % len(colors)]


# Convenience functions
def generate_ideas(topic: str, technique: str = "classic",
                  num_ideas: int = 10) -> BrainstormingSession:
    """Generate ideas using specified technique."""
    generator = IdeaGenerator()
    tech_map = {
        "classic": BrainstormingTechnique.CLASSIC,
        "reverse": BrainstormingTechnique.REVERSE,
        "worst": BrainstormingTechnique.WORST_IDEA
    }
    return generator.brainstorm(topic, tech_map.get(technique, BrainstormingTechnique.CLASSIC), num_ideas)


def think_laterally(topic: str, inputs: List[str] = None) -> List[Idea]:
    """Think laterally about a topic."""
    generator = IdeaGenerator()
    return generator.lateral_thinking(topic, inputs)


def apply_scamper(topic: str, solution: str) -> List[Idea]:
    """Apply SCAMPER method."""
    generator = IdeaGenerator()
    return generator.scamper(topic, solution)


def cross_pollinate(concepts: List[str], domain: str = "general") -> List[Idea]:
    """Cross-pollinate concepts."""
    generator = IdeaGenerator()
    return generator.cross_pollinate(concepts, domain)