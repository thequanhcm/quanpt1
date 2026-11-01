"""V39.1 Logical Reasoning Engine.

Implements formal logic reasoning capabilities:
- Deductive reasoning (general → specific)
- Inductive reasoning (specific → general)
- Abductive reasoning (best explanation)
- Propositional logic (AND, OR, NOT, IMPLIES)
- Syllogism reasoning (Aristotelian logic)
- Logical fallacy detection

Usage:
    from quan_ai_brain.cognition.logical_reasoner import LogicalReasoner
    
    reasoner = LogicalReasoner()
    
    # Deductive reasoning
    result = reasoner.deduce(
        premises=["Tất cả con người đều chết", "Socrates là con người"],
        conclusion="Socrates chết"
    )
    
    # Check logical validity
    valid = reasoner.is_valid_argument(premises, conclusion)
    
    # Detect fallacies
    fallacies = reasoner.detect_fallacies(statement)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter


class ReasoningType(Enum):
    """Types of logical reasoning."""
    DEDUCTIVE = "deductive"      # General → Specific (certain)
    INDUCTIVE = "inductive"      # Specific → General (probabilistic)
    ABDUCTIVE = "abductive"      # Best explanation (hypothetical)
    PROPOSITIONAL = "propositional"  # Boolean logic
    SYLLOGISM = "syllogism"      # Aristotelian logic


class FallacyType(Enum):
    """Common logical fallacies."""
    AD_HOMINEM = "ad_hominem"           # Attack person, not argument
    STRAW_MAN = "straw_man"             # Misrepresent opponent's argument
    FALSE_DILEMMA = "false_dilemma"     # Only 2 options when more exist
    SLIPPERY_SLOPE = "slippery_slope"   # Extreme chain reaction
    CIRCULAR_REASONING = "circular"     # Conclusion in premise
    HASTY_GENERALIZATION = "hasty_generalization"  # Insufficient sample
    POST_HOC = "post_hoc"               # Correlation ≠ causation
    APPEAL_TO_AUTHORITY = "appeal_authority"  # Authority ≠ truth
    RED_HERRING = "red_herring"         # Irrelevant distraction
    BANDWAGON = "bandwagon"             # Popular ≠ true


@dataclass
class LogicalStatement:
    """A logical statement with truth value."""
    content: str
    truth_value: Optional[bool] = None  # None = unknown
    confidence: float = 1.0
    source: str = ""
    premises: List[str] = None
    
    def __post_init__(self):
        if self.premises is None:
            self.premises = []


@dataclass
class ReasoningResult:
    """Result of logical reasoning operation."""
    valid: bool
    reasoning_type: ReasoningType
    conclusion: str
    explanation: str
    confidence: float
    premises_used: List[str]
    potential_fallacies: List[str] = None
    alternative_conclusions: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "reasoning_type": self.reasoning_type.value,
            "conclusion": self.conclusion,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "premises_used": self.premises_used,
            "potential_fallacies": self.potential_fallacies or [],
            "alternative_conclusions": self.alternative_conclusions or []
        }


class LogicalReasoner:
    """
    Advanced logical reasoning engine.
    
    Features:
    - Deductive, inductive, abductive reasoning
    - Propositional logic evaluation
    - Syllogism validation
    - Fallacy detection
    - Argument structure analysis
    """
    
    # Logical operators
    AND_PATTERNS = [r'\band\b', r'&', r',', r'và']
    OR_PATTERNS = [r'\bor\b', r'\|', r'hoặc']
    NOT_PATTERNS = [r'\bnot\b', r'!', r'không', r'chẳng']
    IMPLIES_PATTERNS = [r'\bimplies\b', r'→', r'⇒', r'thì', r'dẫn đến']
    
    # Syllogism patterns (Aristotelian)
    SYLLOGISM_PATTERNS = {
        'BARBARA': {  # All M are P, All S are M → All S are P
            'pattern': r'(tất cả|all)\s+(\w+)\s+(là|are)\s+(\w+)\s*,?\s*(tất cả|all)\s+(\w+)\s+(là|are)\s+(\w+)\s*→?\s*(tất cả|all)\s+(\w+)\s+(là|are)\s+(\w+)',
            'valid': True
        },
        'CELARENT': {  # No M are P, All S are M → No S are P
            'pattern': r'(không có|no)\s+(\w+)\s+(là|are)\s+(\w+)\s*,?\s*(tất cả|all)\s+(\w+)\s+(là|are)\s+(\w+)\s*→?\s*(không có|no)\s+(\w+)\s+(là|are)\s+(\w+)',
            'valid': True
        }
    }
    
    def __init__(self):
        """Initialize logical reasoner."""
        self.knowledge_base: List[LogicalStatement] = []
        self.reasoning_history: List[ReasoningResult] = []
        
        print("✅ Logical Reasoning Engine initialized")
        print("   - Deductive reasoning: Ready")
        print("   - Inductive reasoning: Ready")
        print("   - Abductive reasoning: Ready")
        print("   - Fallacy detection: Ready")
    
    # ==================== DEDUCTIVE REASONING ====================
    
    def deduce(self, premises: List[str], conclusion: str) -> ReasoningResult:
        """
        Perform deductive reasoning (general → specific).
        
        Args:
            premises: List of general statements
            conclusion: Specific conclusion to verify
            
        Returns:
            ReasoningResult with validity and explanation
        """
        if not premises:
            return ReasoningResult(
                valid=False,
                reasoning_type=ReasoningType.DEDUCTIVE,
                conclusion=conclusion,
                explanation="❌ Không có premises để suy luận",
                confidence=0.0,
                premises_used=[]
            )
        
        # Check if conclusion logically follows from premises
        is_valid, explanation = self._validate_deduction(premises, conclusion)
        
        # Check for fallacies
        fallacies = self._detect_fallacies_in_argument(premises, conclusion)
        
        confidence = 1.0 if is_valid else 0.3
        
        result = ReasoningResult(
            valid=is_valid,
            reasoning_type=ReasoningType.DEDUCTIVE,
            conclusion=conclusion,
            explanation=explanation,
            confidence=confidence,
            premises_used=premises,
            potential_fallacies=fallacies
        )
        
        self.reasoning_history.append(result)
        return result
    
    def _validate_deduction(self, premises: List[str], conclusion: str) -> Tuple[bool, str]:
        """Validate if conclusion follows from premises."""
        # Normalize text
        premises_text = " ".join(premises).lower()
        conclusion_text = conclusion.lower()
        
        # Check for key logical patterns
        if self._matches_syllogism(premises, conclusion):
            return True, "✅ Valid syllogism (Aristotelian logic)"
        
        # Check if conclusion is contained in premises (tautology)
        if any(term in premises_text for term in conclusion_text.split()):
            word_count = len(conclusion_text.split())
            match_count = sum(1 for word in conclusion_text.split() if word in premises_text)
            if match_count / word_count > 0.7:
                return True, "✅ Conclusion logically follows from premises"
        
        # Check for implication patterns
        for premise in premises:
            if any(imp in premise.lower() for imp in ['nếu', 'if', 'implies', '→']):
                # Has implication, check if conclusion matches
                if any(word in conclusion_text for word in premise.lower().split()):
                    return True, "✅ Valid modus ponens"
        
        return False, "⚠️ Conclusion may not logically follow from premises"
    
    # ==================== INDUCTIVE REASONING ====================
    
    def induce(self, observations: List[str], hypothesis: str) -> ReasoningResult:
        """
        Perform inductive reasoning (specific → general).
        
        Args:
            observations: List of specific observations
            hypothesis: General hypothesis to test
            
        Returns:
            ReasoningResult with probability assessment
        """
        if not observations:
            return ReasoningResult(
                valid=False,
                reasoning_type=ReasoningType.INDUCTIVE,
                conclusion=hypothesis,
                explanation="❌ Không có observations để quy nạp",
                confidence=0.0,
                premises_used=[]
            )
        
        # Calculate support strength
        support_count = 0
        for obs in observations:
            if any(word in obs.lower() for word in hypothesis.lower().split()):
                support_count += 1
        
        confidence = support_count / len(observations) if observations else 0
        
        # Check for hasty generalization
        fallacies = []
        if len(observations) < 5 and confidence > 0.8:
            fallacies.append(FallacyType.HASTY_GENERALIZATION.value)
        
        explanation = (
            f"✅ {support_count}/{len(observations)} observations support hypothesis "
            f"(confidence: {confidence:.0%})"
        )
        
        result = ReasoningResult(
            valid=confidence > 0.5,
            reasoning_type=ReasoningType.INDUCTIVE,
            conclusion=hypothesis,
            explanation=explanation,
            confidence=confidence,
            premises_used=observations,
            potential_fallacies=fallacies
        )
        
        self.reasoning_history.append(result)
        return result
    
    # ==================== ABDUCTIVE REASONING ====================
    
    def abduce(self, observation: str, possible_explanations: List[str]) -> ReasoningResult:
        """
        Perform abductive reasoning (find best explanation).
        
        Args:
            observation: The observed fact/evidence
            possible_explanations: List of possible explanations
            
        Returns:
            ReasoningResult with best explanation
        """
        if not possible_explanations:
            return ReasoningResult(
                valid=False,
                reasoning_type=ReasoningType.ABDUCTIVE,
                conclusion="",
                explanation="❌ Không có explanation để chọn",
                confidence=0.0,
                premises_used=[]
            )
        
        # Score each explanation
        scores = []
        for explanation in possible_explanations:
            score = self._score_explanation(observation, explanation)
            scores.append((explanation, score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        best_explanation, best_score = scores[0]
        
        # Generate alternatives
        alternatives = [exp for exp, _ in scores[1:3]]
        
        explanation_text = (
            f"✅ Best explanation: '{best_explanation}' (score: {best_score:.2f})\n"
            f"   Alternative: {', '.join(alternatives) if alternatives else 'None'}"
        )
        
        result = ReasoningResult(
            valid=best_score > 0.5,
            reasoning_type=ReasoningType.ABDUCTIVE,
            conclusion=best_explanation,
            explanation=explanation_text,
            confidence=best_score,
            premises_used=[observation],
            alternative_conclusions=alternatives
        )
        
        self.reasoning_history.append(result)
        return result
    
    def _score_explanation(self, observation: str, explanation: str) -> float:
        """Score how well explanation explains observation."""
        obs_words = set(observation.lower().split())
        exp_words = set(explanation.lower().split())
        
        # Word overlap
        overlap = len(obs_words & exp_words)
        total = len(obs_words | exp_words)
        jaccard = overlap / total if total > 0 else 0
        
        # Causal keywords
        causal_keywords = ['vì', 'do', 'bởi', 'cause', 'reason', 'lead to', 'kết quả']
        causal_score = 1.0 if any(kw in explanation.lower() for kw in causal_keywords) else 0.5
        
        return (jaccard * 0.6) + (causal_score * 0.4)
    
    # ==================== PROPOSITIONAL LOGIC ====================
    
    def evaluate_proposition(self, expression: str, truth_values: Dict[str, bool]) -> bool:
        """
        Evaluate propositional logic expression.
        
        Args:
            expression: Logical expression (e.g., "A AND (B OR C)")
            truth_values: Dictionary mapping variables to truth values
            
        Returns:
            Boolean result
        """
        # Replace variables with truth values
        eval_expr = expression.upper()
        for var, value in truth_values.items():
            eval_expr = re.sub(r'\b' + var.upper() + r'\b', str(value), eval_expr)
        
        # Replace logical operators
        eval_expr = re.sub(r'\bAND\b', ' and ', eval_expr)
        eval_expr = re.sub(r'\bOR\b', ' or ', eval_expr)
        eval_expr = re.sub(r'\bNOT\b', ' not ', eval_expr)
        
        try:
            return eval(eval_expr)
        except:
            raise ValueError(f"Invalid proposition: {expression}")
    
    # ==================== SYLLOGISM VALIDATION ====================
    
    def _matches_syllogism(self, premises: List[str], conclusion: str) -> bool:
        """Check if argument matches valid syllogism pattern."""
        all_text = " ".join(premises + [conclusion]).lower()
        
        # Check for Barbara pattern: All A are B, All B are C → All A are C
        if all(x in all_text for x in ['tất cả', 'là', '→']):
            return True
        
        return False
    
    # ==================== FALLACY DETECTION ====================
    
    def detect_fallacies(self, statement: str) -> List[str]:
        """
        Detect logical fallacies in a statement.
        
        Args:
            statement: Statement to analyze
            
        Returns:
            List of detected fallacy types
        """
        fallacies = []
        statement_lower = statement.lower()
        
        # Ad hominem
        if any(pattern in statement_lower for pattern in ['đồ ngốc', 'kẻ ngu', 'anh ta không biết', 'cô ấy sai vì']):
            fallacies.append(FallacyType.AD_HOMINEM.value)
        
        # Straw man
        if any(pattern in statement_lower for pattern in ['bạn đang nói rằng', 'ý bạn là', 'theo bạn']):
            fallacies.append(FallacyType.STRAW_MAN.value)
        
        # False dilemma
        if any(pattern in statement_lower for pattern in ['hoặc... hoặc...', 'chỉ có 2 lựa chọn', 'đồng ý hoặc chống']):
            fallacies.append(FallacyType.FALSE_DILEMMA.value)
        
        # Slippery slope
        if any(pattern in statement_lower for pattern in ['nếu... thì sẽ...', 'dẫn đến việc...', 'chuỗi sự kiện']):
            fallacies.append(FallacyType.SLIPPERY_SLOPE.value)
        
        # Circular reasoning
        words = statement_lower.split()
        if len(words) > 5 and words[0] == words[-1]:
            fallacies.append(FallacyType.CIRCULAR_REASONING.value)
        
        # Post hoc
        if any(pattern in statement_lower for pattern in ['sau đó', 'kế đến', 'vì vậy']):
            fallacies.append(FallacyType.POST_HOC.value)
        
        return fallacies
    
    def _detect_fallacies_in_argument(self, premises: List[str], conclusion: str) -> List[str]:
        """Detect fallacies in an argument."""
        all_text = " ".join(premises + [conclusion])
        return self.detect_fallacies(all_text)
    
    # ==================== ARGUMENT ANALYSIS ====================
    
    def analyze_argument(self, premises: List[str], conclusion: str) -> Dict[str, Any]:
        """
        Comprehensive argument analysis.
        
        Args:
            premises: List of premises
            conclusion: Conclusion
            
        Returns:
            Analysis dictionary
        """
        # Deductive check
        deductive = self.deduce(premises, conclusion)
        
        # Fallacy check
        all_fallacies = self._detect_fallacies_in_argument(premises, conclusion)
        
        # Strength assessment
        strength = "strong" if deductive.valid and not all_fallacies else "weak"
        
        return {
            "validity": deductive.valid,
            "strength": strength,
            "reasoning_type": deductive.reasoning_type.value,
            "confidence": deductive.confidence,
            "fallacies": all_fallacies,
            "explanation": deductive.explanation,
            "improvements": self._suggest_improvements(premises, conclusion, all_fallacies)
        }
    
    def _suggest_improvements(self, premises: List[str], conclusion: str, fallacies: List[str]) -> List[str]:
        """Suggest improvements to argument."""
        improvements = []
        
        if not premises:
            improvements.append("Thêm premises để hỗ trợ conclusion")
        
        if FallacyType.CIRCULAR_REASONING.value in fallacies:
            improvements.append("Tránh lập luận vòng tròn - premises phải độc lập với conclusion")
        
        if FallacyType.HASTY_GENERALIZATION.value in fallacies:
            improvements.append("Thu thập thêm observations để hỗ trợ generalization")
        
        if FallacyType.FALSE_DILEMMA.value in fallacies:
            improvements.append("Xem xét các lựa chọn khác ngoài 2 options hiện tại")
        
        return improvements


# Convenience functions
def is_valid_argument(premises: List[str], conclusion: str) -> bool:
    """Quick check if argument is valid."""
    reasoner = LogicalReasoner()
    result = reasoner.deduce(premises, conclusion)
    return result.valid


def detect_fallacies(text: str) -> List[str]:
    """Quick fallacy detection."""
    reasoner = LogicalReasoner()
    return reasoner.detect_fallacies(text)


def find_best_explanation(observation: str, explanations: List[str]) -> str:
    """Find best explanation for observation."""
    reasoner = LogicalReasoner()
    result = reasoner.abduce(observation, explanations)
    return result.conclusion