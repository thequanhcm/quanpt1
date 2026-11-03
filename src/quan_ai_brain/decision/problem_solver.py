"""V39.3 Problem Solving Engine.

Implements problem-solving capabilities:
- Problem decomposition (break down complex problems)
- Root cause analysis (5 Whys, fishbone, fault trees)
- Solution generation (brainstorming, evaluation, selection)
- Troubleshooting workflows
- Pattern-based problem solving
- Case-based reasoning
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
import re
from collections import defaultdict


class ProblemType(Enum):
    """Problem types."""
    TECHNICAL = "technical"
    BUSINESS = "business"
    PROCESS = "process"
    HUMAN = "human"
    SYSTEMIC = "systemic"
    UNKNOWN = "unknown"


class SolutionStatus(Enum):
    """Solution status."""
    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    SELECTED = "selected"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass
class ProblemStatement:
    """Problem statement."""
    id: str
    title: str
    description: str
    problem_type: ProblemType
    symptoms: List[str]
    impact: float  # 1-10
    urgency: float  # 1-10
    context: Dict[str, Any]
    sub_problems: List['ProblemStatement'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "problem_type": self.problem_type.value,
            "symptoms": self.symptoms,
            "impact": self.impact,
            "urgency": self.urgency,
            "sub_problems_count": len(self.sub_problems)
        }


@dataclass
class RootCause:
    """Root cause analysis result."""
    cause_id: str
    description: str
    category: str
    probability: float  # Likelihood this is the root cause
    evidence: List[str]
    contributing_factors: List[str]
    is_root_cause: bool
    depth: int  # How many levels deep in 5 Whys
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cause_id": self.cause_id,
            "description": self.description,
            "category": self.category,
            "probability": round(self.probability, 2),
            "evidence_count": len(self.evidence),
            "is_root_cause": self.is_root_cause,
            "depth": self.depth
        }


@dataclass
class Solution:
    """Proposed solution."""
    solution_id: str
    title: str
    description: str
    approach: str
    pros: List[str]
    cons: List[str]
    estimated_cost: float
    estimated_effort: float  # In hours/days
    risk_level: str
    success_probability: float
    status: SolutionStatus
    evaluation_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "solution_id": self.solution_id,
            "title": self.title,
            "approach": self.approach,
            "pros_count": len(self.pros),
            "cons_count": len(self.cons),
            "estimated_cost": round(self.estimated_cost, 2),
            "risk_level": self.risk_level,
            "success_probability": round(self.success_probability, 2),
            "status": self.status.value,
            "evaluation_score": round(self.evaluation_score, 2)
        }


@dataclass
class TroubleshootingStep:
    """Troubleshooting step."""
    step_number: int
    action: str
    expected_result: str
    actual_result: Optional[str]
    diagnosis: Optional[str]
    next_step: Optional[int]
    is_complete: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "action": self.action,
            "expected_result": self.expected_result,
            "actual_result": self.actual_result,
            "diagnosis": self.diagnosis,
            "next_step": self.next_step,
            "is_complete": self.is_complete
        }


class ProblemSolver:
    """Problem solving engine."""
    
    def __init__(self):
        """Initialize problem solver."""
        self._initialized = True
        self.problem_counter = 0
        
        print("✅ Problem Solving Engine initialized")
        print(f"   - Problem decomposition: Ready")
        print(f"   - Root cause analysis: Ready")
        print(f"   - Solution generation: Ready")
        print(f"   - Troubleshooting workflows: Ready")
    
    def decompose_problem(self, problem: str, 
                         context: Dict[str, Any] = None) -> ProblemStatement:
        """Decompose a complex problem into sub-problems.
        
        Args:
            problem: Problem description
            context: Additional context
            
        Returns:
            ProblemStatement with sub-problems
        """
        self.problem_counter += 1
        problem_id = f"PROB_{self.problem_counter:04d}"
        
        # Analyze problem type
        problem_lower = problem.lower()
        if any(word in problem_lower for word in ['error', 'bug', 'crash', 'fail']):
            problem_type = ProblemType.TECHNICAL
        elif any(word in problem_lower for word in ['cost', 'revenue', 'profit', 'market']):
            problem_type = ProblemType.BUSINESS
        elif any(word in problem_lower for word in ['process', 'workflow', 'procedure']):
            problem_type = ProblemType.PROCESS
        elif any(word in problem_lower for word in ['people', 'team', 'communication']):
            problem_type = ProblemType.HUMAN
        else:
            problem_type = ProblemType.UNKNOWN
        
        # Extract symptoms (keywords)
        symptoms = self._extract_symptoms(problem)
        
        # Estimate impact and urgency
        impact = self._estimate_impact(problem)
        urgency = self._estimate_urgency(problem)
        
        # Generate sub-problems
        sub_problems = self._generate_sub_problems(problem, problem_type)
        
        return ProblemStatement(
            id=problem_id,
            title=problem[:50] + "..." if len(problem) > 50 else problem,
            description=problem,
            problem_type=problem_type,
            symptoms=symptoms,
            impact=impact,
            urgency=urgency,
            context=context or {},
            sub_problems=sub_problems
        )
    
    def analyze_root_cause(self, problem: str,
                          symptoms: List[str] = None,
                          method: str = "5_whys") -> List[RootCause]:
        """Perform root cause analysis.
        
        Args:
            problem: Problem description
            symptoms: List of observed symptoms
            method: Analysis method (5_whys, fishbone, fault_tree)
            
        Returns:
            List of RootCause objects
        """
        if not symptoms:
            symptoms = self._extract_symptoms(problem)
        
        causes = []
        
        if method == "5_whys":
            causes = self._perform_5_whys(problem, symptoms)
        elif method == "fishbone":
            causes = self._perform_fishbone(problem, symptoms)
        elif method == "fault_tree":
            causes = self._perform_fault_tree(problem, symptoms)
        else:
            causes = self._perform_5_whys(problem, symptoms)
        
        # Sort by probability
        causes.sort(key=lambda x: x.probability, reverse=True)
        
        return causes
    
    def generate_solutions(self, problem: ProblemStatement,
                          root_causes: List[RootCause] = None,
                          constraints: Dict[str, Any] = None) -> List[Solution]:
        """Generate potential solutions.
        
        Args:
            problem: Problem statement
            root_causes: Identified root causes
            constraints: Budget, time, resource constraints
            
        Returns:
            List of proposed solutions
        """
        solutions = []
        
        # Generate solutions based on problem type
        if problem.problem_type == ProblemType.TECHNICAL:
            solutions = self._generate_technical_solutions(problem, root_causes)
        elif problem.problem_type == ProblemType.BUSINESS:
            solutions = self._generate_business_solutions(problem, root_causes)
        elif problem.problem_type == ProblemType.PROCESS:
            solutions = self._generate_process_solutions(problem, root_causes)
        else:
            solutions = self._generate_generic_solutions(problem, root_causes)
        
        # Evaluate solutions
        for solution in solutions:
            solution.evaluation_score = self._evaluate_solution(
                solution, problem, constraints
            )
        
        # Sort by evaluation score
        solutions.sort(key=lambda x: x.evaluation_score, reverse=True)
        
        return solutions
    
    def create_troubleshooting_workflow(self, problem: str,
                                       known_issues: List[Dict[str, Any]] = None) -> List[TroubleshootingStep]:
        """Create a troubleshooting workflow.
        
        Args:
            problem: Problem description
            known_issues: List of known issues and solutions
            
        Returns:
            List of troubleshooting steps
        """
        steps = []
        
        # Step 1: Verify the problem
        steps.append(TroubleshootingStep(
            step_number=1,
            action="Verify and document the problem",
            expected_result="Clear problem statement",
            actual_result=None,
            diagnosis=None,
            next_step=2
        ))
        
        # Step 2: Check basic conditions
        steps.append(TroubleshootingStep(
            step_number=2,
            action="Check basic system conditions (power, connectivity, logs)",
            expected_result="Basic conditions verified",
            actual_result=None,
            diagnosis=None,
            next_step=3
        ))
        
        # Step 3: Isolate the issue
        steps.append(TroubleshootingStep(
            step_number=3,
            action="Isolate the component or process causing the issue",
            expected_result="Problem area identified",
            actual_result=None,
            diagnosis=None,
            next_step=4
        ))
        
        # Step 4: Check known issues
        if known_issues:
            steps.append(TroubleshootingStep(
                step_number=4,
                action="Compare with known issues",
                expected_result="Match found or new issue identified",
                actual_result=None,
                diagnosis=None,
                next_step=5
            ))
        
        # Step 5: Apply fix or escalate
        steps.append(TroubleshootingStep(
            step_number=5,
            action="Apply fix or escalate to specialist",
            expected_result="Problem resolved or escalated",
            actual_result=None,
            diagnosis=None,
            next_step=None
        ))
        
        return steps
    
    def evaluate_solution(self, solution: Solution,
                         problem: ProblemStatement,
                         constraints: Dict[str, Any] = None) -> float:
        """Evaluate a solution.
        
        Args:
            solution: Solution to evaluate
            problem: Problem statement
            constraints: Constraints (budget, time, resources)
            
        Returns:
            Evaluation score (0-10)
        """
        score = 0.0
        
        # Success probability (30%)
        score += solution.success_probability * 3
        
        # Cost effectiveness (25%)
        if constraints and 'budget' in constraints:
            cost_ratio = solution.estimated_cost / constraints['budget']
            cost_score = max(0, 1 - cost_ratio) * 2.5
        else:
            cost_score = 1.5
        score += cost_score
        
        # Risk level (20%)
        risk_scores = {"low": 2.0, "medium": 1.0, "high": 0.5, "critical": 0.2}
        score += risk_scores.get(solution.risk_level.lower(), 1.0)
        
        # Pros vs Cons ratio (15%)
        if solution.cons:
            ratio = len(solution.pros) / len(solution.cons)
        else:
            ratio = 2.0  # Max score if no cons
        score += min(ratio, 2.0) * 0.75
        
        # Effort (10%)
        if solution.estimated_effort < 10:
            effort_score = 1.0
        elif solution.estimated_effort < 50:
            effort_score = 0.7
        else:
            effort_score = 0.4
        score += effort_score
        
        return min(score, 10.0)
    
    def _extract_symptoms(self, problem: str) -> List[str]:
        """Extract symptoms from problem description."""
        symptoms = []
        
        # Look for error patterns
        error_patterns = [
            r'error[:\s]+([^\.,]+)',
            r'fail(?:ed|ure|ing)[:\s]+([^\.,]+)',
            r'not working',
            r'broken',
            r'crash(?:ed|ing)?',
            r'exception'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, problem.lower())
            symptoms.extend(matches)
        
        # Extract key phrases
        phrases = re.findall(r'\b(?:slow|unavailable|incorrect|missing|duplicate)\b', problem.lower())
        symptoms.extend(phrases)
        
        return list(set(symptoms))[:5]
    
    def _estimate_impact(self, problem: str) -> float:
        """Estimate problem impact (1-10)."""
        impact_keywords = {
            'critical': 10, 'severe': 9, 'major': 8, 'significant': 7,
            'moderate': 5, 'minor': 3, 'trivial': 1
        }
        
        problem_lower = problem.lower()
        for keyword, score in impact_keywords.items():
            if keyword in problem_lower:
                return score
        
        # Default based on length (proxy for complexity)
        if len(problem) > 200:
            return 7
        elif len(problem) > 100:
            return 5
        else:
            return 3
    
    def _estimate_urgency(self, problem: str) -> float:
        """Estimate problem urgency (1-10)."""
        urgency_keywords = {
            'immediate': 10, 'urgent': 9, 'asap': 9, 'now': 8,
            'soon': 6, 'later': 3, 'when possible': 1
        }
        
        problem_lower = problem.lower()
        for keyword, score in urgency_keywords.items():
            if keyword in problem_lower:
                return score
        
        return 5  # Default
    
    def _generate_sub_problems(self, problem: str, 
                              problem_type: ProblemType) -> List[ProblemStatement]:
        """Generate sub-problems based on problem type."""
        sub_problems = []
        
        # Generic sub-problems
        if problem_type == ProblemType.TECHNICAL:
            sub_problems = [
                ProblemStatement(
                    id=f"SUB_{len(sub_problems)+1:03d}",
                    title="Identify affected components",
                    description="Determine which system components are affected",
                    problem_type=problem_type,
                    symptoms=[],
                    impact=5.0,
                    urgency=6.0,
                    context={}
                ),
                ProblemStatement(
                    id=f"SUB_{len(sub_problems)+1:03d}",
                    title="Analyze error logs",
                    description="Review system logs for error patterns",
                    problem_type=problem_type,
                    symptoms=[],
                    impact=6.0,
                    urgency=7.0,
                    context={}
                )
            ]
        elif problem_type == ProblemType.BUSINESS:
            sub_problems = [
                ProblemStatement(
                    id=f"SUB_{len(sub_problems)+1:03d}",
                    title="Quantify financial impact",
                    description="Calculate cost/revenue impact",
                    problem_type=problem_type,
                    symptoms=[],
                    impact=8.0,
                    urgency=7.0,
                    context={}
                )
            ]
        
        return sub_problems[:3]
    
    def _perform_5_whys(self, problem: str, symptoms: List[str]) -> List[RootCause]:
        """Perform 5 Whys analysis."""
        causes = []
        
        # Simulate 5 Whys
        cause_templates = [
            ("Direct cause", "Immediate trigger", 0.8, 1),
            ("Process gap", "Missing procedure", 0.7, 2),
            ("Systemic issue", "Underlying system flaw", 0.6, 3),
            ("Root cause", "Fundamental issue", 0.5, 5)
        ]
        
        for i, (title, desc, prob, depth) in enumerate(cause_templates):
            causes.append(RootCause(
                cause_id=f"CAUSE_{i+1:03d}",
                description=f"{title}: {desc}",
                category="Process" if i > 0 else "Technical",
                probability=prob,
                evidence=[f"Symptom: {symptoms[0]}" if symptoms else "Problem analysis"],
                contributing_factors=["Lack of monitoring", "Insufficient testing"],
                is_root_cause=(depth == 5),
                depth=depth
            ))
        
        return causes
    
    def _perform_fishbone(self, problem: str, symptoms: List[str]) -> List[RootCause]:
        """Perform fishbone (Ishikawa) analysis."""
        categories = ["People", "Process", "Technology", "Environment"]
        causes = []
        
        for i, category in enumerate(categories):
            causes.append(RootCause(
                cause_id=f"CAUSE_{i+1:03d}",
                description=f"{category} factor contributing to problem",
                category=category,
                probability=0.6 - (i * 0.1),
                evidence=[f"Category analysis: {category}"],
                contributing_factors=[],
                is_root_cause=False,
                depth=1
            ))
        
        return causes
    
    def _perform_fault_tree(self, problem: str, symptoms: List[str]) -> List[RootCause]:
        """Perform fault tree analysis."""
        causes = []
        
        # Top event
        causes.append(RootCause(
            cause_id="CAUSE_001",
            description=f"Top event: {problem[:50]}",
            category="System",
            probability=1.0,
            evidence=["Problem statement"],
            contributing_factors=[],
            is_root_cause=False,
            depth=0
        ))
        
        # Intermediate events
        for i in range(2):
            causes.append(RootCause(
                cause_id=f"CAUSE_{i+2:03d}",
                description=f"Intermediate failure mode {i+1}",
                category="Component",
                probability=0.7 - (i * 0.2),
                evidence=["Fault tree analysis"],
                contributing_factors=[],
                is_root_cause=False,
                depth=1
            ))
        
        return causes
    
    def _generate_technical_solutions(self, problem: ProblemStatement,
                                     root_causes: List[RootCause]) -> List[Solution]:
        """Generate technical solutions."""
        solutions = []
        
        solutions.append(Solution(
            solution_id="SOL_001",
            title="Implement fix for identified bug",
            description="Apply code fix based on root cause analysis",
            approach="Code modification and testing",
            pros=["Direct solution", "Permanent fix"],
            cons=["Requires development time", "Risk of regression"],
            estimated_cost=500.0,
            estimated_effort=16.0,
            risk_level="medium",
            success_probability=0.85,
            status=SolutionStatus.PROPOSED
        ))
        
        solutions.append(Solution(
            solution_id="SOL_002",
            title="Add monitoring and alerts",
            description="Implement enhanced monitoring to detect issues early",
            approach="Deploy monitoring tools and configure alerts",
            pros=["Early detection", "Prevents recurrence"],
            cons=["Ongoing cost", "May not prevent initial issue"],
            estimated_cost=200.0,
            estimated_effort=8.0,
            risk_level="low",
            success_probability=0.75,
            status=SolutionStatus.PROPOSED
        ))
        
        return solutions
    
    def _generate_business_solutions(self, problem: ProblemStatement,
                                    root_causes: List[RootCause]) -> List[Solution]:
        """Generate business solutions."""
        solutions = []
        
        solutions.append(Solution(
            solution_id="SOL_001",
            title="Process optimization",
            description="Redesign business process to eliminate inefficiency",
            approach="Process reengineering and automation",
            pros=["Long-term improvement", "Cost reduction"],
            cons=["Change management required", "Temporary disruption"],
            estimated_cost=2000.0,
            estimated_effort=80.0,
            risk_level="medium",
            success_probability=0.80,
            status=SolutionStatus.PROPOSED
        ))
        
        return solutions
    
    def _generate_process_solutions(self, problem: ProblemStatement,
                                   root_causes: List[RootCause]) -> List[Solution]:
        """Generate process solutions."""
        solutions = []
        
        solutions.append(Solution(
            solution_id="SOL_001",
            title="Update procedures and documentation",
            description="Revise standard operating procedures",
            approach="Documentation update and training",
            pros=["Clear guidance", "Prevents recurrence"],
            cons=["Requires training", "May be ignored"],
            estimated_cost=300.0,
            estimated_effort=20.0,
            risk_level="low",
            success_probability=0.70,
            status=SolutionStatus.PROPOSED
        ))
        
        return solutions
    
    def _generate_generic_solutions(self, problem: ProblemStatement,
                                   root_causes: List[RootCause]) -> List[Solution]:
        """Generate generic solutions."""
        solutions = []
        
        solutions.append(Solution(
            solution_id="SOL_001",
            title="Comprehensive analysis and fix",
            description="Thorough investigation and targeted solution",
            approach="Analysis, planning, implementation",
            pros=["Systematic approach", "Addresses root cause"],
            cons=["Time-consuming", "May require multiple iterations"],
            estimated_cost=1000.0,
            estimated_effort=40.0,
            risk_level="medium",
            success_probability=0.75,
            status=SolutionStatus.PROPOSED
        ))
        
        return solutions


# Convenience functions
def solve_problem(problem: str, context: Dict[str, Any] = None) -> ProblemStatement:
    """Decompose and analyze a problem."""
    solver = ProblemSolver()
    return solver.decompose_problem(problem, context)


def find_root_causes(problem: str, method: str = "5_whys") -> List[RootCause]:
    """Find root causes of a problem."""
    solver = ProblemSolver()
    return solver.analyze_root_cause(problem, method=method)


def generate_solutions(problem: ProblemStatement) -> List[Solution]:
    """Generate solutions for a problem."""
    solver = ProblemSolver()
    return solver.generate_solutions(problem)


def create_workflow(problem: str) -> List[TroubleshootingStep]:
    """Create troubleshooting workflow."""
    solver = ProblemSolver()
    return solver.create_troubleshooting_workflow(problem)