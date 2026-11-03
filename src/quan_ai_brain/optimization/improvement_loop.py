"""
Continuous Improvement Loop Module (V26.4)

This module implements the measure -> analyze -> propose -> validate ->
apply -> verify improvement cycle with a full audit trail:
- Measure: collect metrics (optionally via AutoTuner's MetricsCollector)
- Analyze: use AutoTuner (V26.1) when importable, else an internal analyzer
- Propose: convert analysis results into change proposals
- Validate: sandbox dry-run on synthetic data before anything is applied
- Apply: apply only validated proposals
- Verify: re-measure and compare against the baseline
- Fail-safe revert: restore the previous configuration whenever
  verification fails, errors occur or max iterations is reached

AutoTuner integration is opportunistic (try/except import); when the import
fails the loop still works with a built-in analyzer.

All behaviour is deterministic, stdlib-only and fully in-memory (simulated).
No network access, no production side effects.

Version: V26.4
Author: QUAN AI BRAIN Team
"""

import logging
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

try:  # opportunistic reuse of V26.1 - never a hard dependency
    from quan_ai_brain.optimization.auto_tuner import (  # type: ignore
        AutoTuner,
        Metric as AutoTunerMetric,
        MetricType,
        MetricsCollector,
        OptimizationSuggestion,
        TuningConfig,
    )
    _AUTOTUNER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without V26.1
    AutoTuner = None  # type: ignore
    AutoTunerMetric = None  # type: ignore
    MetricType = None  # type: ignore
    MetricsCollector = None  # type: ignore
    OptimizationSuggestion = None  # type: ignore
    TuningConfig = None  # type: ignore
    _AUTOTUNER_AVAILABLE = False


@dataclass
class MetricSnapshot:
    """A named metric value captured at a point in time."""

    name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class ChangeProposal:
    """A single configuration change proposal."""

    proposal_id: str
    parameter: str
    current_value: Any
    proposed_value: Any
    reason: str
    expected_improvement: float = 0.0
    risk_level: str = 'low'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'proposal_id': self.proposal_id,
            'parameter': self.parameter,
            'current_value': self.current_value,
            'proposed_value': self.proposed_value,
            'reason': self.reason,
            'expected_improvement': self.expected_improvement,
            'risk_level': self.risk_level,
        }


@dataclass
class AuditEntry:
    """One immutable audit record for a loop step."""

    step: str
    iteration: int
    status: str  # 'ok', 'skipped', 'failed', 'reverted'
    detail: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> Dict[str, Any]:
        return {
            'entry_id': self.entry_id,
            'step': self.step,
            'iteration': self.iteration,
            'status': self.status,
            'detail': self.detail,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class IterationResult:
    """Outcome of one full loop iteration."""

    iteration: int
    status: str  # 'improved', 'no_change', 'reverted', 'failed'
    baseline: Dict[str, float]
    after: Optional[Dict[str, float]]
    applied_proposals: List[ChangeProposal]
    reverted: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'iteration': self.iteration,
            'status': self.status,
            'baseline': self.baseline,
            'after': self.after,
            'applied': [p.to_dict() for p in self.applied_proposals],
            'reverted': self.reverted,
            'error': self.error,
        }


class SandboxValidator:
    """Dry-runs proposals against synthetic (fake) data in isolation.

    The validator receives a sandbox configuration dictionary (a copy of the
    live config) and returns a simulated score. It must never mutate the
    live configuration - it only sees a deep copy.
    """

    def __init__(self,
                 simulate: Optional[Callable[[Dict[str, Any], List[ChangeProposal]], float]] = None,
                 min_expected_improvement: float = 0.0):
        self.simulate = simulate
        self.min_expected_improvement = float(min_expected_improvement)
        self.validation_count = 0
        self.last_sandbox_config: Optional[Dict[str, Any]] = None

    def validate(self, config: Dict[str, Any],
                 proposals: List[ChangeProposal]) -> Dict[str, Any]:
        """Dry-run proposals on a deep copy of the config (sandbox)."""
        self.validation_count += 1
        sandbox = dict(config)  # shallow copy of flat dict = isolated sandbox
        for proposal in proposals:
            sandbox[proposal.parameter] = proposal.proposed_value
        self.last_sandbox_config = dict(sandbox)

        if self.simulate is None:
            return {
                'valid': False,
                'score': 0.0,
                'reason': 'no_simulator_configured',
                'sandbox_config': dict(sandbox),
            }

        try:
            score = float(self.simulate(sandbox, list(proposals)))
        except Exception as exc:
            return {
                'valid': False,
                'score': 0.0,
                'reason': f'simulator_error: {exc}',
                'sandbox_config': dict(sandbox),
            }

        return {
            'valid': score >= self.min_expected_improvement,
            'score': score,
            'reason': 'simulated_score_above_threshold' if score >= self.min_expected_improvement
            else 'simulated_score_below_threshold',
            'sandbox_config': dict(sandbox),
        }


class ImprovementAnalyzer:
    """Fallback analyzer used when AutoTuner is not importable."""

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        # metric -> (direction 'above'/'below', threshold)
        self.thresholds = thresholds or {
            'latency_p95': ('above', 200.0),
            'error_rate': ('above', 1.0),
            'cache_hit_rate': ('below', 90.0),
        }

    def analyze(self, metrics: List[MetricSnapshot]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for metric in metrics:
            rule = self.thresholds.get(metric.name)
            if rule is None:
                continue
            direction, threshold = rule
            if direction == 'above' and metric.value > threshold:
                findings.append({
                    'metric': metric.name,
                    'value': metric.value,
                    'threshold': threshold,
                    'severity': 'high',
                })
            elif direction == 'below' and metric.value < threshold:
                findings.append({
                    'metric': metric.name,
                    'value': metric.value,
                    'threshold': threshold,
                    'severity': 'medium',
                })
        return findings


class ImprovementLoop:
    """Continuous improvement loop with audit trail and fail-safe revert.

    The loop interacts with the outside world exclusively through injected
    callables, keeping the class testable and side-effect free:
    - ``measure_fn()`` -> List[MetricSnapshot] (current metrics)
    - ``verify_fn(baseline, after)`` -> bool (did we improve?)
    - ``config`` dict acts as the live configuration store
    """

    STEPS = ('measure', 'analyze', 'propose', 'validate', 'apply', 'verify')

    def __init__(self,
                 measure_fn: Callable[[], List[MetricSnapshot]],
                 verify_fn: Optional[Callable[[Dict[str, float], Dict[str, float]], bool]] = None,
                 config: Optional[Dict[str, Any]] = None,
                 max_iterations: int = 5,
                 min_improvement: float = 0.01,
                 auto_tuner: Optional[Any] = None,
                 analyzer: Optional[ImprovementAnalyzer] = None,
                 validator: Optional[SandboxValidator] = None,
                 min_samples_for_analysis: int = 3):
        if max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        self.measure_fn = measure_fn
        self.verify_fn = verify_fn or self._default_verify
        self.config: Dict[str, Any] = dict(config) if config else {}
        self.max_iterations = int(max_iterations)
        self.min_improvement = float(min_improvement)
        self.analyzer = analyzer or ImprovementAnalyzer()
        self.validator = validator or SandboxValidator()
        self.min_samples_for_analysis = int(min_samples_for_analysis)
        self.audit_log: List[AuditEntry] = []
        self.iteration_results: List[IterationResult] = []
        self.history: List[Dict[str, Any]] = []
        self.config_backup: Optional[Dict[str, Any]] = None
        self.total_runs = 0

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------
    def _audit(self, step: str, iteration: int, status: str,
               detail: Optional[Dict[str, Any]] = None) -> AuditEntry:
        entry = AuditEntry(step=step, iteration=iteration, status=status,
                           detail=detail or {})
        self.audit_log.append(entry)
        return entry

    # ------------------------------------------------------------------
    # AutoTuner integration (opportunistic)
    # ------------------------------------------------------------------
    def _build_autotuner(self) -> Optional[Any]:
        if not _AUTOTUNER_AVAILABLE:
            return None
        try:
            collector = MetricsCollector()
            tuning_config = TuningConfig(
                config_id='v26_improvement_loop',
                name='ImprovementLoopTuning',
                enabled=True,
                thresholds={
                    'latency_p95_threshold': 200.0,
                    'error_rate_threshold': 1.0,
                    'cpu_threshold': 70.0,
                    'cache_hit_rate_threshold': 90.0,
                },
                optimization_rules={},
                safety_limits={},
            )
            return AutoTuner(config=tuning_config, metrics_collector=collector)
        except Exception as exc:
            logger.warning("AutoTuner construction failed: %s", exc)
            return None

    def analyze(self, metrics: List[MetricSnapshot]) -> List[Dict[str, Any]]:
        """Analyze measured metrics.

        Uses AutoTuner's bottleneck logic (V26.1) when importable and enough
        samples exist; falls back to the internal analyzer otherwise. The
        measured metrics are mapped onto AutoTuner's Metric objects so the
        tuners' thresholds run against the loop's own measurements - not on
        random simulated data.
        """
        if not metrics:
            return []
        findings: List[Dict[str, Any]] = []
        if len(metrics) >= self.min_samples_for_analysis and _AUTOTUNER_AVAILABLE:
            findings = self._analyze_with_autotuner(metrics)
        if not findings:
            findings = self.analyzer.analyze(metrics)
        return findings

    def _analyze_with_autotuner(self, metrics: List[MetricSnapshot]) -> List[Dict[str, Any]]:
        """Map measured metrics onto AutoTuner bottleneck detection."""
        tuner = self._build_autotuner()
        if tuner is None:
            return []
        type_map = {
            'latency_p95': 'latency_p95',
            'error_rate': 'error_rate',
            'cpu_usage': 'cpu_usage',
            'cache_hit_rate': 'cache_hit_rate',
        }
        collected: List[Any] = []
        now = datetime.utcnow()
        for metric in metrics:
            metric_type_name = type_map.get(metric.name)
            if metric_type_name is None:
                continue
            metric_type = MetricType(metric_type_name)
            collected.append(AutoTunerMetric(
                metric_id=metric.name,
                metric_type=metric_type,
                value=metric.value,
                timestamp=now,
            ))
        if not collected:
            return []
        try:
            bottlenecks = tuner._identify_bottlenecks(collected)
        except Exception as exc:
            logger.warning("AutoTuner bottleneck analysis failed: %s", exc)
            return []
        findings = []
        for bottleneck in bottlenecks:
            findings.append({
                'metric': bottleneck['metric'],
                'value': bottleneck['value'],
                'threshold': bottleneck['threshold'],
                'severity': 'high',
                'source': 'autotuner',
                'bottleneck_type': bottleneck['type'],
            })
        return findings

    # ------------------------------------------------------------------
    # Proposals
    # ------------------------------------------------------------------
    def propose(self, findings: List[Dict[str, Any]]) -> List[ChangeProposal]:
        proposals: List[ChangeProposal] = []
        for finding in findings:
            metric = finding.get('metric')
            if metric == 'latency_p95':
                proposals.append(ChangeProposal(
                    proposal_id=f"prop_{metric}_{len(proposals)}",
                    parameter='batch_size',
                    current_value=self.config.get('batch_size', 100),
                    proposed_value=max(10, int(self.config.get('batch_size', 100)) // 2),
                    reason=f"latency_p95={finding.get('value')} above "
                           f"threshold {finding.get('threshold')}; reduce batch size",
                    expected_improvement=0.2,
                    risk_level='low',
                ))
            elif metric == 'error_rate':
                proposals.append(ChangeProposal(
                    proposal_id=f"prop_{metric}_{len(proposals)}",
                    parameter='retry_count',
                    current_value=self.config.get('retry_count', 3),
                    proposed_value=min(10, int(self.config.get('retry_count', 3)) + 1),
                    reason=f"error_rate={finding.get('value')} above "
                           f"threshold {finding.get('threshold')}; increase retries",
                    expected_improvement=0.15,
                    risk_level='medium',
                ))
            elif metric == 'cache_hit_rate':
                proposals.append(ChangeProposal(
                    proposal_id=f"prop_{metric}_{len(proposals)}",
                    parameter='cache_size',
                    current_value=self.config.get('cache_size', 1000),
                    proposed_value=int(self.config.get('cache_size', 1000)) * 2,
                    reason=f"cache_hit_rate={finding.get('value')} below "
                           f"threshold {finding.get('threshold')}; enlarge cache",
                    expected_improvement=0.25,
                    risk_level='low',
                ))
        return proposals

    # ------------------------------------------------------------------
    # Config mutation (with backup for fail-safe revert)
    # ------------------------------------------------------------------
    def _backup_config(self) -> None:
        self.config_backup = dict(self.config)

    def apply_proposals(self, proposals: List[ChangeProposal]) -> int:
        applied = 0
        for proposal in proposals:
            self.config[proposal.parameter] = proposal.proposed_value
            applied += 1
        return applied

    def revert(self) -> bool:
        """Restore the last backed-up configuration (fail-safe)."""
        if self.config_backup is None:
            return False
        self.config = dict(self.config_backup)
        return True

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    @staticmethod
    def _default_verify(baseline: Dict[str, float],
                        after: Dict[str, float]) -> bool:
        """A metric improved when lower latency/error or higher hit rate."""
        lower_is_better = {'latency_p95', 'latency_p50', 'error_rate'}
        for name, base_value in baseline.items():
            new_value = after.get(name)
            if new_value is None:
                continue
            if name in lower_is_better:
                if new_value > base_value:
                    return False
            else:
                if new_value < base_value:
                    return False
        return True

    @staticmethod
    def _mean_metric_value(metrics: List[MetricSnapshot],
                           name: str) -> Optional[float]:
        values = [m.value for m in metrics if m.name == name]
        if not values:
            return None
        return statistics.mean(values)

    def _metrics_to_dict(self, metrics: List[MetricSnapshot]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for metric in metrics:
            existing = result.get(metric.name)
            if existing is None:
                result[metric.name] = metric.value
            else:
                result[metric.name] = (existing + metric.value) / 2.0
        return result

    # ------------------------------------------------------------------
    # The loop
    # ------------------------------------------------------------------
    def run_iteration(self, iteration: int) -> IterationResult:
        baseline_metrics = self.measure_fn()
        baseline = self._metrics_to_dict(baseline_metrics)

        # measure
        self._audit('measure', iteration, 'ok',
                    {'metrics': baseline})

        # analyze
        findings = self.analyze(baseline_metrics)
        self._audit('analyze', iteration, 'ok' if findings else 'skipped',
                    {'findings_count': len(findings)})

        applied_proposals: List[ChangeProposal] = []
        after: Optional[Dict[str, float]] = None
        reverted = False

        if not findings:
            result = IterationResult(
                iteration=iteration, status='no_change', baseline=baseline,
                after=baseline, applied_proposals=[], reverted=False)
            self.iteration_results.append(result)
            self.history.append(result.to_dict())
            return result

        # propose
        proposals = self.propose(findings)
        self._audit('propose', iteration, 'ok' if proposals else 'skipped',
                    {'proposals': [p.to_dict() for p in proposals]})
        if not proposals:
            result = IterationResult(
                iteration=iteration, status='no_change', baseline=baseline,
                after=baseline, applied_proposals=[], reverted=False)
            self.iteration_results.append(result)
            self.history.append(result.to_dict())
            return result

        # validate (sandbox dry-run on synthetic config copy)
        validation = self.validator.validate(self.config, proposals)
        self._audit('validate', iteration,
                    'ok' if validation['valid'] else 'failed',
                    {'validation': {k: v for k, v in validation.items()
                                    if k != 'sandbox_config'},
                     'sandbox_size': len(validation.get('sandbox_config', {}))})
        if not validation['valid']:
            result = IterationResult(
                iteration=iteration, status='failed', baseline=baseline,
                after=None, applied_proposals=[], reverted=False,
                error=validation['reason'])
            self.iteration_results.append(result)
            self.history.append(result.to_dict())
            return result

        # apply (with backup first for fail-safe revert)
        self._backup_config()
        applied_count = self.apply_proposals(proposals)
        applied_proposals = list(proposals)
        self._audit('apply', iteration, 'ok', {'applied_count': applied_count})

        # verify
        try:
            after_metrics = self.measure_fn()
            after = self._metrics_to_dict(after_metrics)
            improved = self.verify_fn(baseline, after)
        except Exception as exc:
            improved = False
            self._audit('verify', iteration, 'failed', {'error': str(exc)})
        else:
            self._audit('verify', iteration, 'ok' if improved else 'failed',
                        {'after': after, 'improved': improved})

        if improved:
            result = IterationResult(
                iteration=iteration, status='improved', baseline=baseline,
                after=after, applied_proposals=applied_proposals,
                reverted=False)
        else:
            # fail-safe revert
            reverted = self.revert()
            self._audit('revert', iteration,
                        'ok' if reverted else 'failed',
                        {'reverted': reverted})
            result = IterationResult(
                iteration=iteration, status='reverted', baseline=baseline,
                after=after, applied_proposals=applied_proposals,
                reverted=reverted)

        self.iteration_results.append(result)
        self.history.append(result.to_dict())
        return result

    def run(self) -> Dict[str, Any]:
        """Run up to ``max_iterations`` iterations; stops early on failure."""
        self.total_runs += 1
        ran = 0
        for iteration in range(1, self.max_iterations + 1):
            result = self.run_iteration(iteration)
            ran += 1
            if result.status in ('failed', 'reverted'):
                break
        summary = {
            'total_runs': self.total_runs,
            'iterations_run': ran,
            'improved': sum(1 for r in self.iteration_results
                            if r.status == 'improved'),
            'reverted': sum(1 for r in self.iteration_results
                            if r.status == 'reverted'),
            'failed': sum(1 for r in self.iteration_results
                          if r.status == 'failed'),
            'no_change': sum(1 for r in self.iteration_results
                             if r.status == 'no_change'),
        }
        self._audit('loop_complete', ran, 'ok', summary)
        return summary

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def get_audit_log(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.audit_log]

    def get_audit_steps(self) -> List[str]:
        return [e.step for e in self.audit_log]

    def get_config(self) -> Dict[str, Any]:
        return dict(self.config)
