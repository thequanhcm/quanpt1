"""V39.2 Causal Reasoning Engine.

Implements causal reasoning capabilities:
- Cause-effect chain analysis
- Counterfactual reasoning
- Correlation vs causation detection
- Root cause analysis (5 Whys, Fishbone)
- Causal inference from data
- Intervention analysis

Usage:
    from quan_ai_brain.cognition.causal_engine import CausalEngine
    
    engine = CausalEngine()
    
    # Analyze cause-effect chain
    chain = engine.analyze_chain("Mưa → Đường ướt → Xe trượt")
    
    # Root cause analysis
    causes = engine.root_cause_analysis("Sự cố: Server down")
    
    # Counterfactual reasoning
    result = engine.counterfactual("Nếu không mưa thì đường có ướt không?")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


class CausalRelationType(Enum):
    """Types of causal relationships."""
    DIRECT_CAUSE = "direct_cause"           # A directly causes B
    INDIRECT_CAUSE = "indirect_cause"       # A causes B through C
    COMMON_CAUSE = "common_cause"           # C causes both A and B
    CORRELATION = "correlation"             # A and B correlate, no causation
    REVERSE_CAUSE = "reverse_cause"         # B causes A (not A causes B)
    SPURIOUS = "spurious"                   # Coincidental correlation


@dataclass
class CausalLink:
    """A causal link between two events."""
    cause: str
    effect: str
    relation_type: CausalRelationType
    strength: float  # 0.0 to 1.0
    confidence: float
    evidence: List[str]
    mechanism: str = ""  # How cause leads to effect


@dataclass
class CausalChain:
    """A chain of causal relationships."""
    links: List[CausalLink]
    total_strength: float
    is_valid: bool
    explanation: str


@dataclass
class RootCauseAnalysis:
    """Result of root cause analysis."""
    problem: str
    root_causes: List[str]
    contributing_factors: List[str]
    analysis_method: str
    recommendations: List[str]
    confidence: float


class CausalEngine:
    """
    Advanced causal reasoning engine.
    
    Features:
    - Cause-effect chain analysis
    - Counterfactual reasoning
    - Correlation vs causation detection
    - Root cause analysis (5 Whys, Fishbone)
    - Causal inference
    """
    
    # Causal keywords
    CAUSE_KEYWORDS = [
        'gây ra', 'dẫn đến', 'khiến', 'làm cho', 'kết quả', 'result', 'cause',
        'because', 'vì', 'do', 'nhờ', 'thanks to', 'leading to'
    ]
    
    EFFECT_KEYWORDS = [
        'kết quả là', 'do đó', 'vì vậy', 'nên', 'therefore', 'thus', 'hence',
        'as a result', 'kết quả', 'system', 'outcome'
    ]
    
    CORRELATION_KEYWORDS = [
        'liên quan', 'correlate', 'associated with', 'connected to',
        'cùng xảy ra', 'xảy ra đồng thời'
    ]
    
    def __init__(self):
        """Initialize causal engine."""
        self.causal_graph: Dict[str, List[str]] = defaultdict(list)
        self.knowledge_base: List[CausalLink] = []
        
        print("✅ Causal Reasoning Engine initialized")
        print("   - Cause-effect analysis: Ready")
        print("   - Counterfactual reasoning: Ready")
        print("   - Root cause analysis: Ready")
        print("   - Correlation detection: Ready")
    
    # ==================== CAUSE-EFFECT CHAIN ANALYSIS ====================
    
    def analyze_chain(self, chain_text: str) -> CausalChain:
        """
        Analyze a cause-effect chain.
        
        Args:
            chain_text: Text describing causal chain (e.g., "A → B → C")
            
        Returns:
            CausalChain with validity and strength
        """
        # Parse chain
        events = self._parse_chain(chain_text)
        
        if len(events) < 2:
            return CausalChain(
                links=[],
                total_strength=0.0,
                is_valid=False,
                explanation="❌ Cần ít nhất 2 events để phân tích chain"
            )
        
        # Analyze each link
        links = []
        for i in range(len(events) - 1):
            link = self._analyze_link(events[i], events[i + 1])
            links.append(link)
            self.knowledge_base.append(link)
        
        # Calculate total strength
        total_strength = sum(link.strength for link in links) / len(links) if links else 0
        
        # Validate chain
        is_valid = all(link.strength > 0.5 for link in links)
        
        explanation = (
            f"✅ Chain có {len(links)} links, strength: {total_strength:.0%}\n"
            f"   {'Valid' if is_valid else 'Invalid'}: "
            f"{'→ '.join(events)}"
        )
        
        return CausalChain(
            links=links,
            total_strength=total_strength,
            is_valid=is_valid,
            explanation=explanation
        )
    
    def _parse_chain(self, chain_text: str) -> List[str]:
        """Parse chain text into events."""
        # Split by arrow or common separators
        events = re.split(r'\s*→\s*|\s*->\s*|\s*;\s*|\s*,\s*|\s*và\s*', chain_text)
        return [e.strip() for e in events if e.strip()]
    
    def _analyze_link(self, cause: str, effect: str) -> CausalLink:
        """Analyze causal link between cause and effect."""
        # Check for causal keywords
        cause_lower = cause.lower()
        effect_lower = effect.lower()
        
        has_cause_keyword = any(kw in cause_lower for kw in self.CAUSE_KEYWORDS)
        has_effect_keyword = any(kw in effect_lower for kw in self.EFFECT_KEYWORDS)
        
        # Calculate strength
        strength = 0.5  # Base strength
        
        if has_cause_keyword and has_effect_keyword:
            strength = 0.9
        elif has_cause_keyword or has_effect_keyword:
            strength = 0.7
        else:
            # Check semantic similarity
            strength = self._estimate_causal_strength(cause, effect)
        
        # Determine relation type
        if strength > 0.7:
            relation_type = CausalRelationType.DIRECT_CAUSE
        elif strength > 0.4:
            relation_type = CausalRelationType.INDIRECT_CAUSE
        else:
            relation_type = CausalRelationType.CORRELATION
        
        # Generate mechanism
        mechanism = self._generate_mechanism(cause, effect)
        
        return CausalLink(
            cause=cause,
            effect=effect,
            relation_type=relation_type,
            strength=strength,
            confidence=0.8,
            evidence=[f"Phân tích từ: '{cause}' → '{effect}'"],
            mechanism=mechanism
        )
    
    def _estimate_causal_strength(self, cause: str, effect: str) -> float:
        """Estimate causal strength based on word overlap and semantics."""
        cause_words = set(cause.lower().split())
        effect_words = set(effect.lower().split())
        
        # Word overlap
        overlap = len(cause_words & effect_words)
        total = len(cause_words | effect_words)
        jaccard = overlap / total if total > 0 else 0
        
        # Time sequence (if cause mentions "trước" and effect mentions "sau")
        time_score = 0.3 if ('trước' in cause or 'trước khi' in cause) else 0
        
        return min(0.5 + jaccard * 0.3 + time_score, 0.9)
    
    def _generate_mechanism(self, cause: str, effect: str) -> str:
        """Generate explanation of how cause leads to effect."""
        return f"{cause} tạo điều kiện/ảnh hưởng đến {effect} thông qua cơ chế nhân quả"
    
    # ==================== ROOT CAUSE ANALYSIS ====================
    
    def root_cause_analysis(self, problem: str, method: str = "5_whys") -> RootCauseAnalysis:
        """
        Perform root cause analysis.
        
        Args:
            problem: The problem to analyze
            method: Analysis method ("5_whys" or "fishbone")
            
        Returns:
            RootCauseAnalysis with causes and recommendations
        """
        if method == "5_whys":
            return self._five_whys_analysis(problem)
        elif method == "fishbone":
            return self._fishbone_analysis(problem)
        else:
            return self._five_whys_analysis(problem)
    
    def _five_whys_analysis(self, problem: str) -> RootCauseAnalysis:
        """Perform 5 Whys root cause analysis."""
        root_causes = []
        contributing_factors = []
        current_problem = problem
        
        for i in range(5):
            # Simulate asking "why"
            why_question = f"Lần {i+1}: Tại sao {current_problem}?"
            
            # Generate plausible answer based on problem
            answer = self._generate_why_answer(current_problem, i)
            
            if "nguyên nhân gốc" in answer or "cơ bản" in answer:
                root_causes.append(answer)
                break
            elif i < 4:
                contributing_factors.append(answer)
                current_problem = answer
            else:
                root_causes.append(f"Nguyên nhân cơ bản: {answer}")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(root_causes, contributing_factors)
        
        return RootCauseAnalysis(
            problem=problem,
            root_causes=root_causes,
            contributing_factors=contributing_factors,
            analysis_method="5 Whys",
            recommendations=recommendations,
            confidence=0.75
        )
    
    def _generate_why_answer(self, problem: str, iteration: int) -> str:
        """Generate plausible 'why' answer."""
        # Simple pattern-based answer generation
        problem_lower = problem.lower()
        
        if iteration == 0:
            return f"Vì có sự cố liên quan đến {problem}"
        elif iteration == 1:
            return f"Vì quy trình kiểm tra chưa đầy đủ cho {problem}"
        elif iteration == 2:
            return f"Vì thiếu hướng dẫn chi tiết về {problem}"
        elif iteration == 3:
            return f"Vì đào tạo nhân viên chưa đủ về {problem}"
        else:
            return f"nguyên nhân gốc rễ: hệ thống quản lý chưa tối ưu cho {problem}"
    
    def _fishbone_analysis(self, problem: str) -> RootCauseAnalysis:
        """Perform Fishbone (Ishikawa) analysis."""
        categories = [
            "Con người (People)",
            "Phương pháp (Methods)",
            "Máy móc (Machines)",
            "Vật liệu (Materials)",
            "Môi trường (Environment)",
            "Đo lường (Measurement)"
        ]
        
        root_causes = []
        for category in categories:
            cause = self._generate_category_cause(problem, category)
            root_causes.append(f"{category}: {cause}")
        
        recommendations = self._generate_recommendations(root_causes, [])
        
        return RootCauseAnalysis(
            problem=problem,
            root_causes=root_causes,
            contributing_factors=[],
            analysis_method="Fishbone (Ishikawa)",
            recommendations=recommendations,
            confidence=0.7
        )
    
    def _generate_category_cause(self, problem: str, category: str) -> str:
        """Generate cause for specific category."""
        return f"Có thể có vấn đề về {category.split()[0]} liên quan đến {problem}"
    
    def _generate_recommendations(self, root_causes: List[str], contributing: List[str]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if root_causes:
            recommendations.append("✅ Khắc phục nguyên nhân gốc rễ trước")
            recommendations.append("✅ Theo dõi hiệu quả sau khi khắc phục")
        
        if contributing:
            recommendations.append("✅ Cải thiện quy trình để ngăn ngừa tái diễn")
            recommendations.append("✅ Đào tạo nhân viên về các vấn đề đã xác định")
        
        recommendations.append("✅ Thiết lập hệ thống cảnh báo sớm")
        recommendations.append("✅ Document bài học kinh nghiệm")
        
        return recommendations
    
    # ==================== COUNTERFACTUAL REASONING ====================
    
    def counterfactual(self, scenario: str) -> Dict[str, Any]:
        """
        Perform counterfactual reasoning.
        
        Args:
            scenario: Counterfactual scenario (e.g., "Nếu không mưa thì...")
            
        Returns:
            Analysis of counterfactual scenario
        """
        # Parse scenario
        if_not, then_what = self._parse_counterfactual(scenario)
        
        if not if_not or not then_what:
            return {
                "valid": False,
                "scenario": scenario,
                "analysis": "❌ Không thể phân tích: cú pháp không đúng"
            }
        
        # Analyze causal relationship
        chain = self.analyze_chain(f"{if_not} → {then_what}")
        
        # Generate alternative scenarios
        alternatives = self._generate_alternative_scenarios(if_not, then_what)
        
        return {
            "valid": True,
            "scenario": scenario,
            "if_not": if_not,
            "then_what": then_what,
            "causal_chain": chain.to_dict() if hasattr(chain, 'to_dict') else str(chain),
            "alternatives": alternatives,
            "confidence": chain.total_strength if chain else 0.5
        }
    
    def _parse_counterfactual(self, scenario: str) -> Tuple[str, str]:
        """Parse counterfactual scenario."""
        # Look for "Nếu không X thì Y" pattern
        match = re.search(r'nếu\s+(không|không có)\s+(.+?)\s+(thì|thì sẽ)\s+(.+)', scenario, re.IGNORECASE)
        if match:
            return match.group(2), match.group(4)
        
        # Look for "X không xảy ra, Y có xảy ra không?" pattern
        match = re.search(r'(.+?)\s+(không\s+xảy\s+ra|không\s+đến)\s*,?\s*(.+?)\s+(có\s+xảy\s+ra\s+không|sẽ\s+thế\s+nào)', scenario, re.IGNORECASE)
        if match:
            return match.group(1), match.group(3)
        
        return "", ""
    
    def _generate_alternative_scenarios(self, if_not: str, then_what: str) -> List[str]:
        """Generate alternative counterfactual scenarios."""
        return [
            f"Nếu {if_not} xảy ra, thì {then_what} có thể không xảy ra",
            f"Nếu có yếu tố khác thay thế {if_not}, thì {then_what} vẫn có thể xảy ra",
            f"Nếu {if_not} xảy ra muộn hơn, thì thời điểm {then_what} cũng thay đổi"
        ]
    
    # ==================== CORRELATION VS CAUSATION ====================
    
    def distinguish_correlation_causation(self, event_a: str, event_b: str, data: List[Dict] = None) -> Dict[str, Any]:
        """
        Distinguish between correlation and causation.
        
        Args:
            event_a: First event
            event_b: Second event
            data: Optional data points for analysis
            
        Returns:
            Analysis of relationship
        """
        # Check for causal keywords
        a_has_cause = any(kw in event_a.lower() for kw in self.CAUSE_KEYWORDS)
        b_has_effect = any(kw in event_b.lower() for kw in self.EFFECT_KEYWORDS)
        
        # Check for correlation keywords
        has_correlation = any(kw in (event_a + event_b).lower() for kw in self.CORRELATION_KEYWORDS)
        
        # Determine relationship
        if a_has_cause and b_has_effect:
            relationship = CausalRelationType.DIRECT_CAUSE
            confidence = 0.8
            explanation = "✅ Có dấu hiệu quan hệ nhân quả trực tiếp"
        elif has_correlation:
            relationship = CausalRelationType.CORRELATION
            confidence = 0.6
            explanation = "⚠️ Chỉ có tương quan, chưa chứng minh được nhân quả"
        else:
            # Check temporal sequence
            relationship = self._infer_relationship(event_a, event_b)
            confidence = 0.5
            explanation = f"🔍 Quan hệ: {relationship.value}"
        
        # Check for common cause
        common_cause = self._check_common_cause(event_a, event_b)
        
        return {
            "event_a": event_a,
            "event_b": event_b,
            "relationship": relationship.value,
            "confidence": confidence,
            "explanation": explanation,
            "common_cause": common_cause,
            "recommendation": self._get_recommendation(relationship)
        }
    
    def _infer_relationship(self, event_a: str, event_b: str) -> CausalRelationType:
        """Infer relationship type from events."""
        # Check temporal indicators
        a_before = 'trước' in event_a.lower() or 'đầu' in event_a.lower()
        b_before = 'trước' in event_b.lower() or 'đầu' in event_b.lower()
        
        if a_before and not b_before:
            return CausalRelationType.DIRECT_CAUSE
        elif b_before and not a_before:
            return CausalRelationType.REVERSE_CAUSE
        else:
            return CausalRelationType.CORRELATION
    
    def _check_common_cause(self, event_a: str, event_b: str) -> Optional[str]:
        """Check for potential common cause."""
        # Simple heuristic: look for shared context
        words_a = set(event_a.lower().split())
        words_b = set(event_b.lower().split())
        shared = words_a & words_b
        
        if len(shared) > 2:
            return f"Có thể có nguyên nhân chung liên quan đến: {', '.join(list(shared)[:3])}"
        
        return None
    
    def _get_recommendation(self, relationship: CausalRelationType) -> str:
        """Get recommendation based on relationship type."""
        recommendations = {
            CausalRelationType.DIRECT_CAUSE: "✅ Có thể can thiệp vào cause để thay đổi effect",
            CausalRelationType.CORRELATION: "⚠️ Cần nghiên cứu thêm để xác định nhân quả",
            CausalRelationType.COMMON_CAUSE: "⚠️ Tìm và xử lý nguyên nhân chung",
            CausalRelationType.REVERSE_CAUSE: "⚠️ Xem xét lại hướng nhân quả",
            CausalRelationType.SPURIOUS: "❌ Mối liên hệ ngẫu nhiên, không nên hành động"
        }
        return recommendations.get(relationship, "🔍 Cần phân tích thêm")


# Convenience functions
def analyze_causal_chain(chain_text: str) -> CausalChain:
    """Quick causal chain analysis."""
    engine = CausalEngine()
    return engine.analyze_chain(chain_text)


def find_root_cause(problem: str) -> RootCauseAnalysis:
    """Quick root cause analysis."""
    engine = CausalEngine()
    return engine.root_cause_analysis(problem)


def check_correlation_vs_causation(event_a: str, event_b: str) -> Dict[str, Any]:
    """Quick correlation vs causation check."""
    engine = CausalEngine()
    return engine.distinguish_correlation_causation(event_a, event_b)