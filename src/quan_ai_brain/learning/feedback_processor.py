"""V39.5 Feedback Processing Engine.

Implements feedback processing capabilities:
- User feedback collection (ratings, comments, corrections)
- Performance metrics tracking (accuracy, latency, satisfaction)
- Error analysis (categorization, root cause, patterns)
- Improvement suggestions (prioritization, impact assessment)
- Feedback loop closure (action tracking, outcome measurement)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
from collections import defaultdict
import statistics


class FeedbackType(Enum):
    """Feedback types."""
    RATING = "rating"
    COMMENT = "comment"
    CORRECTION = "correction"
    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"
    PRAISE = "praise"


class Sentiment(Enum):
    """Sentiment analysis results."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Priority(Enum):
    """Improvement priority."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Feedback:
    """User feedback record."""
    feedback_id: str
    type: FeedbackType
    sentiment: Sentiment
    rating: Optional[float]  # 1-5 scale
    text: str
    category: str
    timestamp: datetime
    user_id: Optional[str]
    context: Dict[str, Any]
    resolved: bool = False
    resolution_action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "type": self.type.value,
            "sentiment": self.sentiment.value,
            "rating": self.rating,
            "category": self.category,
            "resolved": self.resolved,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PerformanceMetric:
    """Performance metric tracking."""
    metric_id: str
    name: str
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any]
    baseline: Optional[float] = None
    target: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": round(self.value, 4),
            "unit": self.unit,
            "baseline": self.baseline,
            "target": self.target,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ErrorAnalysis:
    """Error analysis result."""
    error_id: str
    error_type: str
    description: str
    frequency: int
    severity: float  # 1-10
    root_cause: str
    affected_components: List[str]
    pattern: str
    first_occurrence: datetime
    last_occurrence: datetime
    suggested_fix: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "frequency": self.frequency,
            "severity": round(self.severity, 2),
            "root_cause": self.root_cause,
            "pattern": self.pattern,
            "suggested_fix": self.suggested_fix
        }


@dataclass
class ImprovementSuggestion:
    """Improvement suggestion."""
    suggestion_id: str
    title: str
    description: str
    category: str
    priority: Priority
    impact_score: float  # 0-10
    effort_score: float  # 0-10
    roi_score: float  # impact/effort
    source_feedback_ids: List[str]
    status: str  # proposed, approved, in_progress, completed
    implementation_notes: str
    outcome_measured: bool = False
    outcome_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suggestion_id": self.suggestion_id,
            "title": self.title,
            "category": self.category,
            "priority": self.priority.value,
            "impact_score": round(self.impact_score, 2),
            "effort_score": round(self.effort_score, 2),
            "roi_score": round(self.roi_score, 2),
            "status": self.status,
            "outcome_measured": self.outcome_measured
        }


class FeedbackProcessor:
    """Feedback processing engine."""
    
    def __init__(self):
        """Initialize feedback processor."""
        self.feedback_counter = 0
        self.metric_counter = 0
        self.error_counter = 0
        self.suggestion_counter = 0
        
        self.feedbacks: List[Feedback] = []
        self.metrics: List[PerformanceMetric] = []
        self.errors: List[ErrorAnalysis] = []
        self.suggestions: List[ImprovementSuggestion] = []
        
        self._initialized = True
        
        print("✅ Feedback Processing Engine initialized")
        print(f"   - Feedback collection: Ready")
        print(f"   - Performance tracking: Ready")
        print(f"   - Error analysis: Ready")
        print(f"   - Improvement suggestions: Ready")
    
    def collect_feedback(self, feedback_type: FeedbackType,
                        text: str,
                        rating: Optional[float] = None,
                        category: str = "general",
                        user_id: Optional[str] = None,
                        context: Dict[str, Any] = None) -> Feedback:
        """Collect user feedback.
        
        Args:
            feedback_type: Type of feedback
            text: Feedback text
            rating: Optional rating (1-5)
            category: Feedback category
            user_id: User identifier
            context: Additional context
            
        Returns:
            Feedback object
        """
        self.feedback_counter += 1
        
        # Analyze sentiment (simplified)
        sentiment = self._analyze_sentiment(text)
        
        feedback = Feedback(
            feedback_id=f"FB_{self.feedback_counter:04d}",
            type=feedback_type,
            sentiment=sentiment,
            rating=rating,
            text=text,
            category=category,
            timestamp=datetime.now(),
            user_id=user_id,
            context=context or {}
        )
        
        self.feedbacks.append(feedback)
        
        return feedback
    
    def track_metric(self, metric_name: str,
                    value: float,
                    unit: str = "",
                    baseline: Optional[float] = None,
                    target: Optional[float] = None,
                    context: Dict[str, Any] = None) -> PerformanceMetric:
        """Track performance metric.
        
        Args:
            metric_name: Name of metric
            value: Measured value
            unit: Unit of measurement
            baseline: Baseline value for comparison
            target: Target value
            context: Additional context
            
        Returns:
            PerformanceMetric object
        """
        self.metric_counter += 1
        
        metric = PerformanceMetric(
            metric_id=f"METRIC_{self.metric_counter:04d}",
            name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            context=context or {},
            baseline=baseline,
            target=target
        )
        
        self.metrics.append(metric)
        
        return metric
    
    def analyze_errors(self, error_logs: List[Dict[str, Any]]) -> List[ErrorAnalysis]:
        """Analyze error logs to identify patterns.
        
        Args:
            error_logs: List of error log entries
            
        Returns:
            List of ErrorAnalysis objects
        """
        if not error_logs:
            return []
        
        # Group errors by type
        error_groups = defaultdict(list)
        for log in error_logs:
            error_type = log.get("type", "unknown")
            error_groups[error_type].append(log)
        
        analyses = []
        
        for error_type, logs in error_groups.items():
            self.error_counter += 1
            
            # Calculate frequency
            frequency = len(logs)
            
            # Estimate severity (simplified)
            severity = min(10, frequency * 0.5 + 3)
            
            # Identify pattern
            pattern = self._identify_error_pattern(logs)
            
            # Determine root cause
            root_cause = self._determine_root_cause(error_type, logs)
            
            # Generate suggested fix
            suggested_fix = self._generate_fix_suggestion(error_type, root_cause)
            
            analysis = ErrorAnalysis(
                error_id=f"ERR_{self.error_counter:04d}",
                error_type=error_type,
                description=f"{frequency} occurrences of {error_type}",
                frequency=frequency,
                severity=severity,
                root_cause=root_cause,
                affected_components=list(set(log.get("component", "unknown") for log in logs)),
                pattern=pattern,
                first_occurrence=min(log.get("timestamp", datetime.now()) for log in logs),
                last_occurrence=max(log.get("timestamp", datetime.now()) for log in logs),
                suggested_fix=suggested_fix
            )
            
            analyses.append(analysis)
        
        # Sort by severity
        analyses.sort(key=lambda x: x.severity, reverse=True)
        
        return analyses
    
    def generate_improvements(self,
                             feedbacks: List[Feedback] = None,
                             errors: List[ErrorAnalysis] = None,
                             metrics: List[PerformanceMetric] = None) -> List[ImprovementSuggestion]:
        """Generate improvement suggestions based on feedback, errors, and metrics.
        
        Args:
            feedbacks: List of feedback to analyze
            errors: List of error analyses
            metrics: List of performance metrics
            
        Returns:
            List of ImprovementSuggestion objects
        """
        suggestions = []
        
        # Generate from feedback
        if feedbacks:
            feedback_suggestions = self._generate_from_feedback(feedbacks)
            suggestions.extend(feedback_suggestions)
        
        # Generate from errors
        if errors:
            error_suggestions = self._generate_from_errors(errors)
            suggestions.extend(error_suggestions)
        
        # Generate from metrics
        if metrics:
            metric_suggestions = self._generate_from_metrics(metrics)
            suggestions.extend(metric_suggestions)
        
        # Calculate ROI scores
        for suggestion in suggestions:
            suggestion.roi_score = suggestion.impact_score / max(suggestion.effort_score, 1)
        
        # Sort by ROI
        suggestions.sort(key=lambda x: x.roi_score, reverse=True)
        
        return suggestions
    
    def get_performance_summary(self,
                               metric_names: List[str] = None,
                               time_range: Tuple[datetime, datetime] = None) -> Dict[str, Any]:
        """Get performance summary.
        
        Args:
            metric_names: Specific metrics to include
            time_range: Time range for analysis
            
        Returns:
            Performance summary dictionary
        """
        # Filter metrics
        metrics = self.metrics
        if metric_names:
            metrics = [m for m in metrics if m.name in metric_names]
        
        if time_range:
            start, end = time_range
            metrics = [m for m in metrics if start <= m.timestamp <= end]
        
        if not metrics:
            return {"message": "No metrics found"}
        
        # Calculate statistics
        summary = {}
        metrics_by_name = defaultdict(list)
        
        for metric in metrics:
            metrics_by_name[metric.name].append(metric.value)
        
        for name, values in metrics_by_name.items():
            summary[name] = {
                "current": values[-1] if values else 0,
                "average": statistics.mean(values) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "count": len(values)
            }
        
        # Calculate overall trends
        trends = {}
        for name, values in metrics_by_name.items():
            if len(values) >= 2:
                change = values[-1] - values[0]
                change_pct = (change / values[0] * 100) if values[0] != 0 else 0
                trends[name] = {
                    "direction": "up" if change > 0 else "down" if change < 0 else "stable",
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2)
                }
        
        return {
            "metrics": summary,
            "trends": trends,
            "total_data_points": len(metrics),
            "time_range": {
                "start": metrics[0].timestamp.isoformat() if metrics else None,
                "end": metrics[-1].timestamp.isoformat() if metrics else None
            }
        }
    
    def get_feedback_statistics(self) -> Dict[str, Any]:
        """Get feedback statistics.
        
        Returns:
            Feedback statistics dictionary
        """
        if not self.feedbacks:
            return {"message": "No feedback collected"}
        
        # Count by type
        type_counts = defaultdict(int)
        for fb in self.feedbacks:
            type_counts[fb.type.value] += 1
        
        # Count by sentiment
        sentiment_counts = defaultdict(int)
        for fb in self.feedbacks:
            sentiment_counts[fb.sentiment.value] += 1
        
        # Average rating
        ratings = [fb.rating for fb in self.feedbacks if fb.rating is not None]
        avg_rating = statistics.mean(ratings) if ratings else None
        
        # Resolution rate
        resolved = sum(1 for fb in self.feedbacks if fb.resolved)
        resolution_rate = (resolved / len(self.feedbacks) * 100) if self.feedbacks else 0
        
        return {
            "total_feedback": len(self.feedbacks),
            "by_type": dict(type_counts),
            "by_sentiment": dict(sentiment_counts),
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "resolution_rate": round(resolution_rate, 2),
            "unresolved_count": len(self.feedbacks) - resolved
        }
    
    def _analyze_sentiment(self, text: str) -> Sentiment:
        """Analyze sentiment of text (simplified)."""
        text_lower = text.lower()
        
        positive_words = ["good", "great", "excellent", "amazing", "perfect", "love", "happy"]
        negative_words = ["bad", "terrible", "awful", "horrible", "worst", "hate", "angry"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return Sentiment.POSITIVE
        elif negative_count > positive_count:
            return Sentiment.NEGATIVE
        else:
            return Sentiment.NEUTRAL
    
    def _identify_error_pattern(self, logs: List[Dict[str, Any]]) -> str:
        """Identify error pattern from logs."""
        # Simple pattern detection
        if len(logs) > 10:
            return "Frequent recurring error"
        elif len(logs) > 5:
            return "Moderate frequency error"
        else:
            return "Occasional error"
    
    def _determine_root_cause(self, error_type: str, logs: List[Dict[str, Any]]) -> str:
        """Determine root cause of error."""
        # Simplified root cause analysis
        causes = {
            "timeout": "Network latency or resource contention",
            "null_pointer": "Missing null checks in code",
            "validation": "Input validation logic incomplete",
            "authentication": "Token expiration or invalid credentials",
            "database": "Connection pool exhaustion or query optimization needed"
        }
        
        return causes.get(error_type.lower(), "Unknown root cause - requires investigation")
    
    def _generate_fix_suggestion(self, error_type: str, root_cause: str) -> str:
        """Generate fix suggestion for error."""
        fixes = {
            "timeout": "Implement retry logic with exponential backoff",
            "null_pointer": "Add comprehensive null checks and optional chaining",
            "validation": "Enhance input validation with schema validation",
            "authentication": "Implement token refresh mechanism",
            "database": "Optimize queries and increase connection pool size"
        }
        
        return fixes.get(error_type.lower(), f"Address: {root_cause}")
    
    def _generate_from_feedback(self, feedbacks: List[Feedback]) -> List[ImprovementSuggestion]:
        """Generate suggestions from feedback."""
        suggestions = []
        
        # Group by category
        by_category = defaultdict(list)
        for fb in feedbacks:
            by_category[fb.category].append(fb)
        
        for category, category_feedbacks in by_category.items():
            self.suggestion_counter += 1
            
            # Calculate average rating
            ratings = [fb.rating for fb in category_feedbacks if fb.rating]
            avg_rating = statistics.mean(ratings) if ratings else 3.0
            
            # Determine priority and impact
            if avg_rating < 2.5:
                priority = Priority.HIGH
                impact = 8.0
            elif avg_rating < 3.5:
                priority = Priority.MEDIUM
                impact = 6.0
            else:
                priority = Priority.LOW
                impact = 4.0
            
            suggestion = ImprovementSuggestion(
                suggestion_id=f"SUGGEST_{self.suggestion_counter:04d}",
                title=f"Improve {category.title()}",
                description=f"Based on {len(category_feedbacks)} feedback items",
                category=category,
                priority=priority,
                impact_score=impact,
                effort_score=5.0,
                roi_score=impact / 5.0,
                source_feedback_ids=[fb.feedback_id for fb in category_feedbacks],
                status="proposed"
            )
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_from_errors(self, errors: List[ErrorAnalysis]) -> List[ImprovementSuggestion]:
        """Generate suggestions from error analyses."""
        suggestions = []
        
        for error in errors:
            self.suggestion_counter += 1
            
            priority = Priority.CRITICAL if error.severity > 7 else Priority.HIGH if error.severity > 5 else Priority.MEDIUM
            
            suggestion = ImprovementSuggestion(
                suggestion_id=f"SUGGEST_{self.suggestion_counter:04d}",
                title=f"Fix {error.error_type} errors",
                description=error.suggested_fix,
                category="reliability",
                priority=priority,
                impact_score=error.severity,
                effort_score=6.0,
                roi_score=error.severity / 6.0,
                source_feedback_ids=[error.error_id],
                status="proposed"
            )
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_from_metrics(self, metrics: List[PerformanceMetric]) -> List[ImprovementSuggestion]:
        """Generate suggestions from performance metrics."""
        suggestions = []
        
        for metric in metrics:
            if metric.target and metric.value < metric.target:
                self.suggestion_counter += 1
                
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"SUGGEST_{self.suggestion_counter:04d}",
                    title=f"Improve {metric.name}",
                    description=f"Current: {metric.value} {metric.unit}, Target: {metric.target} {metric.unit}",
                    category="performance",
                    priority=Priority.MEDIUM,
                    impact_score=7.0,
                    effort_score=5.0,
                    roi_score=1.4,
                    source_feedback_ids=[metric.metric_id],
                    status="proposed"
                )
                
                suggestions.append(suggestion)
        
        return suggestions


# Convenience functions
def collect_user_feedback(text: str, rating: float = None, category: str = "general") -> Feedback:
    """Collect user feedback."""
    processor = FeedbackProcessor()
    return processor.collect_feedback(FeedbackType.COMMENT, text, rating, category)


def track_performance(name: str, value: float, unit: str = "") -> PerformanceMetric:
    """Track performance metric."""
    processor = FeedbackProcessor()
    return processor.track_metric(name, value, unit)


def analyze_system_errors(logs: List[Dict[str, Any]]) -> List[ErrorAnalysis]:
    """Analyze system errors."""
    processor = FeedbackProcessor()
    return processor.analyze_errors(logs)


def suggest_improvements() -> List[ImprovementSuggestion]:
    """Suggest improvements."""
    processor = FeedbackProcessor()
    return processor.generate_improvements(processor.feedbacks, processor.errors, processor.metrics)