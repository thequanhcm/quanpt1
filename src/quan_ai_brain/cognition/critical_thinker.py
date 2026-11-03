"""V39.3 Critical Thinking Engine.

Implements critical thinking capabilities:
- Bias detection (cognitive, confirmation, selection)
- Logical fallacy identification
- Evidence evaluation
- Argument structure analysis
- Source credibility assessment
- Reasoning quality evaluation

Usage:
    from quan_ai_brain.cognition.critical_thinker import CriticalThinker
    
    thinker = CriticalThinker()
    
    # Analyze argument quality
    analysis = thinker.analyze_argument("Statement to analyze")
    
    # Detect biases
    biases = thinker.detect_biases(text)
    
    # Evaluate evidence
    evaluation = thinker.evaluate_evidence(claim, evidence_list)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter


class BiasType(Enum):
    """Types of cognitive biases."""
    CONFIRMATION_BIAS = "confirmation_bias"           # Favoring confirming evidence
    SELECTION_BIAS = "selection_bias"                 # Non-representative sample
    ANCHORING_BIAS = "anchoring_bias"                 # Relying too much on first info
    AVAILABILITY_HEURISTIC = "availability_heuristic" # Overweighting recent/vivid
    AUTHORITY_BIAS = "authority_bias"                 # Deferring to authority
    BANDWAGON_BIAS = "bandwagon_bias"                 # Following the crowd
    HINDSIGHT_BIAS = "hindsight_bias"                 # "I knew it all along"
    SELF_SERVING_BIAS = "self_serving_bias"           # Taking credit for success
    NEGATIVITY_BIAS = "negativity_bias"               # Overweighting negative info
    OPTIMISM_BIAS = "optimism_bias"                   # Overestimating positive outcomes


class EvidenceQuality(Enum):
    """Levels of evidence quality."""
    EXCELLENT = "excellent"      # Multiple independent sources, peer-reviewed
    GOOD = "good"                # Reliable sources, consistent
    FAIR = "fair"                # Some support, but limited
    WEAK = "weak"                # Anecdotal, single source
    VERY_WEAK = "very_weak"      # Unreliable, contradictory
    NO_EVIDENCE = "no_evidence"  # Pure speculation


@dataclass
class ArgumentStructure:
    """Parsed argument structure."""
    claim: str
    premises: List[str]
    assumptions: List[str]
    evidence: List[str]
    counterarguments: List[str]
    conclusion: str


@dataclass
class BiasAnalysis:
    """Result of bias analysis."""
    detected_biases: List[BiasType]
    bias_count: int
    severity: str  # low, medium, high
    examples: List[str]
    recommendations: List[str]


@dataclass
class EvidenceEvaluation:
    """Result of evidence evaluation."""
    claim: str
    quality: EvidenceQuality
    quality_score: float  # 0.0 to 1.0
    supporting_evidence: List[str]
    contradictory_evidence: List[str]
    gaps: List[str]
    confidence: float
    recommendation: str


@dataclass
class ArgumentAnalysis:
    """Comprehensive argument analysis."""
    argument: str
    structure: ArgumentStructure
    validity: bool
    strength: str  # strong, moderate, weak
    fallacies: List[str]
    biases: BiasAnalysis
    evidence_quality: EvidenceEvaluation
    overall_score: float
    recommendations: List[str]


class CriticalThinker:
    """
    Critical thinking engine.
    
    Features:
    - Bias detection
    - Fallacy identification
    - Evidence evaluation
    - Argument analysis
    - Source credibility assessment
    """
    
    # Bias indicators
    CONFIRMATION_PATTERNS = [
        r'\bcũng như\b', r'\bcùng với\b', r'\bcũng\b', r'\bcũng vậy\b',
        r'chỉ có', r'chỉ khi', r'chỉ những'
    ]
    
    AUTHORITY_PATTERNS = [
        r'\bchuyên gia\b', r'\bthầy giáo\b', r'\bGS\b', r'\bTS\b',
        r'chỉ đạo của', r'theo ý kiến của', r'chuyên gia cho rằng'
    ]
    
    BANDWAGON_PATTERNS = [
        r'\bnhiều người\b', r'\bđa số\b', r'\bphổ biến\b', r'\bthông dụng\b',
        r'mọi người đều', r'ai cũng', r'phần lớn'
    ]
    
    ANCHORING_PATTERNS = [
        r'\blần đầu\b', r'\ban đầu\b', r'\bđầu tiên\b', r'\bkhởi đầu\b',
        r'con số này', r'giá này'
    ]
    
    # Fallacy patterns (fixed regex)
    FALLACY_PATTERNS = {
        'ad_hominem': [r'đồ ngốc', r'kẻ ngu', r'anh ta không biết'],
        'straw_man': [r'y bạn là', r'ý bạn nói là', r'theo bạn thì'],
        'false_dilemma': [r'hoặc.*hoặc', r'chỉ có 2 lựa chọn', r'đồng ý hoặc chống'],
        'slippery_slope': [r'nếu.*thì sẽ', r'dẫn đến', r'chuỗi sự kiện'],
        'circular': [r'vì.*vì', r'đó là lý do.*đó là lý do'],
        'appeal_to_emotion': [r'đáng thương', r'thương hại', r'ghê tởm'],
        'hasty_generalization': [r'một vài.*tất cả', r'đôi khi.*luôn luôn']
    }
    
    def __init__(self):
        """Initialize critical thinker."""
        self.knowledge_base: List[Dict[str, Any]] = []
        self.analysis_history: List[ArgumentAnalysis] = []
        
        print("✅ Critical Thinking Engine initialized")
        print("   - Bias detection: Ready")
        print("   - Fallacy identification: Ready")
        print("   - Evidence evaluation: Ready")
        print("   - Argument analysis: Ready")
    
    # ==================== BIAS DETECTION ====================
    
    def detect_biases(self, text: str) -> BiasAnalysis:
        """
        Detect cognitive biases in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            BiasAnalysis with detected biases
        """
        detected_biases = []
        examples = []
        
        text_lower = text.lower()
        
        # Check for confirmation bias
        if any(re.search(pattern, text_lower) for pattern in self.CONFIRMATION_PATTERNS):
            detected_biases.append(BiasType.CONFIRMATION_BIAS)
            examples.append("Có dấu hiệu confirmation bias (chỉ tập trung vào evidence phù hợp)")
        
        # Check for authority bias
        if any(re.search(pattern, text_lower) for pattern in self.AUTHORITY_PATTERNS):
            detected_biases.append(BiasType.AUTHORITY_BIAS)
            examples.append("Có dấu hiệu authority bias (dựa vào ý kiến chuyên gia thay vì evidence)")
        
        # Check for bandwagon bias
        if any(re.search(pattern, text_lower) for pattern in self.BANDWAGON_PATTERNS):
            detected_biases.append(BiasType.BANDWAGON_BIAS)
            examples.append("Có dấu hiệu bandwagon bias (theo đám đông)")
        
        # Check for anchoring bias
        if any(re.search(pattern, text_lower) for pattern in self.ANCHORING_PATTERNS):
            detected_biases.append(BiasType.ANCHORING_BIAS)
            examples.append("Có dấu hiệu anchoring bias (dựa quá nhiều vào thông tin đầu tiên)")
        
        # Check for selection bias
        if 'chỉ' in text_lower and ('một số' in text_lower or 'vài' in text_lower):
            detected_biases.append(BiasType.SELECTION_BIAS)
            examples.append("Có dấu hiệu selection bias (mẫu không đại diện)")
        
        # Check for availability heuristic
        if 'gần đây' in text_lower or 'mới đây' in text_lower:
            detected_biases.append(BiasType.AVAILABILITY_HEURISTIC)
            examples.append("Có dấu hiệu availability heuristic (đánh giá dựa trên thông tin dễ nhớ)")
        
        # Determine severity
        bias_count = len(detected_biases)
        if bias_count == 0:
            severity = "low"
        elif bias_count <= 2:
            severity = "medium"
        else:
            severity = "high"
        
        # Generate recommendations
        recommendations = self._generate_bias_recommendations(detected_biases)
        
        return BiasAnalysis(
            detected_biases=detected_biases,
            bias_count=bias_count,
            severity=severity,
            examples=examples,
            recommendations=recommendations
        )
    
    def _generate_bias_recommendations(self, biases: List[BiasType]) -> List[str]:
        """Generate recommendations to reduce biases."""
        recommendations = []
        
        if BiasType.CONFIRMATION_BIAS in biases:
            recommendations.append("✅ Tìm kiếm evidence trái chiều")
            recommendations.append("✅ Xem xét các quan điểm khác")
        
        if BiasType.AUTHORITY_BIAS in biases:
            recommendations.append("✅ Đánh giá evidence độc lập với nguồn")
            recommendations.append("✅ Kiểm tra source credibility")
        
        if BiasType.BANDWAGON_BIAS in biases:
            recommendations.append("✅ Không dựa vào 'đa số' làm evidence")
            recommendations.append("✅ Tìm evidence khách quan")
        
        if BiasType.SELECTION_BIAS in biases:
            recommendations.append("✅ Sử dụng sample đại diện")
            recommendations.append("✅ Tránh cherry-picking")
        
        if not recommendations:
            recommendations.append("✅ Tiếp tục duy trì tư duy phản biện")
        
        return recommendations
    
    # ==================== FALLACY IDENTIFICATION ====================
    
    def identify_fallacies(self, text: str) -> List[str]:
        """
        Identify logical fallacies in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected fallacy names
        """
        fallacies = []
        text_lower = text.lower()
        
        for fallacy_name, patterns in self.FALLACY_PATTERNS.items():
            if any(re.search(pattern, text_lower) for pattern in patterns):
                fallacies.append(fallacy_name)
        
        return fallacies
    
    # ==================== EVIDENCE EVALUATION ====================
    
    def evaluate_evidence(self, claim: str, evidence_list: List[str]) -> EvidenceEvaluation:
        """
        Evaluate quality of evidence supporting a claim.
        
        Args:
            claim: The claim being made
            evidence_list: List of evidence items
            
        Returns:
            EvidenceEvaluation with quality assessment
        """
        if not evidence_list:
            return EvidenceEvaluation(
                claim=claim,
                quality=EvidenceQuality.NO_EVIDENCE,
                quality_score=0.0,
                supporting_evidence=[],
                contradictory_evidence=[],
                gaps=["Không có evidence nào được cung cấp"],
                confidence=0.0,
                recommendation="❌ Cần thu thập evidence trước khi kết luận"
            )
        
        # Score each evidence item
        scores = []
        supporting = []
        contradictory = []
        
        for evidence in evidence_list:
            score = self._score_evidence_item(evidence, claim)
            scores.append(score)
            
            if score >= 0.7:
                supporting.append(evidence)
            elif score <= 0.3:
                contradictory.append(evidence)
        
        # Calculate overall quality
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Determine quality level
        if avg_score >= 0.8:
            quality = EvidenceQuality.EXCELLENT
        elif avg_score >= 0.6:
            quality = EvidenceQuality.GOOD
        elif avg_score >= 0.4:
            quality = EvidenceQuality.FAIR
        elif avg_score >= 0.2:
            quality = EvidenceQuality.WEAK
        else:
            quality = EvidenceQuality.VERY_WEAK
        
        # Identify gaps
        gaps = self._identify_evidence_gaps(claim, evidence_list)
        
        # Generate recommendation
        recommendation = self._generate_evidence_recommendation(quality, gaps)
        
        return EvidenceEvaluation(
            claim=claim,
            quality=quality,
            quality_score=avg_score,
            supporting_evidence=supporting,
            contradictory_evidence=contradictory,
            gaps=gaps,
            confidence=avg_score,
            recommendation=recommendation
        )
    
    def _score_evidence_item(self, evidence: str, claim: str) -> float:
        """Score individual evidence item."""
        score = 0.5  # Base score
        
        # Check for strong indicators
        strong_indicators = [
            'nghiên cứu', 'peer-reviewed', 'experiment', 'data',
            'thống kê', 'số liệu', 'bằng chứng', 'evidence'
        ]
        if any(ind in evidence.lower() for ind in strong_indicators):
            score += 0.2
        
        # Check for weak indicators
        weak_indicators = [
            'tôi nghĩ', 'có vẻ như', 'có lẽ', 'có thể',
            'theo tôi', 'cảm thấy', 'tin rằng'
        ]
        if any(ind in evidence.lower() for ind in weak_indicators):
            score -= 0.2
        
        # Check relevance to claim
        claim_words = set(claim.lower().split())
        evidence_words = set(evidence.lower().split())
        overlap = len(claim_words & evidence_words)
        if overlap > 3:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _identify_evidence_gaps(self, claim: str, evidence_list: List[str]) -> List[str]:
        """Identify gaps in evidence."""
        gaps = []
        
        # Check for missing quantitative evidence
        if any(word in claim.lower() for word in ['bao nhiêu', 'mức độ', 'tỷ lệ']):
            has_numbers = any(re.search(r'\d+', e) for e in evidence_list)
            if not has_numbers:
                gaps.append("Thiếu số liệu định lượng")
        
        # Check for missing source citations
        has_sources = any('nguồn' in e.lower() or 'theo' in e.lower() for e in evidence_list)
        if not has_sources and len(evidence_list) > 0:
            gaps.append("Thiếu nguồn trích dẫn")
        
        # Check for contradictory evidence
        if len(evidence_list) > 1:
            # Simple check: if evidence items are very different
            unique_content = len(set(e.lower() for e in evidence_list))
            if unique_content > len(evidence_list) * 0.8:
                gaps.append("Evidence có thể không nhất quán")
        
        if not gaps:
            gaps.append("Không có gap lớn nào")
        
        return gaps
    
    def _generate_evidence_recommendation(self, quality: EvidenceQuality, gaps: List[str]) -> str:
        """Generate recommendation based on evidence quality."""
        if quality == EvidenceQuality.EXCELLENT:
            return "✅ Evidence mạnh, có thể đưa ra kết luận"
        elif quality == EvidenceQuality.GOOD:
            return "✅ Evidence tốt, kết luận có căn cứ"
        elif quality == EvidenceQuality.FAIR:
            return "⚠️ Evidence trung bình, cần thêm evidence"
        elif quality == EvidenceQuality.WEAK:
            return "⚠️ Evidence yếu, không nên kết luận vội"
        else:
            return "❌ Evidence rất yếu hoặc không có, cần thu thập thêm"
    
    # ==================== ARGUMENT ANALYSIS ====================
    
    def analyze_argument(self, argument: str) -> ArgumentAnalysis:
        """
        Comprehensive argument analysis.
        
        Args:
            argument: Full argument to analyze
            
        Returns:
            ArgumentAnalysis with complete evaluation
        """
        # Parse argument structure
        structure = self._parse_argument_structure(argument)
        
        # Detect biases
        biases = self.detect_biases(argument)
        
        # Identify fallacies
        fallacies = self.identify_fallacies(argument)
        
        # Evaluate evidence
        evidence_eval = self.evaluate_evidence(
            structure.claim,
            structure.evidence + structure.premises
        )
        
        # Determine validity and strength
        validity = len(fallacies) == 0 and biases.bias_count <= 1
        strength = self._determine_strength(evidence_eval.quality, fallacies, biases)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(evidence_eval, fallacies, biases)
        
        # Generate recommendations
        recommendations = self._generate_argument_recommendations(
            structure, fallacies, biases, evidence_eval
        )
        
        analysis = ArgumentAnalysis(
            argument=argument,
            structure=structure,
            validity=validity,
            strength=strength,
            fallacies=fallacies,
            biases=biases,
            evidence_quality=evidence_eval,
            overall_score=overall_score,
            recommendations=recommendations
        )
        
        self.analysis_history.append(analysis)
        return analysis
    
    def _parse_argument_structure(self, argument: str) -> ArgumentStructure:
        """Parse argument into structure."""
        # Simple parsing - extract claim, premises, evidence
        sentences = re.split(r'[.!?]+', argument)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        claim = sentences[0] if sentences else ""
        premises = sentences[1:3] if len(sentences) > 1 else []
        evidence = sentences[3:6] if len(sentences) > 3 else []
        
        assumptions = []
        counterarguments = []
        conclusion = claim
        
        return ArgumentStructure(
            claim=claim,
            premises=premises,
            assumptions=assumptions,
            evidence=evidence,
            counterarguments=counterarguments,
            conclusion=conclusion
        )
    
    def _determine_strength(self, quality: EvidenceQuality, fallacies: List[str], biases: BiasAnalysis) -> str:
        """Determine argument strength."""
        score = 0
        
        # Evidence quality
        quality_scores = {
            EvidenceQuality.EXCELLENT: 3,
            EvidenceQuality.GOOD: 2,
            EvidenceQuality.FAIR: 1,
            EvidenceQuality.WEAK: 0,
            EvidenceQuality.VERY_WEAK: -1,
            EvidenceQuality.NO_EVIDENCE: -2
        }
        score += quality_scores.get(quality, 0)
        
        # Fallacies penalty
        score -= len(fallacies)
        
        # Biases penalty
        if biases.severity == "high":
            score -= 2
        elif biases.severity == "medium":
            score -= 1
        
        if score >= 3:
            return "strong"
        elif score >= 1:
            return "moderate"
        else:
            return "weak"
    
    def _calculate_overall_score(self, evidence: EvidenceEvaluation, fallacies: List[str], biases: BiasAnalysis) -> float:
        """Calculate overall argument score (0.0 to 1.0)."""
        base_score = evidence.quality_score
        
        # Fallacies penalty
        fallacy_penalty = len(fallacies) * 0.1
        
        # Biases penalty
        bias_penalty = biases.bias_count * 0.05
        
        final_score = max(0.0, min(1.0, base_score - fallacy_penalty - bias_penalty))
        
        return final_score
    
    def _generate_argument_recommendations(self, structure: ArgumentStructure, fallacies: List[str], biases: BiasAnalysis, evidence: EvidenceEvaluation) -> List[str]:
        """Generate recommendations to improve argument."""
        recommendations = []
        
        if fallacies:
            recommendations.append(f"✅ Loại bỏ {len(fallacies)} logical fallacy")
        
        if biases.bias_count > 0:
            recommendations.append(f"✅ Giảm thiểu {biases.bias_count} bias đã phát hiện")
        
        if evidence.quality in [EvidenceQuality.WEAK, EvidenceQuality.VERY_WEAK, EvidenceQuality.NO_EVIDENCE]:
            recommendations.append("✅ Thu thập evidence mạnh hơn")
        
        if not structure.premises:
            recommendations.append("✅ Thêm premises để hỗ trợ claim")
        
        if not recommendations:
            recommendations.append("✅ Argument đã tốt, tiếp tục duy trì")
        
        return recommendations


# Convenience functions
def detect_biases(text: str) -> BiasAnalysis:
    """Quick bias detection."""
    thinker = CriticalThinker()
    return thinker.detect_biases(text)


def evaluate_claim(claim: str, evidence: List[str]) -> EvidenceEvaluation:
    """Quick evidence evaluation."""
    thinker = CriticalThinker()
    return thinker.evaluate_evidence(claim, evidence)


def analyze_argument(argument: str) -> ArgumentAnalysis:
    """Quick argument analysis."""
    thinker = CriticalThinker()
    return thinker.analyze_argument(argument)