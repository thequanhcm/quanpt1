"""
Tests for V26 Self-Learning & Optimization modules (V26.2 - V26.5)

Covers:
- TestSelfLearningEngine: experience buffer, pattern extraction, epsilon-greedy
  policy, regression check, policy apply/rollback (V26.2)
- TestAdaptiveAlgorithms: dynamic thresholds, adaptive batch/timeout, cooldown,
  strategy selection (V26.3)
- TestImprovementLoop: measure/analyze/propose/validate/apply/verify cycle,
  audit trail, max iterations, fail-safe revert, AutoTuner reuse (V26.4)
- TestIntelligentCache: TTL, LRU, adaptive capacity, prefetch, prefix
  invalidation, statistics (V26.5)
- TestV26Integration: cross-module workflows

All tests are stdlib-only, deterministic and run fully in-memory.
"""

import random
import statistics
import threading
import time
from datetime import datetime, timedelta

import pytest

from quan_ai_brain.optimization.self_learning_engine import (
    Experience,
    ExperienceBuffer,
    LearnedPattern,
    PatternExtractor,
    PolicyVersion,
    RegressionReport,
    EpsilonGreedyPolicy,
    SelfLearningEngine,
)

from quan_ai_brain.optimization.adaptive_algorithms import (
    AdaptiveConfig,
    AdaptiveStrategySelector,
    CooldownController,
    DynamicThreshold,
    ThresholdResult,
    percentile,
)

from quan_ai_brain.optimization.improvement_loop import (
    AuditEntry,
    ChangeProposal,
    ImprovementAnalyzer,
    ImprovementLoop,
    MetricSnapshot,
    SandboxValidator,
    _AUTOTUNER_AVAILABLE,
)

from quan_ai_brain.optimization.intelligent_cache import (
    CacheEntry,
    CacheStats,
    IntelligentCache,
    TTLIndex,
)


# ======================================================================
# M2 - Self-Learning Engine
# ======================================================================
class TestExperienceBuffer:
    """Test the experience buffer (V26.2)."""

    def test_create_empty_buffer(self):
        buffer = ExperienceBuffer()
        assert buffer.size == 0
        assert buffer.is_empty

    def test_add_experience(self):
        buffer = ExperienceBuffer()
        exp = buffer.add_experience(state='s1', action='a1', reward=1.0,
                                    outcome='good')
        assert buffer.size == 1
        assert exp.state == 's1'
        assert exp.action == 'a1'
        assert exp.reward == 1.0

    def test_buffer_max_size_eviction(self):
        buffer = ExperienceBuffer(max_size=3)
        for i in range(5):
            buffer.add_experience(state=f's{i}', action='a', reward=float(i))
        assert buffer.size == 3
        # oldest evicted
        assert buffer.all()[0].state == 's2'
        assert buffer.all()[-1].state == 's4'

    def test_recent_returns_last_n(self):
        buffer = ExperienceBuffer()
        for i in range(10):
            buffer.add_experience(state=f's{i}', action='a', reward=0.0)
        recent = buffer.recent(3)
        assert len(recent) == 3
        assert [e.state for e in recent] == ['s7', 's8', 's9']

    def test_sample_size(self):
        rng = random.Random(42)
        buffer = ExperienceBuffer()
        for i in range(50):
            buffer.add_experience(state=f's{i}', action='a', reward=0.0)
        sample = buffer.sample(10)
        assert len(sample) == 10
        assert len(set(id(e) for e in sample)) == 10

    def test_sample_larger_than_buffer(self):
        buffer = ExperienceBuffer()
        buffer.add_experience(state='s', action='a', reward=0.0)
        assert len(buffer.sample(5)) == 1

    def test_filter_by_state(self):
        buffer = ExperienceBuffer()
        buffer.add_experience(state='s1', action='a1', reward=1.0)
        buffer.add_experience(state='s2', action='a1', reward=0.5)
        buffer.add_experience(state='s1', action='a2', reward=2.0)
        result = buffer.filter(state='s1')
        assert len(result) == 2
        assert all(e.state == 's1' for e in result)

    def test_filter_by_outcome_and_reward(self):
        buffer = ExperienceBuffer()
        buffer.add_experience(state='s1', action='a1', reward=1.0, outcome='good')
        buffer.add_experience(state='s1', action='a1', reward=-1.0, outcome='bad')
        result = buffer.filter(state='s1', outcome='good')
        assert len(result) == 1
        result = buffer.filter(min_reward=0.0)
        assert len(result) == 1

    def test_clear(self):
        buffer = ExperienceBuffer()
        buffer.add_experience(state='s', action='a', reward=1.0)
        buffer.clear()
        assert buffer.is_empty

    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError):
            ExperienceBuffer(max_size=0)

    def test_to_dicts(self):
        buffer = ExperienceBuffer()
        buffer.add_experience(state='s', action='a', reward=1.0, outcome='good')
        data = buffer.to_dicts()
        assert len(data) == 1
        assert data[0]['state'] == 's'
        assert data[0]['reward'] == 1.0

    def test_experience_key_and_dict(self):
        exp = Experience(state='s', action='a', reward=1.5)
        assert exp.key == ('s', 'a')
        d = exp.to_dict()
        assert d['state'] == 's' and d['reward'] == 1.5


class TestPatternExtractor:
    """Test pattern extraction (V26.2)."""

    def _fill(self, buffer):
        # s1 -> a1 succeeds 4/5; s1 -> a2 fails 3/3; s2 -> a1 succeeds 2/2
        for i in range(4):
            buffer.add_experience('s1', 'a1', 1.0, 'good')
        buffer.add_experience('s1', 'a1', 0.0, 'bad')
        for _ in range(3):
            buffer.add_experience('s1', 'a2', -1.0, 'bad')
        for _ in range(2):
            buffer.add_experience('s2', 'a1', 1.0, 'good')

    def test_extract_basic(self):
        buffer = ExperienceBuffer()
        self._fill(buffer)
        extractor = PatternExtractor()
        patterns = extractor.extract(buffer)
        assert len(patterns) == 3

    def test_frequency_counts(self):
        buffer = ExperienceBuffer()
        self._fill(buffer)
        patterns = PatternExtractor().extract(buffer)
        by_key = {(p.state, p.action): p for p in patterns}
        assert by_key[('s1', 'a1')].frequency == 5
        assert by_key[('s1', 'a2')].frequency == 3
        assert by_key[('s2', 'a1')].frequency == 2

    def test_success_rate(self):
        buffer = ExperienceBuffer()
        self._fill(buffer)
        patterns = PatternExtractor().extract(buffer)
        by_key = {(p.state, p.action): p for p in patterns}
        assert by_key[('s1', 'a1')].success_rate == pytest.approx(0.8)
        assert by_key[('s1', 'a2')].success_rate == pytest.approx(0.0)
        assert by_key[('s2', 'a1')].success_rate == pytest.approx(1.0)

    def test_sorted_by_frequency_desc(self):
        buffer = ExperienceBuffer()
        self._fill(buffer)
        patterns = PatternExtractor().extract(buffer)
        freqs = [p.frequency for p in patterns]
        assert freqs == sorted(freqs, reverse=True)

    def test_min_frequency_filter(self):
        buffer = ExperienceBuffer()
        self._fill(buffer)
        patterns = PatternExtractor().extract(buffer, min_frequency=3)
        assert {(p.state, p.action) for p in patterns} == {('s1', 'a1'), ('s1', 'a2')}

    def test_good_reward_threshold(self):
        buffer = ExperienceBuffer()
        buffer.add_experience('s', 'a', 5.0, 'neutral')
        patterns = PatternExtractor(good_reward_threshold=4.0).extract(buffer)
        assert patterns[0].good_count == 1

    def test_pattern_confidence(self):
        buffer = ExperienceBuffer()
        buffer.add_experience('s1', 'a1', 1.0, 'good')
        buffer.add_experience('s1', 'a2', 1.0, 'good')
        patterns = PatternExtractor().extract(buffer)
        by_key = {(p.state, p.action): p for p in patterns}
        assert by_key[('s1', 'a1')].confidence == pytest.approx(0.5)

    def test_empty_buffer_no_patterns(self):
        assert PatternExtractor().extract(ExperienceBuffer()) == []

    def test_avg_reward(self):
        buffer = ExperienceBuffer()
        buffer.add_experience('s', 'a', 1.0, 'good')
        buffer.add_experience('s', 'a', 3.0, 'good')
        patterns = PatternExtractor().extract(buffer)
        assert patterns[0].avg_reward == pytest.approx(2.0)


class TestEpsilonGreedyPolicy:
    """Test the epsilon-greedy bandit policy (V26.2)."""

    def test_select_from_actions(self):
        policy = EpsilonGreedyPolicy(actions=['a1', 'a2'], epsilon=0.0)
        assert policy.select_action('s') in ('a1', 'a2')

    def test_no_actions_returns_none(self):
        policy = EpsilonGreedyPolicy(epsilon=0.0)
        assert policy.select_action('s') is None

    def test_greedy_prefers_higher_value(self):
        policy = EpsilonGreedyPolicy(actions=['a1', 'a2'], epsilon=0.0)
        for _ in range(10):
            policy.update('s', 'a1', 1.0)
        for _ in range(10):
            policy.update('s', 'a2', 0.1)
        assert policy.select_action('s') == 'a1'
        assert policy.best_action('s') == 'a1'

    def test_unknown_pair_uses_default(self):
        policy = EpsilonGreedyPolicy(default_value=0.0)
        assert policy.expected_reward('s', 'a') == 0.0
        assert policy.value('s', 'a') is None

    def test_update_incremental_mean(self):
        policy = EpsilonGreedyPolicy()
        policy.update('s', 'a', 2.0)
        assert policy.expected_reward('s', 'a') == pytest.approx(2.0)
        policy.update('s', 'a', 4.0)
        assert policy.expected_reward('s', 'a') == pytest.approx(3.0)
        policy.update('s', 'a', 6.0)
        assert policy.expected_reward('s', 'a') == pytest.approx(4.0)

    def test_count_tracking(self):
        policy = EpsilonGreedyPolicy()
        policy.update('s', 'a', 1.0)
        policy.update('s', 'a', 1.0)
        assert policy.count('s', 'a') == 2
        assert policy.count('s', 'b') == 0

    def test_epsilon_one_always_explores(self):
        rng = random.Random(7)
        policy = EpsilonGreedyPolicy(actions=['a1', 'a2'], epsilon=1.0, rng=rng)
        choices = {policy.select_action('s') for _ in range(50)}
        # with eps=1 both actions should eventually appear
        assert choices <= {'a1', 'a2'}
        assert choices == {'a1', 'a2'}

    def test_epsilon_zero_deterministic(self):
        rng = random.Random(7)
        policy = EpsilonGreedyPolicy(actions=['a1', 'a2'], epsilon=0.0, rng=rng)
        policy.update('s', 'a2', 5.0)
        assert all(policy.select_action('s') == 'a2' for _ in range(20))

    def test_snapshot_roundtrip(self):
        policy = EpsilonGreedyPolicy(actions=['a1', 'a2'], epsilon=0.2)
        policy.update('s', 'a1', 1.0)
        policy.update('s', 'a2', 0.5)
        restored = EpsilonGreedyPolicy.from_snapshot(policy.snapshot())
        assert restored.epsilon == pytest.approx(0.2)
        assert restored.expected_reward('s', 'a1') == pytest.approx(1.0)
        assert restored.expected_reward('s', 'a2') == pytest.approx(0.5)
        assert restored.count('s', 'a1') == 1

    def test_clone_independent(self):
        policy = EpsilonGreedyPolicy(actions=['a1'], epsilon=0.0)
        policy.update('s', 'a1', 1.0)
        clone = policy.clone()
        clone.update('s', 'a1', 100.0)
        assert policy.expected_reward('s', 'a1') == pytest.approx(1.0)
        # clone now holds the incremental mean of (1, 100)
        assert clone.expected_reward('s', 'a1') == pytest.approx(50.5)
        assert clone.count('s', 'a1') == 2
        assert policy.count('s', 'a1') == 1

    def test_available_actions_override(self):
        policy = EpsilonGreedyPolicy(actions=['a1', 'a2'], epsilon=0.0)
        assert policy.select_action('s', available_actions=['a2']) == 'a2'

    def test_known_pairs(self):
        policy = EpsilonGreedyPolicy()
        policy.update('s1', 'a1', 1.0)
        policy.update('s2', 'a2', 1.0)
        assert ('s1', 'a1') in policy.known_pairs()


class TestSelfLearningEngine:
    """Test the full self-learning engine (V26.2)."""

    def _engine_with_data(self, min_experiences=5):
        engine = SelfLearningEngine(
            actions=['a1', 'a2'], epsilon=0.0,
            min_experiences=min_experiences, min_improvement=0.0,
            rng=random.Random(123),
        )
        # a1 is clearly better in s1
        for _ in range(4):
            engine.record_experience('s1', 'a1', 1.0, 'good')
        for _ in range(2):
            engine.record_experience('s1', 'a2', 0.0, 'bad')
        return engine

    def test_initial_state(self):
        engine = SelfLearningEngine(actions=['a1', 'a2'], epsilon=0.0)
        stats = engine.get_stats()
        assert stats['buffer_size'] == 0
        assert stats['current_version'] == 'v0'
        assert stats['learn_cycles'] == 0

    def test_record_experience(self):
        engine = SelfLearningEngine()
        engine.record_experience('s', 'a', 1.0, 'good')
        assert engine.buffer.size == 1

    def test_learn_returns_none_when_insufficient(self):
        engine = SelfLearningEngine(min_experiences=10)
        for _ in range(3):
            engine.record_experience('s', 'a', 1.0)
        assert engine.learn() is None

    def test_learn_applies_improvement(self):
        engine = self._engine_with_data()
        report = engine.learn()
        assert report is not None
        assert report.accepted
        assert engine.current_version.version_id == 'v1'
        assert engine.policy.expected_reward('s1', 'a1') == pytest.approx(1.0)

    def test_regression_check_detects_regression(self):
        engine = self._engine_with_data()
        # Craft a candidate that undervalues the known-good action
        candidate = engine.policy.clone()
        candidate._values[('s1', 'a1')] = -5.0
        report = engine.regression_check(candidate)
        assert not report.accepted
        assert report.reason == 'regression_detected'
        assert report.improvement < 0

    def test_regression_check_accepts_improvement(self):
        engine = self._engine_with_data()
        candidate = engine.propose_policy()
        report = engine.regression_check(candidate)
        assert report.accepted

    def test_regression_check_insufficient_data(self):
        engine = SelfLearningEngine(min_experiences=100)
        engine.record_experience('s', 'a', 1.0)
        candidate = engine.propose_policy()
        report = engine.regression_check(candidate)
        assert not report.accepted
        assert report.reason == 'insufficient_replay_data'

    def test_rejected_update_keeps_old_policy(self):
        engine = self._engine_with_data()
        baseline_value = engine.policy.expected_reward('s1', 'a1')
        candidate = engine.policy.clone()
        candidate._values[('s1', 'a1')] = -5.0
        report = engine.regression_check(candidate)
        assert not report.accepted
        # policy unchanged
        assert engine.policy.expected_reward('s1', 'a1') == baseline_value

    def test_rollback_policy(self):
        engine = self._engine_with_data()
        first = engine.learn()
        assert first.accepted
        # Make data worse so the next candidate is worse than v1? Instead
        # directly rollback: v1 -> v0
        removed = engine.rollback_policy()
        assert removed is not None
        assert removed.version_id == 'v1'
        assert engine.current_version.version_id == 'v0'
        assert engine.rollbacks == 1

    def test_rollback_nothing_to_revert(self):
        engine = SelfLearningEngine()
        assert engine.rollback_policy() is None

    def test_rollback_restores_values(self):
        engine = self._engine_with_data()
        engine.learn()
        engine.rollback_policy()
        # v0 had no learned values
        assert engine.policy.expected_reward('s1', 'a1') == 0.0

    def test_improvement_trend(self):
        engine = self._engine_with_data()
        engine.learn()
        trend = engine.improvement_trend()
        assert len(trend) == 2
        assert trend[1] >= trend[0]

    def test_select_action_greedy(self):
        engine = self._engine_with_data()
        engine.learn()
        assert engine.select_action('s1') == 'a1'

    def test_select_action_unknown_state_default(self):
        engine = SelfLearningEngine(actions=['a1', 'a2'], epsilon=0.0)
        assert engine.select_action('unknown') in ('a1', 'a2')

    def test_stats_after_learning(self):
        engine = self._engine_with_data()
        engine.learn()
        stats = engine.get_stats()
        assert stats['learn_cycles'] == 1
        assert stats['accepted_updates'] == 1
        assert stats['patterns_stored'] > 0
        assert stats['buffer_size'] == 6

    def test_extract_patterns_via_engine(self):
        engine = self._engine_with_data()
        patterns = engine.extract_patterns(min_frequency=1)
        assert any(p.state == 's1' and p.action == 'a1' for p in patterns)

    def test_multiple_learn_cycles(self):
        engine = self._engine_with_data()
        r1 = engine.learn()
        for _ in range(2):
            engine.record_experience('s1', 'a1', 1.0, 'good')
        r2 = engine.learn()
        assert r1.accepted and r2.accepted
        assert engine.current_version.version_id == 'v2'

    def test_min_improvement_blocks_tiny_gain(self):
        engine = SelfLearningEngine(actions=['a1'], epsilon=0.0,
                                    min_experiences=2, min_improvement=10.0,
                                    rng=random.Random(1))
        engine.record_experience('s', 'a1', 1.0, 'good')
        engine.record_experience('s', 'a1', 1.0, 'good')
        report = engine.learn()
        # candidate equals current (both 1.0), improvement 0 < 10 required
        assert report is not None and not report.accepted

    def test_epsilon_used_for_exploration(self):
        engine = SelfLearningEngine(actions=['a1', 'a2'], epsilon=1.0,
                                    min_experiences=1, rng=random.Random(9))
        engine.record_experience('s', 'a1', 1.0, 'good')
        engine.learn()
        choices = {engine.select_action('s') for _ in range(50)}
        assert choices == {'a1', 'a2'}


# ======================================================================
# M3 - Adaptive Algorithms
# ======================================================================
class TestPercentile:
    """Test the percentile helper (V26.3)."""

    def test_percentile_50(self):
        assert percentile([1, 2, 3, 4, 5], 50) == pytest.approx(3.0)

    def test_percentile_100(self):
        assert percentile([1, 2, 3], 100) == pytest.approx(3.0)

    def test_percentile_0(self):
        assert percentile([1, 2, 3], 0) == pytest.approx(1.0)

    def test_percentile_interpolation(self):
        assert percentile([10, 20], 50) == pytest.approx(15.0)

    def test_percentile_single_value(self):
        assert percentile([42], 95) == pytest.approx(42.0)

    def test_percentile_p95_of_range(self):
        values = list(range(1, 101))
        assert percentile(values, 95) == pytest.approx(95.05)

    def test_percentile_empty_raises(self):
        with pytest.raises(ValueError):
            percentile([], 50)

    def test_percentile_invalid_pct(self):
        with pytest.raises(ValueError):
            percentile([1, 2, 3], 150)


class TestDynamicThreshold:
    """Test dynamic percentile-based thresholds (V26.3)."""

    def test_static_fallback_before_min_samples(self):
        th = DynamicThreshold('lat', percentile_value=95, min_samples=5,
                              static_fallback=100.0)
        th.observe(10)
        result = th.evaluate(101)
        assert result.breached
        assert result.threshold == 100.0

    def test_threshold_from_percentile(self):
        th = DynamicThreshold('lat', percentile_value=95, min_samples=5,
                              window_size=10)
        for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            th.observe(v)
        expected = percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95)
        assert th.current_threshold() == pytest.approx(expected)

    def test_breach_above(self):
        th = DynamicThreshold('lat', percentile_value=50, min_samples=3,
                              direction='above')
        for v in [1, 2, 3]:
            th.observe(v)
        assert th.evaluate(10).breached
        assert not th.evaluate(2).breached

    def test_breach_below(self):
        th = DynamicThreshold('lat', percentile_value=50, min_samples=3,
                              direction='below')
        for v in [1, 2, 3]:
            th.observe(v)
        assert th.evaluate(0).breached
        assert not th.evaluate(2).breached

    def test_window_rollover(self):
        th = DynamicThreshold('lat', percentile_value=95, min_samples=2,
                              window_size=5)
        for v in [100] * 5:
            th.observe(v)
        for v in [1, 2, 3, 4, 5]:
            th.observe(v)
        # only last 5 values count
        assert th.current_threshold() == pytest.approx(percentile([1, 2, 3, 4, 5], 95))

    def test_absolute_tolerance(self):
        th = DynamicThreshold('lat', percentile_value=95, min_samples=3,
                              absolute_tolerance=10.0)
        for v in [1, 2, 3]:
            th.observe(v)
        assert th.current_threshold() == pytest.approx(percentile([1, 2, 3], 95) + 10.0)

    def test_result_fields(self):
        th = DynamicThreshold('lat', percentile_value=95, min_samples=3)
        for v in [1, 2, 3]:
            th.observe(v)
        result = th.evaluate(100)
        assert isinstance(result, ThresholdResult)
        assert result.metric_name == 'lat'
        assert result.value == 100
        assert result.sample_count == 3
        assert result.percentile == 95

    def test_reset(self):
        th = DynamicThreshold('lat', min_samples=1)
        th.observe(5)
        th.reset()
        assert th.current_threshold() is None

    def test_no_fallback_returns_none(self):
        th = DynamicThreshold('lat', min_samples=5)
        th.observe(1)
        assert th.current_threshold() is None

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            DynamicThreshold('lat', direction='sideways')

    def test_invalid_percentile_raises(self):
        with pytest.raises(ValueError):
            DynamicThreshold('lat', percentile_value=120)

    def test_stats(self):
        th = DynamicThreshold('lat', min_samples=3)
        for v in [1, 2, 3]:
            th.observe(v)
        stats = th.stats()
        assert stats['count'] == 3
        assert stats['max'] == 3
        assert stats['mean'] == pytest.approx(2.0)


class TestAdaptiveConfig:
    """Test adaptive batch size / timeout (V26.3)."""

    def test_no_data_no_adjustment(self):
        cfg = AdaptiveConfig()
        entry = cfg.adjust()
        assert not entry['adjusted']
        assert entry['reason'] == 'no_data'

    def test_headroom_increases_batch(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0)
        for _ in range(20):
            cfg.record_latency(5.0)  # p95 far below 0.5*30
        entry = cfg.adjust()
        assert entry['reason'] == 'headroom_increase_batch'
        assert entry['new_batch_size'] == 120
        assert entry['new_timeout'] == 30.0

    def test_pressure_reduces_batch_raises_timeout(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0)
        for _ in range(20):
            cfg.record_latency(29.0)  # p95 > 0.9*30
        entry = cfg.adjust()
        assert entry['reason'] == 'pressure_reduce_batch_raise_timeout'
        assert entry['new_batch_size'] == 70
        assert entry['new_timeout'] == pytest.approx(37.5)

    def test_stable_zone(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0)
        for _ in range(20):
            cfg.record_latency(20.0)  # between 0.5x and 0.9x
        entry = cfg.adjust()
        assert entry['reason'] == 'stable'
        assert entry['new_batch_size'] == 100

    def test_batch_size_clamped_to_bounds(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0,
                             min_batch_size=10, max_batch_size=110)
        for _ in range(20):
            cfg.record_latency(1.0)
        cfg.adjust()
        cfg.adjust()
        assert cfg.batch_size <= 110

    def test_timeout_clamped_to_bounds(self):
        cfg = AdaptiveConfig(initial_timeout=100.0, max_timeout=150.0)
        for _ in range(20):
            cfg.record_latency(99.0)
        cfg.adjust()
        cfg.adjust()
        cfg.adjust()
        assert cfg.timeout <= 150.0

    def test_history_records_adjustments(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0)
        for _ in range(20):
            cfg.record_latency(5.0)
        cfg.adjust()
        assert len(cfg.adjustment_history) == 1
        assert cfg.adjustment_history[0]['old_batch_size'] == 100

    def test_get_config(self):
        cfg = AdaptiveConfig(initial_batch_size=64, initial_timeout=12.0)
        assert cfg.get_config() == {'batch_size': 64, 'timeout': 12.0}

    def test_stats(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0)
        for _ in range(10):
            cfg.record_latency(10.0)
        stats = cfg.stats()
        assert stats['sample_count'] == 10
        assert stats['latency_p95'] == pytest.approx(10.0)

    def test_repeated_growth_compounds(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0)
        for _ in range(20):
            cfg.record_latency(5.0)
        cfg.adjust()
        first = cfg.batch_size
        cfg.adjust()
        assert cfg.batch_size > first


class TestCooldownController:
    """Test cooldown behaviour (V26.3)."""

    def test_first_change_allowed(self):
        cc = CooldownController(cooldown_seconds=60)
        assert cc.try_change('cache', now=datetime(2024, 10, 28, 12, 0, 0))

    def test_second_change_blocked_within_cooldown(self):
        cc = CooldownController(cooldown_seconds=60)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        assert cc.try_change('cache', now=t0)
        assert not cc.try_change('cache', now=t0 + timedelta(seconds=30))

    def test_change_allowed_after_cooldown(self):
        cc = CooldownController(cooldown_seconds=60)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        cc.try_change('cache', now=t0)
        assert cc.try_change('cache', now=t0 + timedelta(seconds=61))

    def test_force_overrides_cooldown(self):
        cc = CooldownController(cooldown_seconds=60)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        cc.try_change('cache', now=t0)
        assert cc.try_change('cache', now=t0 + timedelta(seconds=1), force=True)

    def test_independent_channels(self):
        cc = CooldownController(cooldown_seconds=60)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        cc.try_change('a', now=t0)
        assert cc.try_change('b', now=t0)

    def test_remaining_time(self):
        cc = CooldownController(cooldown_seconds=60)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        cc.try_change('cache', now=t0)
        assert cc.remaining('cache', now=t0 + timedelta(seconds=10)) == pytest.approx(50.0)
        assert cc.remaining('cache', now=t0 + timedelta(seconds=70)) == 0.0

    def test_change_count(self):
        cc = CooldownController(cooldown_seconds=10)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        cc.try_change('c', now=t0)
        cc.try_change('c', now=t0 + timedelta(seconds=20))
        assert cc.change_count('c') == 2

    def test_is_ready(self):
        cc = CooldownController(cooldown_seconds=60)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        assert cc.is_ready('x', now=t0)
        cc.try_change('x', now=t0)
        assert not cc.is_ready('x', now=t0 + timedelta(seconds=10))
        assert cc.is_ready('x', now=t0 + timedelta(seconds=60))

    def test_reset_channel(self):
        cc = CooldownController(cooldown_seconds=60)
        t0 = datetime(2024, 10, 28, 12, 0, 0)
        cc.try_change('a', now=t0)
        cc.try_change('b', now=t0)
        cc.reset('a')
        assert cc.is_ready('a', now=t0)
        assert not cc.is_ready('b', now=t0 + timedelta(seconds=5))

    def test_invalid_cooldown_raises(self):
        with pytest.raises(ValueError):
            CooldownController(cooldown_seconds=-1)


class TestAdaptiveStrategySelector:
    """Test context-based strategy selection (V26.3)."""

    def test_default_strategy(self):
        selector = AdaptiveStrategySelector(default_strategy='baseline')
        assert selector.select({'device': 'desktop'}) == 'baseline'

    def test_rule_matching(self):
        selector = AdaptiveStrategySelector(default_strategy='baseline')
        selector.add_rule('mobile', 'compact',
                          lambda ctx: ctx.get('device') == 'mobile')
        assert selector.select({'device': 'mobile'}) == 'compact'
        assert selector.select({'device': 'desktop'}) == 'baseline'

    def test_priority_order(self):
        selector = AdaptiveStrategySelector(default_strategy='baseline')
        selector.add_rule('low', 'A', lambda ctx: True, priority=1)
        selector.add_rule('high', 'B', lambda ctx: True, priority=10)
        assert selector.select({}) == 'B'

    def test_failing_predicate_skipped(self):
        selector = AdaptiveStrategySelector(default_strategy='baseline')
        selector.add_rule('never', 'X', lambda ctx: False, priority=10)
        selector.add_rule('always', 'Y', lambda ctx: True, priority=1)
        assert selector.select({}) == 'Y'

    def test_selection_counts(self):
        selector = AdaptiveStrategySelector(default_strategy='baseline')
        selector.add_rule('r1', 'S1', lambda ctx: ctx.get('k') == 1)
        selector.select({'k': 1})
        selector.select({'k': 1})
        selector.select({'k': 2})
        counts = selector.selection_counts()
        assert counts['S1'] == 2
        assert counts['baseline'] == 1


# ======================================================================
# M4 - Continuous Improvement Loop
# ======================================================================
def _make_metrics(**values) -> list:
    return [MetricSnapshot(name=k, value=v) for k, v in values.items()]


class TestSandboxValidator:
    """Test sandbox dry-run validation (V26.4)."""

    def test_no_simulator_invalid(self):
        validator = SandboxValidator()
        result = validator.validate({'a': 1}, [ChangeProposal(
            'p1', 'a', 1, 2, 'test')])
        assert not result['valid']
        assert result['reason'] == 'no_simulator_configured'

    def test_simulator_receives_sandbox_copy(self):
        seen = {}

        def sim(config, proposals):
            seen.update(config)
            return 1.0

        validator = SandboxValidator(simulate=sim)
        live = {'batch_size': 100}
        validator.validate(live, [ChangeProposal('p1', 'batch_size', 100, 50, 'r')])
        assert seen['batch_size'] == 50
        assert live['batch_size'] == 100  # untouched

    def test_valid_when_score_above_threshold(self):
        validator = SandboxValidator(simulate=lambda c, p: 0.5,
                                     min_expected_improvement=0.1)
        result = validator.validate({}, [])
        assert result['valid']

    def test_invalid_when_score_below_threshold(self):
        validator = SandboxValidator(simulate=lambda c, p: 0.05,
                                     min_expected_improvement=0.1)
        result = validator.validate({}, [])
        assert not result['valid']

    def test_simulator_exception_handled(self):
        def bad_sim(config, proposals):
            raise RuntimeError('boom')

        validator = SandboxValidator(simulate=bad_sim)
        result = validator.validate({}, [])
        assert not result['valid']
        assert 'simulator_error' in result['reason']

    def test_validation_count(self):
        validator = SandboxValidator(simulate=lambda c, p: 1.0)
        validator.validate({}, [])
        validator.validate({}, [])
        assert validator.validation_count == 2


class TestImprovementAnalyzer:
    """Test fallback analyzer (V26.4)."""

    def test_high_latency_detected(self):
        analyzer = ImprovementAnalyzer()
        findings = analyzer.analyze(_make_metrics(latency_p95=300.0))
        assert len(findings) == 1
        assert findings[0]['metric'] == 'latency_p95'

    def test_no_findings_when_healthy(self):
        analyzer = ImprovementAnalyzer()
        findings = analyzer.analyze(_make_metrics(latency_p95=100.0,
                                                  error_rate=0.1,
                                                  cache_hit_rate=95.0))
        assert findings == []

    def test_low_cache_hit_detected(self):
        analyzer = ImprovementAnalyzer()
        findings = analyzer.analyze(_make_metrics(cache_hit_rate=50.0))
        assert findings[0]['metric'] == 'cache_hit_rate'

    def test_unknown_metric_ignored(self):
        analyzer = ImprovementAnalyzer()
        assert analyzer.analyze(_make_metrics(exotic=1.0)) == []


class TestImprovementLoop:
    """Test the full improvement loop (V26.4)."""

    def _loop(self, metrics_sequence, verify_fn=None, config=None,
              validator=None, max_iterations=3):
        """Each element of ``metrics_sequence`` is one measurement batch
        (a list of MetricSnapshot) consumed by successive measure() calls."""
        sequence = list(metrics_sequence)

        def measure():
            if sequence:
                return sequence.pop(0)
            return []

        return ImprovementLoop(
            measure_fn=measure,
            verify_fn=verify_fn,
            config=config if config is not None else {'batch_size': 100,
                                                      'cache_size': 1000,
                                                      'retry_count': 3},
            validator=validator,
            max_iterations=max_iterations,
        )

    def test_autotuner_available(self):
        # V26.1 exists in this workspace, so the loop must detect it
        assert _AUTOTUNER_AVAILABLE

    def test_analyze_uses_autotuner(self):
        loop = self._loop([])
        findings = loop.analyze(_make_metrics(latency_p95=500.0,
                                              error_rate=2.0,
                                              cache_hit_rate=50.0,
                                              throughput=100.0,
                                              latency_p50=100.0,
                                              latency_p99=600.0,
                                              cpu_usage=90.0))
        assert findings, 'AutoTuner path should produce findings'
        assert all(f.get('source') == 'autotuner' for f in findings)

    def test_fallback_analyzer_used_for_few_samples(self):
        loop = self._loop([])
        findings = loop.analyze(_make_metrics(latency_p95=300.0,
                                              error_rate=0.5))
        assert findings
        assert all('source' not in f for f in findings)

    def test_propose_latency_proposal(self):
        loop = self._loop([])
        proposals = loop.propose([{'metric': 'latency_p95', 'value': 300.0,
                                   'threshold': 200.0}])
        assert len(proposals) == 1
        assert proposals[0].parameter == 'batch_size'
        assert proposals[0].proposed_value == 50

    def test_propose_error_rate_proposal(self):
        loop = self._loop([])
        proposals = loop.propose([{'metric': 'error_rate', 'value': 2.0,
                                   'threshold': 1.0}])
        assert proposals[0].parameter == 'retry_count'
        assert proposals[0].proposed_value == 4

    def test_propose_cache_proposal(self):
        loop = self._loop([])
        proposals = loop.propose([{'metric': 'cache_hit_rate', 'value': 50.0,
                                   'threshold': 90.0}])
        assert proposals[0].parameter == 'cache_size'
        assert proposals[0].proposed_value == 2000

    def test_apply_proposals_mutates_config(self):
        loop = self._loop([], config={'batch_size': 100})
        loop.apply_proposals([ChangeProposal('p', 'batch_size', 100, 42, 'r')])
        assert loop.config['batch_size'] == 42

    def test_revert_restores_backup(self):
        loop = self._loop([], config={'batch_size': 100})
        loop._backup_config()
        loop.config['batch_size'] = 999
        assert loop.revert()
        assert loop.config['batch_size'] == 100

    def test_revert_without_backup_returns_false(self):
        loop = self._loop([])
        assert not loop.revert()

    def test_iteration_no_findings_no_change(self):
        healthy = _make_metrics(latency_p95=100.0, error_rate=0.1,
                                cache_hit_rate=99.0)
        loop = self._loop([healthy])
        result = loop.run_iteration(1)
        assert result.status == 'no_change'
        assert loop.get_config()['batch_size'] == 100

    def test_full_improvement_cycle(self):
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        improved = _make_metrics(latency_p95=100.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        loop = self._loop(
            [baseline, improved],
            validator=SandboxValidator(simulate=lambda c, p: 0.5,
                                       min_expected_improvement=0.1))
        result = loop.run_iteration(1)
        assert result.status == 'improved'
        assert loop.get_config()['batch_size'] == 50
        steps = loop.get_audit_steps()
        assert steps == ['measure', 'analyze', 'propose', 'validate',
                         'apply', 'verify']

    def test_verify_failure_triggers_revert(self):
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        worse = _make_metrics(latency_p95=500.0, error_rate=0.1,
                              cache_hit_rate=99.0)
        loop = self._loop(
            [baseline, worse],
            validator=SandboxValidator(simulate=lambda c, p: 0.9,
                                       min_expected_improvement=0.1))
        result = loop.run_iteration(1)
        assert result.status == 'reverted'
        assert result.reverted
        assert loop.get_config()['batch_size'] == 100
        assert any(e.step == 'revert' and e.status == 'ok'
                   for e in loop.audit_log)

    def test_validation_failure_blocks_apply(self):
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        loop = self._loop(
            [baseline],
            validator=SandboxValidator(simulate=lambda c, p: 0.0,
                                       min_expected_improvement=0.5))
        result = loop.run_iteration(1)
        assert result.status == 'failed'
        assert loop.get_config()['batch_size'] == 100  # untouched
        steps = loop.get_audit_steps()
        assert 'apply' not in steps

    def test_audit_entries_recorded_every_step(self):
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        improved = _make_metrics(latency_p95=100.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        loop = self._loop(
            [baseline, improved],
            validator=SandboxValidator(simulate=lambda c, p: 0.5,
                                       min_expected_improvement=0.1))
        loop.run_iteration(1)
        log = loop.get_audit_log()
        assert len(log) == 6
        assert all(e['iteration'] == 1 for e in log)
        assert all(e['status'] == 'ok' for e in log)

    def test_run_stops_on_failure(self):
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        worse = _make_metrics(latency_p95=400.0, error_rate=0.1,
                              cache_hit_rate=99.0)
        loop = self._loop([baseline, worse, worse, worse],
                          validator=SandboxValidator(simulate=lambda c, p: 0.9,
                                                     min_expected_improvement=0.1))
        summary = loop.run()
        assert summary['iterations_run'] == 1
        assert summary['reverted'] == 1

    def test_run_respects_max_iterations(self):
        # each iteration reports high latency and improved metrics, so the
        # loop keeps improving until max_iterations
        def make_pair():
            baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                     cache_hit_rate=99.0)
            improved = _make_metrics(latency_p95=100.0, error_rate=0.1,
                                     cache_hit_rate=99.0)
            return [baseline, improved]

        seq = make_pair() * 5
        loop = self._loop(
            seq, max_iterations=3,
            validator=SandboxValidator(simulate=lambda c, p: 0.5,
                                       min_expected_improvement=0.1))
        summary = loop.run()
        assert summary['iterations_run'] == 3
        assert summary['improved'] == 3

    def test_invalid_max_iterations_raises(self):
        with pytest.raises(ValueError):
            ImprovementLoop(measure_fn=lambda: [], max_iterations=0)

    def test_default_verify_lower_is_better(self):
        assert ImprovementLoop._default_verify({'latency_p95': 100.0},
                                               {'latency_p95': 50.0})
        assert not ImprovementLoop._default_verify({'latency_p95': 100.0},
                                                   {'latency_p95': 200.0})

    def test_default_verify_higher_is_better(self):
        assert ImprovementLoop._default_verify({'cache_hit_rate': 80.0},
                                               {'cache_hit_rate': 95.0})
        assert not ImprovementLoop._default_verify({'cache_hit_rate': 80.0},
                                                   {'cache_hit_rate': 70.0})

    def test_measure_exception_during_verify_reverts(self):
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        calls = {'n': 0}

        def measure():
            calls['n'] += 1
            if calls['n'] == 1:
                return baseline
            raise RuntimeError('sensor failure')

        loop = ImprovementLoop(
            measure_fn=measure,
            config={'batch_size': 100, 'cache_size': 1000, 'retry_count': 3},
            validator=SandboxValidator(simulate=lambda c, p: 0.5,
                                       min_expected_improvement=0.1))
        result = loop.run_iteration(1)
        assert result.status == 'reverted'
        assert loop.get_config()['batch_size'] == 100

    def test_to_dict_roundtrip(self):
        proposal = ChangeProposal('p1', 'batch_size', 100, 50, 'r')
        entry = AuditEntry(step='apply', iteration=1, status='ok')
        assert proposal.to_dict()['proposed_value'] == 50
        assert entry.to_dict()['step'] == 'apply'

    def test_metric_snapshot_dict(self):
        snap = MetricSnapshot(name='latency_p95', value=123.0, unit='ms')
        assert snap.to_dict()['value'] == 123.0


# ======================================================================
# M5 - Intelligent Cache
# ======================================================================
class FakeClock:
    """Deterministic clock for cache tests."""

    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestCacheEntryAndTTLIndex:
    """Test cache entry dataclass and TTL index (V26.5)."""

    def test_entry_not_expired_without_ttl(self):
        entry = CacheEntry(key='k', value=1, expires_at=None)
        assert not entry.is_expired

    def test_entry_expired(self):
        clock = FakeClock()
        entry = CacheEntry(key='k', value=1,
                           expires_at=clock() - 10)
        assert entry.is_expired

    def test_ttl_index_add_get(self):
        idx = TTLIndex()
        idx.add('a', 100.0)
        assert idx.get('a') == 100.0
        assert idx.get('b') is None

    def test_ttl_index_due_keys(self):
        idx = TTLIndex()
        idx.add('a', 50.0)
        idx.add('b', 150.0)
        assert idx.due_keys(now=100.0) == ['a']
        assert idx.due_keys(now=200.0) == ['a', 'b']

    def test_ttl_index_remove_and_len(self):
        idx = TTLIndex()
        idx.add('a', 1.0)
        idx.add('b', 2.0)
        idx.remove('a')
        assert len(idx) == 1

    def test_ttl_index_add_none_removes(self):
        idx = TTLIndex()
        idx.add('a', 1.0)
        idx.add('a', None)
        assert len(idx) == 0


class TestIntelligentCacheBasics:
    """Test basic cache operations (V26.5)."""

    def test_set_and_get(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('k1', 'v1')
        assert cache.get('k1') == 'v1'

    def test_get_missing_returns_default(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        assert cache.get('missing') is None
        assert cache.get('missing', 'fallback') == 'fallback'

    def test_miss_counted(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.get('missing')
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

    def test_hit_counted(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('k', 'v')
        cache.get('k')
        assert cache.stats.hits == 1

    def test_overwrite_same_key(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('k', 1)
        cache.set('k', 2)
        assert cache.get('k') == 2
        assert len(cache) == 1

    def test_delete(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('k', 'v')
        assert cache.delete('k')
        assert not cache.delete('k')
        assert 'k' not in cache

    def test_exists(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('k', 'v')
        assert cache.exists('k')
        assert not cache.exists('nope')

    def test_clear(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        for i in range(5):
            cache.set(f'k{i}', i)
        assert cache.clear() == 5
        assert len(cache) == 0

    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError):
            IntelligentCache(max_size=0)

    def test_invalid_ttl_raises(self):
        with pytest.raises(ValueError):
            IntelligentCache(ttl_seconds=0)


class TestCacheTTL:
    """Test TTL expiry (V26.5)."""

    def test_entry_expires_after_ttl(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, ttl_seconds=10, clock=clock)
        cache.set('k', 'v')
        assert cache.get('k') == 'v'
        clock.advance(11)
        assert cache.get('k') is None

    def test_custom_ttl_per_entry(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, ttl_seconds=100, clock=clock)
        cache.set('short', 'v', ttl=5)
        clock.advance(6)
        assert cache.get('short') is None
        assert cache.stats.expirations == 1

    def test_no_ttl_entry_never_expires(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, ttl_seconds=10, clock=clock)
        cache.set('k', 'v', ttl=10 ** 9)
        clock.advance(1000)
        assert cache.get('k') == 'v'

    def test_evict_expired(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        cache.set('b', 2, ttl=1000)
        clock.advance(11)
        removed = cache.evict_expired()
        assert removed == ['a']
        assert len(cache) == 1

    def test_stats_track_expiration_as_miss(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, ttl_seconds=5, clock=clock)
        cache.set('k', 'v')
        clock.advance(6)
        cache.get('k')
        assert cache.stats.expirations == 1
        assert cache.stats.misses == 1


class TestCacheLRU:
    """Test LRU eviction (V26.5)."""

    def test_eviction_when_full(self):
        cache = IntelligentCache(max_size=2, adaptive_capacity=False,
                                 clock=FakeClock())
        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)  # evicts 'a'
        assert len(cache) == 2
        assert 'a' not in cache
        assert cache.get('c') == 3
        assert cache.stats.evictions == 1

    def test_get_refreshes_recency(self):
        cache = IntelligentCache(max_size=2, adaptive_capacity=False,
                                 clock=FakeClock())
        cache.set('a', 1)
        cache.set('b', 2)
        cache.get('a')  # refresh 'a'
        cache.set('c', 3)  # now 'b' is LRU
        assert 'a' in cache
        assert 'b' not in cache

    def test_eviction_order_multiple(self):
        cache = IntelligentCache(max_size=2, adaptive_capacity=False,
                                 clock=FakeClock())
        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)
        cache.set('d', 4)
        assert cache.stats.evictions == 2
        assert 'c' in cache and 'd' in cache


class TestCacheAdaptiveCapacity:
    """Test adaptive capacity based on hit rate (V26.5)."""

    def test_no_adjustment_below_interval(self):
        cache = IntelligentCache(max_size=100, adjustment_interval=50,
                                 adaptive_capacity=True, clock=FakeClock())
        for i in range(10):
            cache.set(f'k{i}', i)
            cache.get(f'k{i}')
        assert cache.stats.capacity_adjustments == 0

    def test_grow_on_high_hit_rate(self):
        cache = IntelligentCache(max_size=100, adjustment_interval=20,
                                 grow_threshold=0.8, grow_factor=1.5,
                                 clock=FakeClock())
        for i in range(10):
            cache.set(f'k{i}', i)
        for _ in range(2):  # 20 lookups, all hits -> exactly 1 adjustment
            for i in range(10):
                cache.get(f'k{i}')
        assert cache.max_size == 150
        assert cache.stats.capacity_adjustments == 1

    def test_shrink_on_low_hit_rate(self):
        cache = IntelligentCache(max_size=100, adjustment_interval=20,
                                 shrink_threshold=0.5, shrink_factor=0.5,
                                 min_size=10, clock=FakeClock())
        for i in range(20):
            cache.set(f'k{i}', i)  # 20 sets
        for i in range(20):
            cache.get(f'miss-{i}')  # 20 misses -> exactly 1 adjustment
        assert cache.max_size == 50
        assert cache.stats.capacity_adjustments == 1

    def test_shrink_respects_min_size(self):
        cache = IntelligentCache(max_size=100, adjustment_interval=10,
                                 shrink_threshold=0.9, shrink_factor=0.5,
                                 min_size=90, clock=FakeClock())
        for i in range(20):
            cache.get(f'miss-{i}')
        assert cache.max_size == 90

    def test_never_exceeds_max_allowed(self):
        cache = IntelligentCache(max_size=8000, adjustment_interval=10,
                                 grow_threshold=0.5, grow_factor=2.0,
                                 max_allowed_size=10000, clock=FakeClock())
        for i in range(20):
            cache.set(f'k{i}', i)
            cache.get(f'k{i}')
        assert cache.max_size <= 10000

    def test_force_adjust_capacity(self):
        cache = IntelligentCache(max_size=100, adaptive_capacity=True,
                                 clock=FakeClock())
        result = cache.force_adjust_capacity(hit_rate=0.9)
        assert result['adjusted']
        assert result['new_size'] == 150

    def test_force_adjust_shrink(self):
        cache = IntelligentCache(max_size=100, adaptive_capacity=True,
                                 shrink_threshold=0.5, shrink_factor=0.5,
                                 min_size=10, clock=FakeClock())
        result = cache.force_adjust_capacity(hit_rate=0.2)
        assert result['new_size'] == 50

    def test_adaptive_disabled(self):
        cache = IntelligentCache(max_size=100, adaptive_capacity=False,
                                 adjustment_interval=1, clock=FakeClock())
        for i in range(20):
            cache.set(f'k{i}', i)
            cache.get(f'k{i}')
        assert cache.stats.capacity_adjustments == 0


class TestCachePrefetch:
    """Test prefetch hooks (V26.5)."""

    def test_prefetch_with_dict_loader(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.register_prefetch_hook(lambda keys: {k: f'v-{k}' for k in keys})
        stored = cache.prefetch(['a', 'b'])
        assert stored == 2
        assert cache.get('a') == 'v-a'

    def test_prefetch_with_list_loader(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.register_prefetch_hook(lambda keys: [f'v-{k}' for k in keys])
        assert cache.prefetch(['x', 'y']) == 2
        assert cache.get('y') == 'v-y'

    def test_prefetch_warm_get_is_hit(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.register_prefetch_hook(lambda keys: {k: 1 for k in keys})
        cache.prefetch(['warm'])
        cache.get('warm')
        assert cache.stats.hits == 1
        assert cache.stats.misses == 0

    def test_prefetch_empty_noop(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        assert cache.prefetch([]) == 0

    def test_prefetch_uses_loader_fallback(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock(),
                                 loader=lambda k: f'loaded-{k}')
        assert cache.prefetch(['a']) == 1
        assert cache.get('a') == 'loaded-a'

    def test_prefetch_loader_failure_stores_nothing(self):
        def bad_loader(keys):
            raise RuntimeError('nope')

        cache = IntelligentCache(max_size=10, clock=FakeClock(),
                                 loader=bad_loader)
        assert cache.prefetch(['a']) == 0

    def test_prefetch_counts(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.register_prefetch_hook(lambda keys: {k: 1 for k in keys})
        cache.prefetch(['a', 'b', 'c'])
        assert cache.stats.prefetches == 3


class TestCacheInvalidation:
    """Test invalidation by key and prefix (V26.5)."""

    def test_invalidate_single(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('user:1', 'a')
        cache.set('user:2', 'b')
        assert cache.invalidate('user:1')
        assert 'user:1' not in cache
        assert 'user:2' in cache

    def test_invalidate_missing_returns_false(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        assert not cache.invalidate('ghost')

    def test_invalidate_prefix(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('user:1', 1)
        cache.set('user:2', 2)
        cache.set('order:1', 3)
        removed = cache.invalidate_prefix('user:')
        assert removed == 2
        assert 'user:1' not in cache and 'user:2' not in cache
        assert 'order:1' in cache

    def test_invalidate_prefix_no_match(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('a', 1)
        assert cache.invalidate_prefix('zzz') == 0

    def test_invalidate_prefix_stats(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('p:1', 1)
        cache.set('p:2', 2)
        cache.invalidate_prefix('p:')
        assert cache.stats.invalidations == 2

    def test_keys_with_prefix(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('user:1', 1)
        cache.set('order:1', 2)
        assert cache.keys(prefix='user:') == ['user:1']

    def test_invalidation_makes_get_miss(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('k', 'v')
        cache.invalidate('k')
        cache.get('k')
        assert cache.stats.misses == 1


class TestCacheStats:
    """Test statistics (V26.5)."""

    def test_hit_rate(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('a', 1)
        cache.get('a')
        cache.get('a')
        cache.get('miss')
        assert cache.stats.hit_rate == pytest.approx(2 / 3)

    def test_hit_rate_zero_lookups(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        assert cache.stats.hit_rate == 0.0

    def test_stats_dict(self):
        cache = IntelligentCache(max_size=10, name='unit', clock=FakeClock())
        cache.set('a', 1)
        cache.get('a')
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['sets'] == 1
        assert stats['name'] == 'unit'
        assert stats['size'] == 1
        assert stats['max_size'] == 10

    def test_reset_stats(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock())
        cache.set('a', 1)
        cache.get('a')
        cache.reset_stats()
        assert cache.get_stats()['hits'] == 0
        assert len(cache) == 1  # entries kept

    def test_cache_stats_dataclass(self):
        stats = CacheStats(hits=3, misses=1)
        assert stats.total_lookups == 4
        assert stats.hit_rate == pytest.approx(0.75)
        assert stats.to_dict()['evictions'] == 0


class TestCacheLoader:
    """Test load-through behaviour (V26.5)."""

    def test_get_with_loader_populates(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, clock=clock,
                                 loader=lambda k: f'loaded-{k}')
        assert cache.get('x') == 'loaded-x'
        assert cache.get('x') == 'loaded-x'  # now cached
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1

    def test_loader_exception_returns_default(self):
        def bad_loader(key):
            raise RuntimeError('db down')

        cache = IntelligentCache(max_size=10, clock=FakeClock(),
                                 loader=bad_loader)
        assert cache.get('x', 'default') == 'default'

    def test_loader_none_result_not_stored(self):
        cache = IntelligentCache(max_size=10, clock=FakeClock(),
                                 loader=lambda k: None)
        cache.get('x')
        assert len(cache) == 0


class TestCacheThreadSafety:
    """Test basic thread-safety of cache operations (V26.5)."""

    def test_concurrent_sets_and_gets(self):
        cache = IntelligentCache(max_size=1000, adaptive_capacity=False,
                                 clock=FakeClock())
        errors = []

        def worker(base):
            try:
                for i in range(200):
                    cache.set(f'{base}:{i}', i)
                    cache.get(f'{base}:{i}')
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,))
                   for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(cache) == 800


# ======================================================================
# Integration - V26 modules working together
# ======================================================================
class TestV26Integration:
    """Cross-module integration tests (V26)."""

    def test_learning_engine_feeds_adaptive_threshold(self):
        # Learn the best action (quality score: higher is better), then feed
        # the learned rewards into a dynamic threshold.
        engine = SelfLearningEngine(actions=['fast', 'slow'], epsilon=0.0,
                                    min_experiences=4, rng=random.Random(5))
        for _ in range(3):
            engine.record_experience('q', 'fast', 10.0, 'good')
        engine.record_experience('q', 'slow', 2.0, 'bad')
        engine.learn()
        best = engine.select_action('q')
        assert best == 'fast'

        # Scores cluster at 10; a much lower new score dips below the
        # percentile floor -> 'below' gate flags the regression.
        th = DynamicThreshold('quality', percentile_value=50, min_samples=2,
                              direction='below')
        for e in engine.buffer.all():
            th.observe(e.reward)
        assert th.evaluate(1.0).breached
        assert not th.evaluate(10.0).breached

    def test_cache_stats_feed_dynamic_threshold(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=100, clock=clock)
        cache.register_prefetch_hook(lambda keys: {k: k for k in keys})
        cache.prefetch([f'k{i}' for i in range(10)])
        hit_rates = []
        for i in range(10):
            cache.get(f'k{i}')  # hits
            hit_rates.append(cache.stats.hit_rate)
        th = DynamicThreshold('hit_rate', percentile_value=50, min_samples=3,
                              direction='above')
        for hr in hit_rates:
            th.observe(hr)
        # hit_rate rises monotonically toward 1.0; final values sit at the
        # top of the observed window, so nothing breaches an 'above' gate.
        assert not th.evaluate(hit_rates[-1]).breached
        assert th.evaluate(2.0).breached  # impossible spike is flagged

    def test_cooldown_gates_improvement_loop_reapply(self):
        applied = {'n': 0}
        cc = CooldownController(cooldown_seconds=3600)
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        improved = _make_metrics(latency_p95=100.0, error_rate=0.1,
                                 cache_hit_rate=99.0)

        def measure():
            # alternate: baseline (findings) then improved (no findings)
            return improved if applied['n'] else baseline

        loop = ImprovementLoop(
            measure_fn=measure,
            config={'batch_size': 100, 'cache_size': 1000, 'retry_count': 3},
            validator=SandboxValidator(simulate=lambda c, p: 0.5,
                                       min_expected_improvement=0.1))
        t0 = datetime.utcnow()
        for _ in range(3):
            result = loop.run_iteration(1)
            if result.status == 'no_change':
                break
            if result.status == 'improved' and cc.try_change('batch_size', now=t0):
                applied['n'] += 1
            else:
                break
        assert applied['n'] == 1
        # last audit entry belongs to the final (no_change) iteration
        assert loop.audit_log[-1].step == 'analyze'

    def test_improvement_loop_with_intelligent_cache(self):
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, clock=clock, name='loop_cache')
        baseline = _make_metrics(latency_p95=300.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        improved = _make_metrics(latency_p95=100.0, error_rate=0.1,
                                 cache_hit_rate=99.0)
        calls = {'n': 0}

        def measure():
            calls['n'] += 1
            cache.set('probe', calls['n'])
            return improved if calls['n'] > 1 else baseline

        loop = ImprovementLoop(
            measure_fn=measure,
            config={'batch_size': 100, 'cache_size': 1000, 'retry_count': 3},
            validator=SandboxValidator(simulate=lambda c, p: 0.5,
                                       min_expected_improvement=0.1))
        result = loop.run_iteration(1)
        assert result.status == 'improved'
        assert cache.exists('probe')
        assert cache.get('probe') == 2

    def test_policy_snapshot_into_cache_style_store(self):
        engine = SelfLearningEngine(actions=['a1', 'a2'], epsilon=0.0,
                                    min_experiences=2, rng=random.Random(3))
        engine.record_experience('s', 'a1', 1.0, 'good')
        engine.record_experience('s', 'a2', 0.5, 'neutral')
        engine.learn()
        snapshot = engine.policy.snapshot()
        restored = EpsilonGreedyPolicy.from_snapshot(snapshot)
        assert restored.expected_reward('s', 'a1') == \
            pytest.approx(engine.policy.expected_reward('s', 'a1'))

    def test_adaptive_config_with_dynamic_threshold_monitor(self):
        cfg = AdaptiveConfig(initial_batch_size=100, initial_timeout=30.0)
        th = DynamicThreshold('latency', percentile_value=95, min_samples=10)
        for _ in range(20):
            cfg.record_latency(10.0)
            th.observe(10.0)
        cfg.adjust()
        assert cfg.batch_size == 120  # headroom
        assert not th.evaluate(10.0).breached

    def test_full_v26_pipeline(self):
        """End-to-end: learn -> select -> cache -> improve."""
        # 1. learn
        engine = SelfLearningEngine(actions=['cache_first', 'direct'],
                                    epsilon=0.0, min_experiences=4,
                                    rng=random.Random(11))
        for _ in range(3):
            engine.record_experience('fetch', 'cache_first', 1.0, 'good')
        engine.record_experience('fetch', 'direct', 0.2, 'bad')
        report = engine.learn()
        assert report.accepted
        # 2. select
        assert engine.select_action('fetch') == 'cache_first'
        # 3. cache the chosen strategy
        clock = FakeClock()
        cache = IntelligentCache(max_size=10, ttl_seconds=100, clock=clock)
        cache.set('strategy:fetch', 'cache_first')
        # 4. improve: healthy metrics -> no change
        loop = ImprovementLoop(
            measure_fn=lambda: _make_metrics(latency_p95=50.0, error_rate=0.0,
                                             cache_hit_rate=99.0),
            config={'batch_size': 100, 'cache_size': 1000, 'retry_count': 3})
        summary = loop.run()
        assert summary['no_change'] >= 1
        assert loop.get_config()['batch_size'] == 100
        # cache entry still valid
        assert cache.get('strategy:fetch') == 'cache_first'
