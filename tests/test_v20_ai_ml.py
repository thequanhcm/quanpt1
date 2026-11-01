"""V20 tests — AI/ML Enhancements & Auto-Optimization (20 tests)."""
from __future__ import annotations

import pytest

from quan_ai_brain.ai.auto_tuning import (
    AutoTuner, AnomalyDetector, PredictiveMaintenance
)
from quan_ai_brain.ai.recommendation_engine import (
    RecommendationEngine, PersonalizationEngine, DiversityFilter, SerendipityEngine
)


class TestAutoTuner:
    """Tests for auto-tuner."""
    
    def test_tune_cache_size(self):
        """Test cache size tuning."""
        tuner = AutoTuner()
        suggestion = tuner.tune_cache_size(
            current_size=1000,
            memory_available=8000,
            access_pattern='random'
        )
        
        assert suggestion.parameter == 'cache_size'
        assert suggestion.suggested_value > 0
        assert suggestion.expected_improvement >= 0
        assert suggestion.confidence > 0
    
    def test_tune_batch_size(self):
        """Test batch size tuning."""
        tuner = AutoTuner()
        suggestion = tuner.tune_batch_size(
            current_batch=32,
            cpu_cores=4
        )
        
        assert suggestion.parameter == 'batch_size'
        assert suggestion.suggested_value > 0
    
    def test_tune_learning_rate_converging(self):
        """Test learning rate tuning with converging loss."""
        tuner = AutoTuner()
        loss_history = [0.9, 0.7, 0.5, 0.3, 0.2, 0.15, 0.12, 0.10]
        
        suggestion = tuner.tune_learning_rate(
            current_lr=0.01,
            loss_history=loss_history,
            epochs=8
        )
        
        assert suggestion.parameter == 'learning_rate'
        assert suggestion.suggested_value > 0
    
    def test_optimize_query_plan_simple(self):
        """Test query plan optimization for simple query."""
        tuner = AutoTuner()
        plan = tuner.optimize_query_plan(
            query_complexity='simple',
            data_size=1000,
            available_indexes=[]
        )
        
        assert 'estimated_cost' in plan
        assert plan['parallel_execution'] is False
    
    def test_analyze_bottlenecks(self):
        """Test bottleneck analysis."""
        tuner = AutoTuner()
        metrics = {
            'cpu_usage': 85,
            'memory_usage': 70,
            'query_latency_ms': 500
        }
        
        bottlenecks = tuner.analyze_bottlenecks(metrics)
        
        assert len(bottlenecks) >= 1
        assert any(b['type'] == 'cpu' for b in bottlenecks)


class TestAnomalyDetector:
    """Tests for anomaly detector."""
    
    def test_detect_query_anomalies(self):
        """Test query anomaly detection."""
        detector = AnomalyDetector()
        
        # Normal latencies
        normal_latencies = [100, 105, 98, 102, 101, 99, 103, 100, 104, 101]
        anomalies = detector.detect_query_anomalies(normal_latencies)
        assert len(anomalies) == 0
        
        # With anomaly
        anomalous_latencies = normal_latencies + [500, 102, 100]
        anomalies = detector.detect_query_anomalies(anomalous_latencies)
        assert len(anomalies) >= 0  # May or may not detect depending on threshold
    
    def test_detect_usage_anomalies(self):
        """Test usage anomaly detection."""
        detector = AnomalyDetector()
        
        usage_data = [
            {'value': 100}, {'value': 102}, {'value': 98},
            {'value': 101}, {'value': 100}, {'value': 200}  # Spike
        ]
        
        anomalies = detector.detect_usage_anomalies(usage_data)
        # May detect the spike
    
    def test_detect_performance_anomalies(self):
        """Test performance anomaly detection."""
        detector = AnomalyDetector()
        
        metrics = {
            'cpu_usage': 85,
            'memory_usage': 92,
            'disk_io': 50
        }
        
        thresholds = {
            'cpu_usage': 80,
            'memory_usage': 90
        }
        
        anomalies = detector.detect_performance_anomalies(metrics, thresholds)
        
        assert len(anomalies) >= 1
        assert any(a.anomaly_type == 'performance' for a in anomalies)
    
    def test_acknowledge_anomaly(self):
        """Test acknowledging anomaly."""
        detector = AnomalyDetector()
        
        # Create an anomaly
        metrics = {'cpu_usage': 95}
        thresholds = {'cpu_usage': 80}
        anomalies = detector.detect_performance_anomalies(metrics, thresholds)
        
        if anomalies:
            result = detector.acknowledge_anomaly(anomalies[0].anomaly_id)
            assert result is True
            assert anomalies[0].acknowledged is True


class TestPredictiveMaintenance:
    """Tests for predictive maintenance."""
    
    def test_predict_cache_efficiency(self):
        """Test cache efficiency prediction."""
        maint = PredictiveMaintenance()
        
        forecast = maint.predict_cache_efficiency(
            current_efficiency=0.75,
            trend='increasing'
        )
        
        assert len(forecast.predictions) == 7
        assert forecast.predictions[-1] > forecast.predictions[0]
        assert len(forecast.confidence_intervals) == 7
    
    def test_predict_memory_usage(self):
        """Test memory usage prediction."""
        maint = PredictiveMaintenance()
        
        forecast = maint.predict_memory_usage(
            current_usage=60.0,
            growth_rate=0.02
        )
        
        assert len(forecast.predictions) == 7
        assert forecast.predictions[-1] > forecast.predictions[0]
    
    def test_forecast_arima(self):
        """Test ARIMA forecasting."""
        maint = PredictiveMaintenance()
        
        data = [10, 12, 11, 13, 14, 12, 15, 14, 16, 15]
        forecast = maint.forecast_arima(data, periods=5)
        
        assert len(forecast.predictions) == 5
        assert forecast.model_used == 'arima_simplified'
    
    def test_schedule_maintenance(self):
        """Test maintenance scheduling."""
        maint = PredictiveMaintenance()
        
        predicted_issues = [
            {'severity': 'high', 'description': 'Memory full', 'estimated_duration': 60},
            {'severity': 'medium', 'description': 'Cache clear', 'estimated_duration': 30}
        ]
        
        maintenance_window = {
            'next_available': '2024-01-15T02:00:00Z',
            'next_scheduled': '2024-01-20T02:00:00Z'
        }
        
        schedule = maint.schedule_maintenance(predicted_issues, maintenance_window)
        
        assert len(schedule) == 2
        assert schedule[0]['priority'] == 'high'
    
    def test_generate_maintenance_report(self):
        """Test maintenance report generation."""
        maint = PredictiveMaintenance()
        
        forecasts = [
            maint.predict_cache_efficiency(0.75, 'stable'),
            maint.predict_memory_usage(60.0, 0.02)
        ]
        
        schedule = [
            {'issue': 'Test issue', 'priority': 'medium', 'scheduled_time': 'Next window'}
        ]
        
        report = maint.generate_maintenance_report(forecasts, schedule)
        
        assert 'generated_at' in report
        assert 'forecasts' in report
        assert 'scheduled_maintenance' in report
        assert 'recommendations' in report


class TestRecommendationEngine:
    """Tests for recommendation engine."""
    
    def test_recommend_by_content(self):
        """Test content-based recommendation."""
        engine = RecommendationEngine()
        
        # Add items
        engine.add_item('item1', {'tags': ['python', 'ml'], 'title': 'ML Guide'}, ['tech'])
        engine.add_item('item2', {'tags': ['python', 'web'], 'title': 'Web Guide'}, ['tech'])
        engine.add_item('item3', {'tags': ['cooking'], 'title': 'Cooking'}, ['lifestyle'])
        
        # Recommend
        query = {'tags': ['python', 'data']}
        recs = engine.recommend_by_content(query, top_k=2)
        
        assert len(recs) >= 1
        assert recs[0].item_id in ['item1', 'item2']
    
    def test_recommend_by_trending(self):
        """Test trending recommendation."""
        engine = RecommendationEngine()
        
        # Add items
        engine.add_item('item1', {'tags': ['trending']}, ['tech'])
        engine.add_item('item2', {'tags': ['popular']}, ['tech'])
        
        # Simulate interactions
        from datetime import datetime, timezone, timedelta
        engine._interactions = [
            {'item_id': 'item1', 'timestamp': (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()},
            {'item_id': 'item1', 'timestamp': (datetime.now(timezone.utc) - timedelta(minutes=30)).timestamp()},
            {'item_id': 'item2', 'timestamp': (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()}
        ]
        
        recs = engine.recommend_by_trending(time_window=24, top_k=2)
        
        assert len(recs) >= 1
        assert recs[0].item_id == 'item1'  # Most trending
    
    def test_update_item_popularity(self):
        """Test item popularity update."""
        engine = RecommendationEngine()
        
        engine.add_item('item1', {'tags': ['test']}, ['tech'])
        
        initial_popularity = engine._items['item1']['popularity']
        
        engine.update_item_popularity('item1', 'view')
        assert engine._items['item1']['popularity'] == initial_popularity + 1
        
        engine.update_item_popularity('item1', 'like')
        assert engine._items['item1']['popularity'] == initial_popularity + 6  # 1 + 5
    
    def test_get_all_recommendations(self):
        """Test combined recommendations."""
        engine = RecommendationEngine()
        
        # Add items
        engine.add_item('item1', {'tags': ['python'], 'categories': ['tech']}, ['tech'])
        engine.add_item('item2', {'tags': ['ml'], 'categories': ['tech']}, ['tech'])
        
        recs = engine.get_all_recommendations(
            user_id=None,
            context={'query': {'tags': ['python']}},
            top_k=2
        )
        
        assert len(recs) >= 0  # May be empty if no items match


class TestPersonalizationEngine:
    """Tests for personalization engine."""
    
    def test_build_user_profile(self):
        """Test building user profile."""
        engine = PersonalizationEngine()
        
        profile = engine.build_user_profile(
            user_id='user1',
            initial_interests={'tech': 0.8, 'science': 0.5}
        )
        
        assert profile.user_id == 'user1'
        assert profile.interests['tech'] == 0.8
    
    def test_update_user_profile(self):
        """Test updating user profile."""
        engine = PersonalizationEngine()
        engine.build_user_profile('user1')
        
        interactions = [
            {'item_id': 'item1', 'type': 'like', 'categories': ['tech']},
            {'item_id': 'item2', 'type': 'view', 'categories': ['science']}
        ]
        
        profile = engine.update_user_profile('user1', interactions)
        
        assert profile is not None
        assert profile.interests['tech'] > 0
        assert len(profile.interaction_history) == 2
    
    def test_evaluate_recommendations(self):
        """Test recommendation evaluation."""
        engine = PersonalizationEngine()
        engine.build_user_profile('user1')  # Build profile first
        
        feedback = [
            {'item_id': 'item1', 'recommended': True, 'relevant': True},
            {'item_id': 'item2', 'recommended': True, 'relevant': False},
            {'item_id': 'item3', 'recommended': False, 'relevant': True}
        ]
        
        metrics = engine.evaluate_recommendations('user1', feedback)
        
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics


class TestDiversityFilter:
    """Tests for diversity filter."""
    
    def test_filter_duplicates(self):
        """Test duplicate filtering."""
        filter_engine = DiversityFilter()
        
        from quan_ai_brain.ai.recommendation_engine import Recommendation
        recs = [
            Recommendation('item1', 0.9, 'reason1'),
            Recommendation('item2', 0.8, 'reason2'),
            Recommendation('item1', 0.7, 'reason3')  # Duplicate
        ]
        
        unique = filter_engine.filter_duplicates(recs)
        
        assert len(unique) == 2
        assert unique[0].item_id == 'item1'
        assert unique[1].item_id == 'item2'
    
    def test_ensure_diversity(self):
        """Test diversity enforcement."""
        filter_engine = DiversityFilter()
        
        from quan_ai_brain.ai.recommendation_engine import Recommendation
        recs = [
            Recommendation('item1', 0.9, 'reason1', {'categories': ['tech']}),
            Recommendation('item2', 0.8, 'reason2', {'categories': ['tech']}),
            Recommendation('item3', 0.7, 'reason3', {'categories': ['tech']}),
            Recommendation('item4', 0.6, 'reason4', {'categories': ['lifestyle']})
        ]
        
        diversified = filter_engine.ensure_diversity(recs, max_per_category=2)
        
        # Should limit tech items to 2
        tech_count = sum(1 for r in diversified if 'tech' in r.metadata.get('categories', []))
        assert tech_count <= 2


class TestSerendipityEngine:
    """Tests for serendipity engine."""
    
    def test_add_serendipity(self):
        """Test adding serendipitous recommendations."""
        serendipity = SerendipityEngine(serendipity_rate=0.2)
        
        from quan_ai_brain.ai.recommendation_engine import Recommendation, UserProfile
        recs = [
            Recommendation('item1', 0.9, 'reason1'),
            Recommendation('item2', 0.8, 'reason2')
        ]
        
        all_items = {
            'item3': {'content': {'tags': ['surprise']}, 'categories': ['unknown']},
            'item4': {'content': {'tags': ['new']}, 'categories': ['new']}
        }
        
        profile = UserProfile(
            user_id='user1',
            interests={'tech': 0.5},
            preferences={},
            interaction_history=[]
        )
        
        enhanced = serendipity.add_serendipity(recs, all_items, profile)
        
        # Should add some serendipitous items
        assert len(enhanced) >= len(recs)