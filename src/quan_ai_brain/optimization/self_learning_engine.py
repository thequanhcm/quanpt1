"""
Self-Learning Engine Module (V26.2)

This module provides self-learning capabilities based on accumulated
experience, including:
- Experience buffer (bounded storage of state/action/reward/outcome records)
- Pattern extraction (frequency of state -> action -> good outcome)
- Policy updates via a simple epsilon-greedy bandit
- Regression check before applying a new policy (mean score before/after
  on a replay of past experiences)
- Policy rollback to the previous version

All behaviour is deterministic, stdlib-only and fully in-memory (simulated).
No network access, no external ML frameworks, no production side effects.

Version: V26.2
Author: QUAN AI BRAIN Team
"""

import logging
import random
import statistics
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """A single observed experience: state -> action -> reward/outcome."""

    state: str
    action: str
    reward: float
    outcome: str = "neutral"  # e.g. 'good', 'bad', 'neutral'
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> Tuple[str, str]:
        return (self.state, self.action)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'state': self.state,
            'action': self.action,
            'reward': self.reward,
            'outcome': self.outcome,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
        }


class ExperienceBuffer:
    """Bounded FIFO buffer of experiences (oldest evicted when full)."""

    def __init__(self, max_size: int = 10000):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._experiences: deque = deque(maxlen=max_size)

    def add(self, experience: Experience) -> Experience:
        self._experiences.append(experience)
        return experience

    def add_experience(self, state: str, action: str, reward: float,
                       outcome: str = "neutral",
                       metadata: Optional[Dict[str, Any]] = None) -> Experience:
        return self.add(Experience(
            state=state,
            action=action,
            reward=reward,
            outcome=outcome,
            metadata=metadata or {},
        ))

    def all(self) -> List[Experience]:
        return list(self._experiences)

    def recent(self, n: int = 10) -> List[Experience]:
        if n <= 0:
            return []
        items = list(self._experiences)
        return items[-n:]

    def sample(self, n: int = 10) -> List[Experience]:
        items = list(self._experiences)
        if n >= len(items):
            return items
        return random.sample(items, n)

    def filter(self, state: Optional[str] = None, action: Optional[str] = None,
               outcome: Optional[str] = None,
               min_reward: Optional[float] = None) -> List[Experience]:
        result = []
        for e in self._experiences:
            if state is not None and e.state != state:
                continue
            if action is not None and e.action != action:
                continue
            if outcome is not None and e.outcome != outcome:
                continue
            if min_reward is not None and e.reward < min_reward:
                continue
            result.append(e)
        return result

    @property
    def size(self) -> int:
        return len(self._experiences)

    @property
    def is_empty(self) -> bool:
        return len(self._experiences) == 0

    def clear(self) -> None:
        self._experiences.clear()

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._experiences]


@dataclass
class LearnedPattern:
    """A learned (state -> action) pattern with frequency and success stats."""

    state: str
    action: str
    frequency: int
    good_count: int
    success_rate: float
    avg_reward: float
    total_in_state: int

    @property
    def confidence(self) -> float:
        if self.total_in_state <= 0:
            return 0.0
        return self.frequency / self.total_in_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            'state': self.state,
            'action': self.action,
            'frequency': self.frequency,
            'good_count': self.good_count,
            'success_rate': self.success_rate,
            'avg_reward': self.avg_reward,
            'total_in_state': self.total_in_state,
            'confidence': self.confidence,
        }


class PatternExtractor:
    """Extracts (state -> action -> good outcome) patterns from a buffer."""

    def __init__(self, good_outcomes: Tuple[str, ...] = ('good', 'success'),
                 good_reward_threshold: Optional[float] = None):
        self.good_outcomes = tuple(good_outcomes)
        self.good_reward_threshold = good_reward_threshold

    def _is_good(self, experience: Experience) -> bool:
        if experience.outcome in self.good_outcomes:
            return True
        if self.good_reward_threshold is not None and \
                experience.reward >= self.good_reward_threshold:
            return True
        return False

    def extract(self, buffer: ExperienceBuffer,
                min_frequency: int = 1) -> List[LearnedPattern]:
        totals: Counter = Counter()
        good: Counter = Counter()
        rewards: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        state_totals: Counter = Counter()

        for e in buffer.all():
            key = e.key
            totals[key] += 1
            state_totals[e.state] += 1
            rewards[key].append(e.reward)
            if self._is_good(e):
                good[key] += 1

        patterns: List[LearnedPattern] = []
        for (state, action), frequency in totals.items():
            if frequency < min_frequency:
                continue
            patterns.append(LearnedPattern(
                state=state,
                action=action,
                frequency=frequency,
                good_count=good[(state, action)],
                success_rate=good[(state, action)] / frequency,
                avg_reward=statistics.mean(rewards[(state, action)]),
                total_in_state=state_totals[state],
            ))

        patterns.sort(key=lambda p: (-p.frequency, p.state, p.action))
        return patterns


class EpsilonGreedyPolicy:
    """Simple epsilon-greedy bandit policy over (state, action) pairs.

    Values are incremental means of observed rewards. Unknown pairs fall
    back to ``default_value``. Selection is deterministic under epsilon=0.
    """

    def __init__(self, actions: Optional[List[str]] = None, epsilon: float = 0.1,
                 default_value: float = 0.0,
                 rng: Optional[random.Random] = None):
        self.actions: List[str] = list(actions) if actions else []
        self.epsilon = float(epsilon)
        self.default_value = float(default_value)
        self._rng = rng if rng is not None else random.Random()
        self._values: Dict[Tuple[str, str], float] = {}
        self._counts: Dict[Tuple[str, str], int] = {}

    def select_action(self, state: str,
                      available_actions: Optional[List[str]] = None) -> Optional[str]:
        actions = list(available_actions) if available_actions else self.actions
        if not actions:
            return None
        if self.epsilon > 0 and self._rng.random() < self.epsilon:
            return self._rng.choice(actions)
        return self.best_action(state, actions)

    def best_action(self, state: str,
                    available_actions: Optional[List[str]] = None) -> Optional[str]:
        actions = list(available_actions) if available_actions else self.actions
        if not actions:
            return None
        return max(actions, key=lambda a: self.expected_reward(state, a))

    def value(self, state: str, action: str) -> Optional[float]:
        return self._values.get((state, action))

    def expected_reward(self, state: str, action: str) -> float:
        value = self._values.get((state, action))
        return self.default_value if value is None else value

    def update(self, state: str, action: str, reward: float) -> float:
        key = (state, action)
        count = self._counts.get(key, 0)
        current = self._values.get(key, 0.0)
        new_count = count + 1
        new_value = current + (reward - current) / new_count
        self._counts[key] = new_count
        self._values[key] = new_value
        return new_value

    def count(self, state: str, action: str) -> int:
        return self._counts.get((state, action), 0)

    def known_pairs(self) -> List[Tuple[str, str]]:
        return sorted(self._values.keys())

    def clone(self) -> "EpsilonGreedyPolicy":
        clone = EpsilonGreedyPolicy(
            actions=list(self.actions),
            epsilon=self.epsilon,
            default_value=self.default_value,
            rng=self._rng,
        )
        clone._values = dict(self._values)
        clone._counts = dict(self._counts)
        return clone

    def snapshot(self) -> Dict[str, Any]:
        return {
            'actions': list(self.actions),
            'epsilon': self.epsilon,
            'default_value': self.default_value,
            'values': {f"{s}|{a}": v for (s, a), v in self._values.items()},
            'counts': {f"{s}|{a}": c for (s, a), c in self._counts.items()},
        }

    @classmethod
    def from_snapshot(cls, data: Dict[str, Any],
                      rng: Optional[random.Random] = None) -> "EpsilonGreedyPolicy":
        policy = cls(
            actions=list(data.get('actions', [])),
            epsilon=float(data.get('epsilon', 0.1)),
            default_value=float(data.get('default_value', 0.0)),
            rng=rng,
        )
        for key, value in data.get('values', {}).items():
            state, action = key.split('|', 1)
            policy._values[(state, action)] = float(value)
        for key, count in data.get('counts', {}).items():
            state, action = key.split('|', 1)
            policy._counts[(state, action)] = int(count)
        return policy

    def to_dict(self) -> Dict[str, Any]:
        return self.snapshot()


@dataclass
class PolicyVersion:
    """A versioned snapshot of a policy."""

    version_id: str
    policy_snapshot: Dict[str, Any]
    avg_score: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    experiences_seen: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version_id': self.version_id,
            'avg_score': self.avg_score,
            'created_at': self.created_at.isoformat(),
            'experiences_seen': self.experiences_seen,
        }


@dataclass
class RegressionReport:
    """Result of the regression check performed before applying a policy."""

    accepted: bool
    old_score: float
    new_score: float
    improvement: float
    min_improvement: float
    replay_size: int
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'accepted': self.accepted,
            'old_score': self.old_score,
            'new_score': self.new_score,
            'improvement': self.improvement,
            'min_improvement': self.min_improvement,
            'replay_size': self.replay_size,
            'reason': self.reason,
        }


class SelfLearningEngine:
    """Self-learning engine: buffer -> patterns -> bandit policy -> guarded apply.

    Flow:
    1. ``record_experience`` accumulates experience in the buffer (the active
       policy is NOT updated on record - only on accepted learn cycles).
    2. ``learn`` trains a candidate policy on the full buffer, runs a
       regression check (mean expected score before vs after on replay) and
       only applies the candidate when it does not regress.
    3. ``rollback_policy`` restores the previous applied policy version.
    """

    def __init__(self, actions: Optional[List[str]] = None, epsilon: float = 0.1,
                 min_experiences: int = 10, min_improvement: float = 0.0,
                 max_buffer_size: int = 10000,
                 rng: Optional[random.Random] = None,
                 good_outcomes: Tuple[str, ...] = ('good', 'success')):
        self.buffer = ExperienceBuffer(max_size=max_buffer_size)
        self.pattern_extractor = PatternExtractor(good_outcomes=good_outcomes)
        self.policy = EpsilonGreedyPolicy(
            actions=actions, epsilon=epsilon,
            rng=rng if rng is not None else random.Random(),
        )
        self.min_experiences = int(min_experiences)
        self.min_improvement = float(min_improvement)
        self._version_stack: List[PolicyVersion] = [
            PolicyVersion(
                version_id="v0",
                policy_snapshot=self.policy.snapshot(),
                avg_score=0.0,
                experiences_seen=0,
            )
        ]
        self.learned_patterns: List[LearnedPattern] = []
        self.learn_cycles = 0
        self.accepted_updates = 0
        self.rejected_updates = 0
        self.rollbacks = 0

    # ------------------------------------------------------------------
    # Experience recording
    # ------------------------------------------------------------------
    def record_experience(self, state: str, action: str, reward: float,
                          outcome: str = "neutral",
                          metadata: Optional[Dict[str, Any]] = None) -> Experience:
        return self.buffer.add_experience(
            state=state, action=action, reward=reward,
            outcome=outcome, metadata=metadata,
        )

    def extract_patterns(self, min_frequency: int = 2,
                         min_success_rate: float = 0.0) -> List[LearnedPattern]:
        patterns = self.pattern_extractor.extract(
            self.buffer, min_frequency=min_frequency)
        if min_success_rate > 0.0:
            patterns = [p for p in patterns if p.success_rate >= min_success_rate]
        return patterns

    # ------------------------------------------------------------------
    # Policy proposal / regression / learning
    # ------------------------------------------------------------------
    def propose_policy(self) -> EpsilonGreedyPolicy:
        """Train a candidate policy from scratch on the whole buffer."""
        candidate = self.policy.clone()
        # Reset learned values so the candidate is trained purely on data.
        candidate._values = {}
        candidate._counts = {}
        for experience in self.buffer.all():
            candidate.update(experience.state, experience.action, experience.reward)
        return candidate

    def _evaluate(self, policy: EpsilonGreedyPolicy,
                  experiences: List[Experience]) -> float:
        if not experiences:
            return 0.0
        return statistics.mean(
            policy.expected_reward(e.state, e.action) for e in experiences)

    def regression_check(self, candidate: EpsilonGreedyPolicy,
                         replay: Optional[List[Experience]] = None) -> RegressionReport:
        """Compare candidate vs current policy on a replay of experiences.

        The replay score of a policy is the mean of its expected reward for
        the (state, action) pairs actually observed in the replay data.
        """
        data = replay if replay is not None else self.buffer.all()
        old_score = self._evaluate(self.policy, data)
        new_score = self._evaluate(candidate, data)
        improvement = new_score - old_score

        if len(data) < self.min_experiences:
            return RegressionReport(
                accepted=False,
                old_score=old_score,
                new_score=new_score,
                improvement=improvement,
                min_improvement=self.min_improvement,
                replay_size=len(data),
                reason='insufficient_replay_data',
            )

        if improvement >= self.min_improvement:
            reason = 'improvement_above_threshold' if improvement > 0 \
                else 'no_regression'
            return RegressionReport(
                accepted=True,
                old_score=old_score,
                new_score=new_score,
                improvement=improvement,
                min_improvement=self.min_improvement,
                replay_size=len(data),
                reason=reason,
            )

        return RegressionReport(
            accepted=False,
            old_score=old_score,
            new_score=new_score,
            improvement=improvement,
            min_improvement=self.min_improvement,
            replay_size=len(data),
            reason='regression_detected',
        )

    def learn(self) -> Optional[RegressionReport]:
        """Full learning cycle: patterns -> candidate -> regression -> apply."""
        if self.buffer.size < self.min_experiences:
            logger.info(
                "Learn skipped: %d experiences < min %d",
                self.buffer.size, self.min_experiences,
            )
            return None

        self.learn_cycles += 1
        self.learned_patterns = self.extract_patterns(min_frequency=1)
        candidate = self.propose_policy()
        report = self.regression_check(candidate)

        if report.accepted:
            version = PolicyVersion(
                version_id=f"v{len(self._version_stack)}",
                policy_snapshot=candidate.snapshot(),
                avg_score=report.new_score,
                experiences_seen=report.replay_size,
            )
            self._version_stack.append(version)
            self.policy = candidate
            self.accepted_updates += 1
            logger.info(
                "Policy %s applied (score %.4f -> %.4f)",
                version.version_id, report.old_score, report.new_score,
            )
        else:
            self.rejected_updates += 1
            logger.info(
                "Policy update rejected (%s): %.4f -> %.4f",
                report.reason, report.old_score, report.new_score,
            )
        return report

    # ------------------------------------------------------------------
    # Versioning / rollback
    # ------------------------------------------------------------------
    def rollback_policy(self) -> Optional[PolicyVersion]:
        """Revert to the previously applied policy version.

        Returns the removed (current) version, or None when there is nothing
        to roll back to (only the initial version exists).
        """
        if len(self._version_stack) <= 1:
            return None
        removed = self._version_stack.pop()
        restored = self._version_stack[-1]
        self.policy = EpsilonGreedyPolicy.from_snapshot(
            restored.policy_snapshot, rng=self.policy._rng)
        self.rollbacks += 1
        logger.info("Rolled back policy from %s to %s",
                    removed.version_id, restored.version_id)
        return removed

    @property
    def current_version(self) -> PolicyVersion:
        return self._version_stack[-1]

    def improvement_trend(self) -> List[float]:
        return [version.avg_score for version in self._version_stack]

    # ------------------------------------------------------------------
    # Action selection / stats
    # ------------------------------------------------------------------
    def select_action(self, state: str,
                      available_actions: Optional[List[str]] = None) -> Optional[str]:
        return self.policy.select_action(state, available_actions)

    def get_stats(self) -> Dict[str, Any]:
        return {
            'buffer_size': self.buffer.size,
            'learn_cycles': self.learn_cycles,
            'accepted_updates': self.accepted_updates,
            'rejected_updates': self.rejected_updates,
            'rollbacks': self.rollbacks,
            'current_version': self.current_version.version_id,
            'version_count': len(self._version_stack),
            'patterns_stored': len(self.learned_patterns),
            'epsilon': self.policy.epsilon,
            'actions': list(self.policy.actions),
            'min_experiences': self.min_experiences,
            'min_improvement': self.min_improvement,
        }
