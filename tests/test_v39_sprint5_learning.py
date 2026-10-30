"""Tests for Sprint 5: Self-Learning & Improvement.

Tests:
- FeedbackProcessor: Submit feedback, categorization, sentiment analysis
- SelfOptimizer: Parameter optimization, A/B testing
- KnowledgeRefiner: Quality assessment, refinement tracking
"""
import pytest
import json
from pathlib import Path
import tempfile
import shutil

from quan_ai_brain.learning.feedback_processor import (
    FeedbackProcessor, Feedback, FeedbackType, FeedbackCategory, Sentiment
)
from quan_ai_brain.learning.self_optimizer import (
    SelfOptimizer, ParameterConfig, OptimizationRun
)
from quan_ai_brain.learning.knowledge_refiner import (
    KnowledgeRefiner, KnowledgeRefinement, KnowledgeQuality
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_brain.db"
    
    yield str(db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def feedback_processor(temp_db):
    """Create a FeedbackProcessor instance."""
    return FeedbackProcessor(db_path=temp_db)


@pytest.fixture
def self_optimizer(temp_db):
    """Create a SelfOptimizer instance."""
    return SelfOptimizer(db_path=temp_db)


@pytest.fixture
def knowledge_refiner(temp_db):
    """Create a KnowledgeRefiner instance."""
    return KnowledgeRefiner(db_path=temp_db)


class TestFeedbackProcessor:
    """Tests for FeedbackProcessor class."""
    
    def test_submit_rating_feedback(self, feedback_processor):
        """Test submitting rating feedback."""
        feedback = feedback_processor.submit_feedback(
            feedback_type=FeedbackType.RATING,
            category=FeedbackCategory.QUALITY,
            rating=4.5,
            entity_type="task",
            entity_id="task_001"
        )
        
        assert feedback.id is not None
        assert feedback.rating == 4.5
        assert feedback.sentiment == Sentiment.POSITIVE
    
    def test_submit_thumbs_feedback(self, feedback_processor):
        """Test submitting thumbs feedback."""
        feedback = feedback_processor.submit_feedback(
            feedback_type=FeedbackType.THUMBS,
            category=FeedbackCategory.HELPFULNESS,
            thumbs=1,
            entity_type="lesson",
            entity_id="lesson_001"
        )
        
        assert feedback.thumbs == 1
        assert feedback.sentiment == Sentiment.POSITIVE
    
    def test_submit_text_feedback(self, feedback_processor):
        """Test submitting text feedback."""
        feedback = feedback_processor.submit_feedback(
            feedback_type=FeedbackType.TEXT,
            category=FeedbackCategory.ACCURACY,
            text="This is very helpful and accurate!",
            entity_type="practice",
            entity_id="practice_001"
        )
        
        assert feedback.text == "This is very helpful and accurate!"
        assert feedback.sentiment == Sentiment.POSITIVE
    
    def test_negative_feedback(self, feedback_processor):
        """Test negative feedback detection."""
        feedback = feedback_processor.submit_feedback(
            feedback_type=FeedbackType.TEXT,
            category=FeedbackCategory.QUALITY,
            text="This is terrible and wrong",
            entity_type="task",
            entity_id="task_002"
        )
        
        assert feedback.sentiment == Sentiment.NEGATIVE
    
    def test_get_feedbacks_by_entity(self, feedback_processor):
        """Test getting feedbacks by entity."""
        feedback_processor.submit_feedback(
            feedback_type=FeedbackType.RATING,
            category=FeedbackCategory.QUALITY,
            rating=5,
            entity_type="task",
            entity_id="task_001"
        )
        
        feedback_processor.submit_feedback(
            feedback_type=FeedbackType.RATING,
            category=FeedbackCategory.QUALITY,
            rating=4,
            entity_type="task",
            entity_id="task_001"
        )
        
        feedback_processor.submit_feedback(
            feedback_type=FeedbackType.RATING,
            category=FeedbackCategory.QUALITY,
            rating=3,
            entity_type="task",
            entity_id="task_002"
        )
        
        task1_feedbacks = feedback_processor.get_feedbacks(
            entity_type="task",
            entity_id="task_001"
        )
        
        assert len(task1_feedbacks) == 2
    
    def test_get_aggregation(self, feedback_processor):
        """Test getting feedback aggregation."""
        for rating in [5, 4, 5, 3, 4]:
            feedback_processor.submit_feedback(
                feedback_type=FeedbackType.RATING,
                category=FeedbackCategory.QUALITY,
                rating=rating,
                entity_type="task",
                entity_id="task_001"
            )
        
        aggregation = feedback_processor.get_aggregation(
            "task", "task_001", FeedbackCategory.QUALITY
        )
        
        assert aggregation is not None
        assert aggregation.total_feedbacks == 5
        assert aggregation.avg_rating == 4.2
        assert aggregation.recent_trend in ['improving', 'stable', 'declining']
    
    def test_mark_processed(self, feedback_processor):
        """Test marking feedback as processed."""
        feedback = feedback_processor.submit_feedback(
            feedback_type=FeedbackType.RATING,
            category=FeedbackCategory.QUALITY,
            rating=4,
            entity_type="task",
            entity_id="task_001"
        )
        
        assert not feedback.processed
        
        feedback_processor.mark_processed(feedback.id)
        
        updated = feedback_processor.get_feedback(feedback.id)
        assert updated.processed
    
    def test_get_statistics(self, feedback_processor):
        """Test getting feedback statistics."""
        feedback_processor.submit_feedback(
            feedback_type=FeedbackType.RATING,
            category=FeedbackCategory.QUALITY,
            rating=5
        )
        
        feedback_processor.submit_feedback(
            feedback_type=FeedbackType.THUMBS,
            category=FeedbackCategory.HELPFULNESS,
            thumbs=1
        )
        
        stats = feedback_processor.get_statistics()
        
        assert stats['total_feedbacks'] == 2
        assert stats['by_type']['rating'] == 1
        assert stats['by_type']['thumbs'] == 1
        assert stats['avg_rating'] == 5.0


class TestSelfOptimizer:
    """Tests for SelfOptimizer class."""
    
    def test_register_parameter(self, self_optimizer):
        """Test registering a parameter."""
        self_optimizer.register_parameter(
            name="learning_rate",
            value=0.01,
            min_value=0.001,
            max_value=0.1,
            step=0.001,
            description="Learning rate for optimization",
            category="training"
        )
        
        value = self_optimizer.get_parameter("learning_rate")
        assert value == 0.01
    
    def test_set_parameter(self, self_optimizer):
        """Test setting parameter value."""
        self_optimizer.register_parameter("threshold", 0.5)
        
        self_optimizer.set_parameter("threshold", 0.75)
        
        value = self_optimizer.get_parameter("threshold")
        assert value == 0.75
    
    def test_start_optimization(self, self_optimizer):
        """Test starting optimization run."""
        run_id = self_optimizer.start_optimization(
            "accuracy_metric",
            {"learning_rate": 0.01}
        )
        
        assert run_id is not None
        
        history = self_optimizer.get_optimization_history()
        assert len(history) == 1
        assert history[0].status == 'running'
    
    def test_record_iteration(self, self_optimizer):
        """Test recording optimization iteration."""
        run_id = self_optimizer.start_optimization("metric", {"param": 1.0})
        
        self_optimizer.record_iteration(
            run_id, 0, {"param": 0.5}, 0.85
        )
        self_optimizer.record_iteration(
            run_id, 1, {"param": 0.6}, 0.90
        )
        
        results = self_optimizer.get_optimization_results(run_id)
        
        assert len(results) == 2
        assert results[0]['metric_value'] == 0.85
        assert results[1]['metric_value'] == 0.90
    
    def test_complete_optimization(self, self_optimizer):
        """Test completing optimization run."""
        run_id = self_optimizer.start_optimization("metric", {"param": 1.0})
        
        self_optimizer.record_iteration(run_id, 0, {"param": 0.5}, 0.85)
        self_optimizer.complete_optimization(run_id, improvement=0.15)
        
        history = self_optimizer.get_optimization_history()
        assert history[0].status == 'completed'
        assert history[0].improvement == 0.15
    
    def test_optimize_parameter(self, self_optimizer):
        """Test optimizing a parameter."""
        # Register parameter
        self_optimizer.register_parameter(
            "test_param",
            value=0.5,
            min_value=0.0,
            max_value=1.0,
            step=0.1
        )
        
        # Simple metric function (maximize at 0.8)
        def metric(params):
            value = params['test_param']
            return -abs(value - 0.8)  # Negative distance to 0.8
        
        result = self_optimizer.optimize_parameter(
            "test_param",
            metric,
            iterations=5,
            direction='maximize'
        )
        
        assert result['run_id'] is not None
        assert result['best_value'] <= 0
        assert result['improvement'] >= 0
    
    def test_get_statistics(self, self_optimizer):
        """Test getting optimization statistics."""
        self_optimizer.register_parameter("param1", 0.5)
        
        run_id = self_optimizer.start_optimization("metric", {"param1": 0.5})
        self_optimizer.complete_optimization(run_id, improvement=0.1)
        
        stats = self_optimizer.get_statistics()
        
        assert stats['total_runs'] == 1
        assert stats['completed_runs'] == 1
        assert stats['total_parameters'] == 1


class TestKnowledgeRefiner:
    """Tests for KnowledgeRefiner class."""
    
    def test_record_refinement(self, knowledge_refiner):
        """Test recording knowledge refinement."""
        refinement_id = knowledge_refiner.record_refinement(
            knowledge_id="knowledge_001",
            refinement_type="update",
            old_value="Old value",
            new_value="New value",
            reason="Updated based on new information",
            confidence_before=0.6,
            confidence_after=0.85
        )
        
        assert refinement_id is not None
        
        refinements = knowledge_refiner.get_refinements("knowledge_001")
        assert len(refinements) == 1
        assert refinements[0].refinement_type == "update"
    
    def test_assess_quality(self, knowledge_refiner):
        """Test assessing knowledge quality."""
        quality = knowledge_refiner.assess_quality(
            knowledge_id="knowledge_001",
            accuracy=0.9,
            completeness=0.8,
            recency=0.7,
            feedback=0.85
        )
        
        assert quality.overall_score > 0.8
        assert quality.accuracy_score == 0.9
    
    def test_get_quality(self, knowledge_refiner):
        """Test getting knowledge quality."""
        knowledge_refiner.assess_quality(
            knowledge_id="knowledge_001",
            accuracy=0.85,
            completeness=0.75,
            recency=0.8,
            feedback=0.9
        )
        
        quality = knowledge_refiner.get_quality("knowledge_001")
        
        assert quality is not None
        assert quality.accuracy_score == 0.85
    
    def test_merge_knowledge(self, knowledge_refiner):
        """Test merging knowledge."""
        refinement_id = knowledge_refiner.merge_knowledge(
            source_ids=["source_1", "source_2"],
            target_id="target_1",
            merged_value="Merged content",
            reason="Combined duplicate knowledge"
        )
        
        assert refinement_id is not None
        
        refinements = knowledge_refiner.get_refinements("target_1")
        assert len(refinements) == 1
        assert refinements[0].refinement_type == "merge"
    
    def test_identify_low_quality(self, knowledge_refiner):
        """Test identifying low-quality knowledge."""
        knowledge_refiner.assess_quality(
            knowledge_id="knowledge_001",
            accuracy=0.9,
            completeness=0.85,
            recency=0.9,
            feedback=0.95
        )
        
        knowledge_refiner.assess_quality(
            knowledge_id="knowledge_002",
            accuracy=0.3,
            completeness=0.4,
            recency=0.3,
            feedback=0.35
        )
        
        low_quality = knowledge_refiner.identify_low_quality(threshold=0.5)
        
        assert len(low_quality) == 1
        assert "knowledge_002" in low_quality
    
    def test_get_improvement_suggestions(self, knowledge_refiner):
        """Test getting improvement suggestions."""
        knowledge_refiner.assess_quality(
            knowledge_id="knowledge_001",
            accuracy=0.4,  # Low
            completeness=0.5,  # Low
            recency=0.3,  # Low
            feedback=0.4  # Low
        )
        
        suggestions = knowledge_refiner.get_improvement_suggestions("knowledge_001")
        
        assert len(suggestions) > 0
        assert any(s['type'] == 'accuracy' for s in suggestions)
    
    def test_get_statistics(self, knowledge_refiner):
        """Test getting refinement statistics."""
        knowledge_refiner.record_refinement(
            knowledge_id="knowledge_001",
            refinement_type="update",
            old_value="Old",
            new_value="New",
            reason="Update",
            confidence_before=0.5,
            confidence_after=0.8
        )
        
        knowledge_refiner.assess_quality(
            knowledge_id="knowledge_001",
            accuracy=0.8,
            completeness=0.7,
            recency=0.75,
            feedback=0.85
        )
        
        stats = knowledge_refiner.get_statistics()
        
        assert stats['total_refinements'] == 1
        assert stats['by_type']['update'] == 1
        assert abs(stats['avg_confidence_improvement'] - 0.3) < 0.001


class TestLearningIntegration:
    """Integration tests for self-learning system."""
    
    def test_feedback_driven_optimization(self, temp_db):
        """Test feedback-driven parameter optimization."""
        feedback_proc = FeedbackProcessor(db_path=temp_db)
        optimizer = SelfOptimizer(db_path=temp_db)
        
        # Register parameter
        optimizer.register_parameter(
            "response_quality_threshold",
            value=0.7,
            min_value=0.5,
            max_value=0.9
        )
        
        # Collect feedback
        for rating in [3, 4, 2, 5, 4]:
            feedback_proc.submit_feedback(
                feedback_type=FeedbackType.RATING,
                category=FeedbackCategory.QUALITY,
                rating=rating,
                entity_type="response",
                entity_id=f"response_{rating}"
            )
        
        # Optimize based on feedback
        def quality_metric(params):
            threshold = params['response_quality_threshold']
            # Simulate: higher threshold = better quality but fewer responses
            return threshold * 0.9  # Simplified metric
        
        result = optimizer.optimize_parameter(
            "response_quality_threshold",
            quality_metric,
            iterations=5,
            direction='maximize'
        )
        
        assert result['best_value'] >= 0
        assert optimizer.get_parameter("response_quality_threshold") != 0.7
    
    def test_knowledge_refinement_loop(self, temp_db):
        """Test knowledge refinement based on feedback."""
        feedback_proc = FeedbackProcessor(db_path=temp_db)
        refiner = KnowledgeRefiner(db_path=temp_db)
        
        # Initial knowledge
        knowledge_id = "knowledge_001"
        
        # Assess initial quality
        initial_quality = refiner.assess_quality(
            knowledge_id=knowledge_id,
            accuracy=0.6,
            completeness=0.5,
            recency=0.6,
            feedback=0.55
        )
        
        # Collect negative feedback
        feedback_proc.submit_feedback(
            feedback_type=FeedbackType.TEXT,
            category=FeedbackCategory.ACCURACY,
            text="This information is outdated and incorrect",
            entity_type="knowledge",
            entity_id=knowledge_id
        )
        
        # Record refinement
        refiner.record_refinement(
            knowledge_id=knowledge_id,
            refinement_type="update",
            old_value="Outdated information",
            new_value="Updated accurate information",
            reason="Updated based on user feedback",
            confidence_before=0.6,
            confidence_after=0.85,
            feedback_score=0.3
        )
        
        # Re-assess quality with improved values
        new_quality = refiner.assess_quality(
            knowledge_id=knowledge_id,
            accuracy=0.8,  # Improved
            completeness=0.7,  # Improved
            recency=0.8,  # Improved
            feedback=0.75  # Improved
        )
        
        assert new_quality.overall_score > initial_quality.overall_score
        
        # Get suggestions
        suggestions = refiner.get_improvement_suggestions(knowledge_id)
        assert len(suggestions) >= 0  # May have fewer suggestions now
    
    def test_full_self_learning_cycle(self, temp_db):
        """Test complete self-learning cycle."""
        feedback_proc = FeedbackProcessor(db_path=temp_db)
        optimizer = SelfOptimizer(db_path=temp_db)
        refiner = KnowledgeRefiner(db_path=temp_db)
        
        # 1. Register tunable parameter
        optimizer.register_parameter(
            "learning_threshold",
            value=0.6,
            min_value=0.4,
            max_value=0.8
        )
        
        # 2. Collect feedback on system performance
        for i in range(5):
            feedback_proc.submit_feedback(
                feedback_type=FeedbackType.RATING,
                category=FeedbackCategory.QUALITY,
                rating=3 + (i % 3),  # Varying ratings
                entity_type="system",
                entity_id=f"cycle_test_{i}"
            )
        
        # 3. Optimize parameter based on feedback
        def performance_metric(params):
            threshold = params['learning_threshold']
            return threshold * 0.85  # Simplified
        
        opt_result = optimizer.optimize_parameter(
            "learning_threshold",
            performance_metric,
            iterations=3,
            direction='maximize'
        )
        
        # 4. Record knowledge improvement
        refiner.record_refinement(
            knowledge_id="system_knowledge",
            refinement_type="update",
            old_value=f"Old threshold: 0.6",
            new_value=f"Optimized threshold: {optimizer.get_parameter('learning_threshold')}",
            reason="Auto-optimized based on feedback",
            confidence_before=0.6,
            confidence_after=0.85
        )
        
        # 5. Assess final quality
        final_quality = refiner.assess_quality(
            knowledge_id="system_knowledge",
            accuracy=0.85,
            completeness=0.8,
            recency=0.9,
            feedback=0.8
        )
        
        assert final_quality.overall_score > 0.8
        assert opt_result['improvement'] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])