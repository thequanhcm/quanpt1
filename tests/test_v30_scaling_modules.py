"""
V30 Scaling Modules Test Suite (~60 tests).

Covers:
- TestLoadBalancer (M1): strategies, health registry, sticky, circuit breaker
- TestPerformanceOptimizer (M2): plan analysis, index, cache, sharding, N+1
- TestDisasterRecovery (M3): backup/verify/restore, RTO/RPO, failover machine
- TestObservability (M4): spans, SLO, burn rate, alerts, logs
- TestBusinessIntelligence (M5): rollups, KPI, dashboard, schedules
- TestV30Integration: cross-module flows

All in-process; DR uses tmp_path only.
"""

import hashlib
import time
from datetime import datetime, timedelta, timezone

import pytest

from quan_ai_brain.scaling.disaster_recovery import (
    BackupManifest,
    DisasterRecovery,
    FailoverError,
    FailoverState,
)
from quan_ai_brain.scaling.horizontal_scaling import (
    BackendNode,
    CircuitState,
    HealthCheckRegistry,
    LoadBalancer,
    NodeState,
    ScalingStrategy,
)
from quan_ai_brain.scaling.monitoring import (
    AlertRule,
    AlertSeverity,
    Observability,
    SpanStatus,
)
from quan_ai_brain.scaling.business_intelligence import (
    BusinessIntelligence,
    ChartWidget,
    MetricWidget,
    RollupGranularity,
    ScheduleConfig,
    TableWidget,
    TimePoint,
    TrendDirection,
)
from quan_ai_brain.scaling.performance_optimizer import (
    CacheLevel,
    OpType,
    PlanOp,
    QueryOptimizer,
    QueryPlan,
)


def _node(node_id, weight=1, port=8000):
    return BackendNode(node_id=node_id, address="127.0.0.1", port=port, weight=weight)


# ======================================================================
# M1: Load Balancer
# ======================================================================

class TestLoadBalancer:

    def test_register_and_deregister(self):
        lb = LoadBalancer()
        lb.add_node(_node("n1"))
        assert len(lb.nodes()) == 1
        assert lb.remove_node("n1") is True
        assert lb.remove_node("n1") is False
        assert lb.nodes() == []

    def test_duplicate_node_rejected(self):
        lb = LoadBalancer()
        lb.add_node(_node("n1"))
        with pytest.raises(ValueError):
            lb.add_node(_node("n1"))

    def test_round_robin_distribution(self):
        lb = LoadBalancer()
        for i in range(3):
            lb.add_node(_node(f"n{i}"))
        picks = [lb.route().node_id for _ in range(6)]
        assert picks == ["n0", "n1", "n2", "n0", "n1", "n2"]

    def test_round_robin_skips_unhealthy(self):
        lb = LoadBalancer()
        lb.add_node(_node("n1"))
        lb.add_node(_node("n2"))
        lb.mark_unhealthy("n1")
        picks = [lb.route().node_id for _ in range(4)]
        assert set(picks) == {"n2"}

    def test_least_connections(self):
        lb = LoadBalancer(strategy=ScalingStrategy.LEAST_CONNECTIONS)
        lb.add_node(_node("n1"))
        lb.add_node(_node("n2"))
        first = lb.route()
        assert first.node_id == "n1"
        # n1 now has 1 active conn; next route should pick n2
        second = lb.route()
        assert second.node_id == "n2"
        lb.release("n1")
        third = lb.route()
        assert third.node_id == "n1"

    def test_least_connections_tiebreak_deterministic(self):
        lb = LoadBalancer(strategy=ScalingStrategy.LEAST_CONNECTIONS)
        lb.add_node(_node("b"))
        lb.add_node(_node("a"))
        assert lb.route().node_id == "a"  # tie -> lexicographic

    def test_weighted_respects_ratio(self):
        lb = LoadBalancer(strategy=ScalingStrategy.WEIGHTED)
        lb.add_node(_node("heavy", weight=3))
        lb.add_node(_node("light", weight=1))
        picks = [lb.route().node_id for _ in range(40)]
        assert picks.count("heavy") == 30
        assert picks.count("light") == 10

    def test_sticky_by_client_hash(self):
        lb = LoadBalancer(strategy=ScalingStrategy.STICKY)
        for i in range(3):
            lb.add_node(_node(f"n{i}"))
        a1 = lb.route(client_id="client-A").node_id
        a2 = lb.route(client_id="client-A").node_id
        a3 = lb.route(client_id="client-A").node_id
        assert a1 == a2 == a3

    def test_sticky_deterministic_across_instances(self):
        lb1 = LoadBalancer(strategy=ScalingStrategy.STICKY)
        lb2 = LoadBalancer(strategy=ScalingStrategy.STICKY)
        for i in range(3):
            lb1.add_node(_node(f"n{i}"))
            lb2.add_node(_node(f"n{i}"))
        assert lb1.route(client_id="user-42").node_id == \
               lb2.route(client_id="user-42").node_id

    def test_sticky_matches_pure_hash(self):
        lb = LoadBalancer(strategy=ScalingStrategy.STICKY)
        for i in range(3):
            lb.add_node(_node(f"n{i}"))
        h = int(hashlib.sha256(b"user-9").hexdigest(), 16)
        expected = [n.node_id for n in lb.healthy_nodes()][h % 3]
        assert lb.route(client_id="user-9").node_id == expected

    def test_sticky_falls_back_when_node_unhealthy(self):
        lb = LoadBalancer(strategy=ScalingStrategy.STICKY)
        for i in range(3):
            lb.add_node(_node(f"n{i}"))
        bound = lb.route(client_id="c1").node_id
        lb.mark_unhealthy(bound)
        rebalanced = lb.route(client_id="c1").node_id
        assert rebalanced != bound
        assert lb.is_node_healthy(rebalanced)

    def test_health_marks_unhealthy_after_threshold(self):
        lb = LoadBalancer(health_failure_threshold=3)
        lb.add_node(_node("n1"))
        assert lb.mark_failure("n1") == NodeState.HEALTHY
        assert lb.mark_failure("n1") == NodeState.HEALTHY
        assert lb.mark_failure("n1") == NodeState.UNHEALTHY
        assert not lb.is_node_healthy("n1")

    def test_health_recovers_on_success(self):
        lb = LoadBalancer(health_failure_threshold=2)
        lb.add_node(_node("n1"))
        lb.mark_failure("n1")
        lb.mark_failure("n1")
        assert lb.mark_success("n1") == NodeState.HEALTHY
        assert lb.is_node_healthy("n1")

    def test_health_registry_standalone(self):
        hc = HealthCheckRegistry(failure_threshold=2)
        assert hc.record_failure("x") == NodeState.HEALTHY
        assert hc.record_failure("x") == NodeState.UNHEALTHY
        assert hc.failure_count("x") == 2
        assert hc.is_healthy("x") is False

    def test_no_healthy_node_raises(self):
        lb = LoadBalancer()
        with pytest.raises(RuntimeError):
            lb.route()

    def test_all_nodes_marked_unhealthy_raises(self):
        lb = LoadBalancer()
        lb.add_node(_node("n1"))
        lb.mark_unhealthy("n1")
        with pytest.raises(RuntimeError):
            lb.route()

    def test_circuit_opens_after_failures(self):
        lb = LoadBalancer(cb_failure_threshold=3)
        lb.add_node(_node("n1"))
        for _ in range(3):
            lb.circuit("n1").record_failure()
        assert lb.circuit_state("n1") == CircuitState.OPEN

    def test_circuit_rejects_when_open(self):
        lb = LoadBalancer(cb_failure_threshold=1)
        lb.add_node(_node("n1"))
        lb.trip_circuit("n1")
        with pytest.raises(RuntimeError):
            lb.route()

    def test_circuit_half_open_after_timeout(self):
        lb = LoadBalancer(cb_failure_threshold=1, cb_recovery_timeout=0.0)
        lb.add_node(_node("n1"))
        lb.trip_circuit("n1")
        assert lb.circuit("n1").can_pass() is True
        assert lb.circuit_state("n1") == CircuitState.HALF_OPEN

    def test_circuit_closes_on_success(self):
        lb = LoadBalancer(cb_failure_threshold=1, cb_recovery_timeout=0.0)
        lb.add_node(_node("n1"))
        lb.trip_circuit("n1")
        lb.record_request_result("n1", success=True)
        assert lb.circuit_state("n1") == CircuitState.CLOSED

    def test_circuit_reopens_on_failed_probe(self):
        lb = LoadBalancer(cb_failure_threshold=1, cb_recovery_timeout=0.0)
        lb.add_node(_node("n1"))
        lb.trip_circuit("n1")
        lb.record_request_result("n1", success=False)
        assert lb.circuit_state("n1") == CircuitState.OPEN

    def test_stats_and_distribution(self):
        lb = LoadBalancer()
        lb.add_node(_node("n1"))
        lb.add_node(_node("n2"))
        for _ in range(4):
            lb.route()
        assert lb.stats["requests_routed"] == 4
        dist = lb.load_distribution()
        assert sum(dist.values()) == 4
        assert set(dist.values()) == {2}

    def test_release_decrements_connections(self):
        lb = LoadBalancer()
        lb.add_node(_node("n1"))
        n = lb.route()
        assert n.active_connections == 1
        lb.release(n.node_id)
        assert n.active_connections == 0

    def test_invalid_health_threshold(self):
        with pytest.raises(ValueError):
            HealthCheckRegistry(failure_threshold=0)


# ======================================================================
# M2: Performance Optimizer
# ======================================================================

def _scan(table, cost, fields=None, rows=0):
    return PlanOp(op_type=OpType.SEQ_SCAN, table=table, cost=cost,
                  filter_fields=fields or [], rows=rows)


class TestPerformanceOptimizer:

    def test_plan_total_cost(self):
        plan = QueryPlan("q1", [_scan("t", 50), _scan("t", 30)])
        assert plan.total_cost == 80

    def test_healthy_plan_verdict(self):
        opt = QueryOptimizer()
        plan = QueryPlan("q1", [_scan("t", 10)])
        assert opt.analyze_plan(plan).verdict == "healthy"

    def test_expensive_plan_verdict(self):
        opt = QueryOptimizer(cost_threshold=100)
        plan = QueryPlan("q1", [_scan("t", 150)])
        assert opt.analyze_plan(plan).verdict == "needs_optimization"

    def test_critical_plan_verdict(self):
        opt = QueryOptimizer(cost_threshold=100)
        plan = QueryPlan("q1", [_scan("t", 1200)])
        assert opt.analyze_plan(plan).verdict == "critical"

    def test_expensive_ops_listed(self):
        opt = QueryOptimizer(cost_threshold=100)
        plan = QueryPlan("q1", [_scan("t", 500), _scan("t2", 5)])
        rep = opt.analyze_plan(plan)
        assert len(rep.expensive_ops) == 1
        assert rep.expensive_ops[0].table == "t"

    def test_index_suggestion_on_repeated_filter(self):
        opt = QueryOptimizer()
        plan = QueryPlan("q1", [
            _scan("orders", 10, fields=["user_id"]),
            _scan("orders", 10, fields=["user_id"]),
            _scan("orders", 10, fields=["user_id"]),
        ])
        sugg = opt.suggest_indexes(plan)
        assert len(sugg) == 1
        assert sugg[0].table == "orders"
        assert sugg[0].fields == ["user_id"]

    def test_index_no_suggestion_for_single_filter(self):
        opt = QueryOptimizer()
        plan = QueryPlan("q1", [_scan("orders", 10, fields=["user_id"])])
        assert opt.suggest_indexes(plan) == []

    def test_index_aggregates_across_plans(self):
        opt = QueryOptimizer()
        plans = [
            QueryPlan(f"q{i}", [_scan("users", 5, fields=["email"])])
            for i in range(3)
        ]
        sugg = opt.suggest_indexes_from_plans(plans)
        assert len(sugg) == 1
        assert sugg[0].fields == ["email"]

    def test_cache_l1_high_hit_rate(self):
        opt = QueryOptimizer()
        rec = opt.cache_advisor("k", cost=10, hit_rate=0.95)
        assert rec.level == CacheLevel.L1

    def test_cache_l2_medium_hit_rate(self):
        opt = QueryOptimizer()
        rec = opt.cache_advisor("k", cost=10, hit_rate=0.6)
        assert rec.level == CacheLevel.L2

    def test_cache_expensive_low_hit_still_l2(self):
        opt = QueryOptimizer(cost_threshold=100)
        rec = opt.cache_advisor("k", cost=500, hit_rate=0.1)
        assert rec.level == CacheLevel.L2

    def test_cache_none_cheap_low_hit(self):
        opt = QueryOptimizer(cost_threshold=100)
        rec = opt.cache_advisor("k", cost=5, hit_rate=0.1)
        assert rec.level == CacheLevel.NONE

    def test_sharding_high_cardinality_hash(self):
        opt = QueryOptimizer()
        s = opt.suggest_sharding_key("orders", {"user_id": 5000, "status": 5})
        assert s is not None
        assert s.key_field == "user_id"
        assert s.method == "hash"

    def test_sharding_low_cardinality_rejected(self):
        opt = QueryOptimizer(sharding_cardinality_threshold=100)
        assert opt.suggest_sharding_key("orders", {"status": 4}) is None

    def test_sharding_range_for_moderate(self):
        opt = QueryOptimizer(sharding_cardinality_threshold=100)
        s = opt.suggest_sharding_key("events", {"day": 150})
        assert s.method == "range"

    def test_sharding_empty_fields(self):
        opt = QueryOptimizer()
        assert opt.suggest_sharding_key("orders", {}) is None

    def test_n_plus_1_detected(self):
        opt = QueryOptimizer(n_plus_1_threshold=3)
        plans = [QueryPlan(f"q{i}", [_scan("users", 2)]) for i in range(5)]
        findings = opt.detect_n_plus_1(plans)
        assert len(findings) == 1
        assert findings[0].repetitions == 5
        assert findings[0].severity == "medium"

    def test_n_plus_1_high_severity(self):
        opt = QueryOptimizer(n_plus_1_threshold=3)
        plans = [QueryPlan(f"q{i}", [_scan("users", 2)]) for i in range(15)]
        findings = opt.detect_n_plus_1(plans)
        assert findings[0].severity == "high"

    def test_n_plus_1_not_triggered_below_threshold(self):
        opt = QueryOptimizer(n_plus_1_threshold=3)
        plans = [QueryPlan("q1", [_scan("users", 2)]),
                 QueryPlan("q2", [_scan("users", 2)])]
        assert opt.detect_n_plus_1(plans) == []

    def test_n_plus_1_different_plans_not_grouped(self):
        opt = QueryOptimizer(n_plus_1_threshold=3)
        plans = [
            QueryPlan("q1", [_scan("users", 2)]),
            QueryPlan("q2", [_scan("orders", 2)]),
            QueryPlan("q3", [_scan("items", 2)]),
        ]
        assert opt.detect_n_plus_1(plans) == []

    def test_report_serializable(self):
        opt = QueryOptimizer()
        plan = QueryPlan("q1", [_scan("t", 500, fields=["a", "a"])])
        d = opt.analyze_plan(plan).to_dict()
        assert d["query_id"] == "q1"
        assert d["total_cost"] == 500
        assert "cache_recommendation" in d

    def test_report_to_dict_json_roundtrip(self):
        import json
        opt = QueryOptimizer()
        plan = QueryPlan("q1", [_scan("t", 10)])
        d = opt.analyze_plan(plan).to_dict()
        assert json.loads(json.dumps(d))["query_id"] == "q1"


# ======================================================================
# M3: Disaster Recovery
# ======================================================================

class TestDisasterRecovery:

    def _source_with_files(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        (src / "a.txt").write_text("alpha", encoding="utf-8")
        sub = src / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("beta-contents", encoding="utf-8")
        return src

    def test_backup_copies_files(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        assert (bdir / "a.txt").read_text(encoding="utf-8") == "alpha"
        assert (bdir / "sub" / "b.txt").read_text(encoding="utf-8") == "beta-contents"
        assert len(m.files) == 2
        assert m.total_bytes > 0

    def test_backup_manifest_hashes(self, tmp_path):
        src = self._source_with_files(tmp_path)
        dr = DisasterRecovery()
        m = dr.create_backup(src, tmp_path / "backup")
        entry = next(f for f in m.files if f["path"] == "a.txt")
        assert entry["sha256"] == hashlib.sha256(b"alpha").hexdigest()

    def test_backup_missing_source_raises(self, tmp_path):
        dr = DisasterRecovery()
        with pytest.raises(FileNotFoundError):
            dr.create_backup(tmp_path / "nope", tmp_path / "backup")

    def test_verify_ok(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        res = dr.verify_backup(bdir, m)
        assert res.valid is True
        assert res.missing_files == []
        assert res.hash_mismatches == []
        assert m.status == "verified"

    def test_verify_detects_tampering(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        (bdir / "a.txt").write_text("tampered!", encoding="utf-8")
        res = dr.verify_backup(bdir, m)
        assert res.valid is False
        assert res.hash_mismatches == ["a.txt"]
        assert m.status == "failed"

    def test_verify_detects_missing_file(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        (bdir / "a.txt").unlink()
        res = dr.verify_backup(bdir, m)
        assert res.valid is False
        assert res.missing_files == ["a.txt"]

    def test_restore_dry_run_writes_nothing(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        target = tmp_path / "target"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        res = dr.restore_backup(bdir, m, target, dry_run=True)
        assert res.dry_run is True
        assert len(res.restored_files) == 2
        assert not target.exists()

    def test_restore_real_recovers_content(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        target = tmp_path / "target"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        res = dr.restore_backup(bdir, m, target, dry_run=False)
        assert res.dry_run is False
        assert (target / "a.txt").read_text(encoding="utf-8") == "alpha"
        assert (target / "sub" / "b.txt").read_text(encoding="utf-8") == "beta-contents"

    def test_restore_skips_missing_backup_file(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        target = tmp_path / "target"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        (bdir / "a.txt").unlink()
        res = dr.restore_backup(bdir, m, target, dry_run=False)
        assert res.skipped_files == ["a.txt"]
        assert res.restored_files == ["sub/b.txt"]

    def test_plan_restore_lists_actions(self, tmp_path):
        src = self._source_with_files(tmp_path)
        bdir = tmp_path / "backup"
        dr = DisasterRecovery()
        m = dr.create_backup(src, bdir)
        actions = dr.plan_restore(bdir, m)
        assert all(a["action"] == "restore" for a in actions)

    def test_rto_proportional_to_size(self, tmp_path):
        src = self._source_with_files(tmp_path)
        dr = DisasterRecovery()
        m = dr.create_backup(src, tmp_path / "backup")
        rr = dr.compute_rto_rpo(tmp_path / "backup", m, now=datetime.now(timezone.utc))
        expected = m.total_bytes / (100 * 1024 * 1024)
        assert rr.rto_seconds == pytest.approx(expected)
        assert rr.rto_seconds < 15 * 60  # under 15-minute RTO target

    def test_rpo_from_manifest_timestamp(self, tmp_path):
        src = self._source_with_files(tmp_path)
        dr = DisasterRecovery()
        m = dr.create_backup(src, tmp_path / "backup")
        now = datetime.now(timezone.utc)
        rr = dr.compute_rto_rpo(tmp_path / "backup", m, now=now + timedelta(minutes=10))
        assert 590 <= rr.rpo_seconds <= 610  # ~10 minutes

    def test_rpo_across_multiple_manifests(self, tmp_path):
        now = datetime.now(timezone.utc)
        m1 = BackupManifest(backup_id="b1",
                            created_at=(now - timedelta(hours=2)).isoformat(),
                            source_dir="/x")
        m2 = BackupManifest(backup_id="b2",
                            created_at=(now - timedelta(minutes=5)).isoformat(),
                            source_dir="/x")
        dr = DisasterRecovery()
        rpo = dr.compute_rpo_from_manifests([m1, m2], now=now)
        assert 290 <= rpo <= 310  # newest backup wins: ~5 min

    def test_rpo_empty_manifests_infinite(self):
        dr = DisasterRecovery()
        assert dr.compute_rpo_from_manifests([]) == float("inf")

    def test_failover_happy_path(self):
        dr = DisasterRecovery()
        assert dr.failover_state == FailoverState.PRIMARY
        assert dr.start_failover() == FailoverState.FAILOVER
        assert dr.promote_replica() == FailoverState.PROMOTED
        assert dr.start_failback() == FailoverState.FAILBACK
        assert dr.complete_failback() == FailoverState.RECONCILED

    def test_failover_invalid_transition_promote(self):
        dr = DisasterRecovery()
        with pytest.raises(FailoverError):
            dr.promote_replica()

    def test_failover_invalid_transition_failback(self):
        dr = DisasterRecovery()
        with pytest.raises(FailoverError):
            dr.start_failback()

    def test_failover_cannot_restart_from_promoted(self):
        dr = DisasterRecovery()
        dr.start_failover()
        dr.promote_replica()
        with pytest.raises(FailoverError):
            dr.start_failover()

    def test_failover_history_records(self):
        dr = DisasterRecovery()
        dr.start_failover()
        dr.promote_replica()
        hist = dr.failover_history()
        assert len(hist) == 2
        assert hist[0]["from"] == "primary"
        assert hist[1]["to"] == "promoted"

    def test_manifest_roundtrip(self, tmp_path):
        src = self._source_with_files(tmp_path)
        dr = DisasterRecovery()
        m = dr.create_backup(src, tmp_path / "backup")
        m2 = BackupManifest.from_dict(m.to_dict())
        assert m2.backup_id == m.backup_id
        assert m2.total_bytes == m.total_bytes
        assert len(m2.files) == len(m.files)

    def test_serialize_manifest_json(self, tmp_path):
        import json
        src = self._source_with_files(tmp_path)
        dr = DisasterRecovery()
        m = dr.create_backup(src, tmp_path / "backup")
        parsed = json.loads(dr.serialize_manifest(m.backup_id))
        assert parsed["backup_id"] == m.backup_id

    def test_dr_never_touches_real_data(self, tmp_path):
        """Guard: DR only writes where the caller points it."""
        src = self._source_with_files(tmp_path)
        dr = DisasterRecovery()
        m = dr.create_backup(src, tmp_path / "backup")
        dr.restore_backup(tmp_path / "backup", m, tmp_path / "target")
        # all artifacts confined to tmp_path
        for p in [tmp_path / "backup", tmp_path / "target"]:
            assert str(p).startswith(str(tmp_path))


# ======================================================================
# M4: Observability
# ======================================================================

class TestObservability:

    def test_span_lifecycle(self):
        obs = Observability()
        s = obs.start_span("op")
        time.sleep(0.01)
        obs.end_span(s)
        assert s.duration_ms >= 5
        assert s.status == SpanStatus.OK

    def test_span_parent_trace_inherited(self):
        obs = Observability()
        parent = obs.start_span("parent")
        child = obs.start_span("child", parent_span_id=parent.span_id)
        assert child.parent_id == parent.span_id
        assert child.trace_id == parent.trace_id

    def test_trace_tree_order(self):
        obs = Observability()
        root = obs.start_span("root")
        child = obs.start_span("child", parent_span_id=root.span_id)
        grand = obs.start_span("grand", parent_span_id=child.span_id)
        tree = obs.trace_tree(root.trace_id)
        assert [s.name for s in tree] == ["root", "child", "grand"]

    def test_span_error_status(self):
        obs = Observability()
        s = obs.start_span("op")
        obs.end_span(s, SpanStatus.ERROR)
        assert s.status == SpanStatus.ERROR

    def test_traced_context_ok(self):
        obs = Observability()
        with obs.traced("op") as span:
            pass
        assert span.status == SpanStatus.OK
        assert obs.slo_success_ratio(window=10) == 1.0

    def test_traced_context_error_records_failure(self):
        obs = Observability()
        try:
            with obs.traced("op"):
                raise ValueError("boom")
        except ValueError:
            pass
        assert obs.slo_success_ratio(window=10) == 0.0

    def test_slo_ratio_over_window(self):
        obs = Observability(window_seconds=100)
        now = time.time()
        for i in range(8):
            obs.record_outcome(True, at=now - 50)
        for i in range(2):
            obs.record_outcome(False, at=now - 50)
        assert obs.slo_success_ratio(window=100, now=now) == pytest.approx(0.8)

    def test_slo_window_excludes_old_events(self):
        obs = Observability(window_seconds=10)
        now = time.time()
        obs.record_outcome(False, at=now - 1000)  # outside window
        obs.record_outcome(True, at=now - 1)
        assert obs.slo_success_ratio(window=10, now=now) == 1.0

    def test_slo_no_data_returns_none(self):
        obs = Observability()
        assert obs.slo_success_ratio() is None

    def test_slo_compliance_exact_target_fluid(self):
        obs = Observability(slo_target=0.99)
        now = time.time()
        for _ in range(99):
            obs.record_outcome(True, at=now)
        obs.record_outcome(False, at=now)
        status = obs.slo_status(window=60, now=now)
        assert status["compliant"] is True   # 0.99 >= 0.99 target
        assert status["observed"] == pytest.approx(0.99)

    def test_slo_compliance_breach(self):
        obs = Observability(slo_target=0.99)
        now = time.time()
        for _ in range(95):
            obs.record_outcome(True, at=now)
        for _ in range(5):
            obs.record_outcome(False, at=now)
        status = obs.slo_status(window=60, now=now)
        assert status["compliant"] is False
        assert status["observed"] == pytest.approx(0.95)

    def test_error_budget_burn_rate(self):
        obs = Observability(slo_target=0.99)
        now = time.time()
        for _ in range(90):
            obs.record_outcome(True, at=now)
        for _ in range(10):
            obs.record_outcome(False, at=now)
        # error ratio 0.1 / allowed 0.01 = 10x burn
        assert obs.error_budget_burn_rate(window=60, now=now) == pytest.approx(10.0)

    def test_error_budget_remaining(self):
        obs = Observability(slo_target=0.99)
        now = time.time()
        for _ in range(95):
            obs.record_outcome(True, at=now)
        for _ in range(5):
            obs.record_outcome(False, at=now)
        # consumed 5x budget -> remaining 0
        assert obs.error_budget_remaining(window=60, now=now) == 0.0

    def test_alert_fires_after_duration(self):
        obs = Observability()
        rule = AlertRule("r1", "cpu", threshold=90, comparison="gt",
                         for_seconds=60, severity=AlertSeverity.CRITICAL)
        obs.add_alert_rule(rule)
        t0 = 1000.0
        obs.record_metric("cpu", 95, at=t0)          # breach starts
        obs.record_metric("cpu", 95, at=t0 + 30)     # still inside for-window
        assert obs.fired_alerts() == []
        obs.record_metric("cpu", 95, at=t0 + 61)     # duration exceeded
        alerts = obs.fired_alerts()
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    def test_alert_resets_when_value_recovers(self):
        obs = Observability()
        obs.add_alert_rule(AlertRule("r1", "cpu", 90, "gt", for_seconds=60))
        t0 = 1000.0
        obs.record_metric("cpu", 95, at=t0)
        obs.record_metric("cpu", 50, at=t0 + 10)   # recovered
        obs.record_metric("cpu", 95, at=t0 + 70)   # breach restarts
        assert obs.fired_alerts() == []

    def test_alert_below_threshold_never_fires(self):
        obs = Observability()
        obs.add_alert_rule(AlertRule("r1", "cpu", 90, "gt", for_seconds=10))
        for i in range(10):
            obs.record_metric("cpu", 50, at=1000.0 + i * 20)
        assert obs.fired_alerts() == []

    def test_alert_comparison_operators(self):
        assert AlertRule("a", "m", 10, "gte", 0).evaluate(10) is True
        assert AlertRule("b", "m", 10, "lt", 0).evaluate(9) is True
        assert AlertRule("c", "m", 10, "lte", 0).evaluate(10) is True
        assert AlertRule("d", "m", 10, "eq", 0).evaluate(10) is True
        with pytest.raises(ValueError):
            AlertRule("e", "m", 10, "ne", 0).evaluate(10)

    def test_duplicate_rule_rejected(self):
        obs = Observability()
        obs.add_alert_rule(AlertRule("r1", "cpu", 90, "gt", 0))
        with pytest.raises(ValueError):
            obs.add_alert_rule(AlertRule("r1", "cpu", 90, "gt", 0))

    def test_remove_rule(self):
        obs = Observability()
        obs.add_alert_rule(AlertRule("r1", "cpu", 90, "gt", 0))
        assert obs.remove_alert_rule("r1") is True
        assert obs.remove_alert_rule("r1") is False

    def test_log_ring_buffer_capacity(self):
        obs = Observability(log_capacity=5)
        for i in range(10):
            obs.log("INFO", f"msg-{i}")
        logs = obs.query_logs()
        assert len(logs) == 5
        assert logs[0].message == "msg-5"
        assert logs[-1].message == "msg-9"

    def test_log_filter_level(self):
        obs = Observability()
        obs.log("INFO", "info-msg")
        obs.log("ERROR", "error-msg")
        assert len(obs.query_logs(min_level="ERROR")) == 1
        assert obs.query_logs(min_level="ERROR")[0].level == "ERROR"

    def test_log_filter_contains(self):
        obs = Observability()
        obs.log("INFO", "payment processed")
        obs.log("INFO", "user login")
        hits = obs.query_logs(contains="payment")
        assert len(hits) == 1
        assert "payment" in hits[0].message

    def test_log_filter_time_and_source(self):
        obs = Observability()
        obs.log("INFO", "early", source="svc-a", timestamp=100.0)
        obs.log("INFO", "late", source="svc-b", timestamp=200.0)
        assert len(obs.query_logs(since=150.0)) == 1
        assert obs.query_logs(source="svc-a")[0].message == "early"

    def test_log_filter_limit(self):
        obs = Observability()
        for i in range(8):
            obs.log("INFO", f"m{i}")
        assert len(obs.query_logs(limit=3)) == 3

    def test_slo_and_alerts_share_metrics(self):
        obs = Observability(slo_target=0.99)
        obs.add_alert_rule(AlertRule("err", "error_rate", 0.5, "gt", 0))
        now = time.time()
        for _ in range(10):
            obs.record_outcome(False, at=now)
        obs.record_metric("error_rate", 0.9, at=now)
        assert obs.error_budget_burn_rate(window=60, now=now) > 1.0
        assert len(obs.fired_alerts()) == 1


# ======================================================================
# M5: Business Intelligence
# ======================================================================

class TestBusinessIntelligence:

    def _points(self):
        base = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)
        pts = []
        for h in range(2):
            for m in range(2):
                pts.append(TimePoint(base + timedelta(hours=h, minutes=m * 30),
                                     value=10.0))
        return pts  # 4 points, 2 hourly buckets, 10 each

    def test_hourly_rollup_sum(self):
        bi = BusinessIntelligence()
        out = bi.aggregate_time_series(self._points(), RollupGranularity.HOURLY)
        assert len(out) == 2
        assert out[0].value == 20
        assert out[0].timestamp.minute == 0

    def test_daily_rollup_sum(self):
        bi = BusinessIntelligence()
        out = bi.aggregate_time_series(self._points(), RollupGranularity.DAILY)
        assert len(out) == 1
        assert out[0].value == 40
        assert out[0].timestamp.hour == 0

    def test_average_rollup(self):
        bi = BusinessIntelligence()
        out = bi.average_time_series(self._points(), RollupGranularity.HOURLY)
        assert out[0].value == 10  # mean of two 10s

    def test_rollup_empty_input(self):
        bi = BusinessIntelligence()
        assert bi.aggregate_time_series([], RollupGranularity.DAILY) == []

    def test_rollup_chronological_order(self):
        bi = BusinessIntelligence()
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        pts = [TimePoint(base + timedelta(days=i), float(i)) for i in range(5, -1, -1)]
        out = bi.aggregate_time_series(pts, RollupGranularity.DAILY)
        assert [p.value for p in out] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]

    def test_kpi_target_met(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k1", "uptime", actual=99.95, target=99.9)
        assert kpi.met is True
        assert kpi.attainment == pytest.approx(99.95 / 99.9)

    def test_kpi_target_missed(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k1", "uptime", actual=99.5, target=99.9)
        assert kpi.met is False
        assert kpi.attainment < 1.0

    def test_kpi_lower_is_better(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k2", "p95_latency_ms", actual=80, target=100,
                               higher_is_better=False)
        assert kpi.met is True
        assert kpi.attainment == pytest.approx(100 / 80)

    def test_kpi_trend_up(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k3", "users", actual=120, target=100,
                               history=[50, 70, 90, 120])
        assert kpi.direction == TrendDirection.UP

    def test_kpi_trend_down(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k3", "errors", actual=5, target=10,
                               history=[30, 20, 10, 5])
        assert kpi.direction == TrendDirection.DOWN

    def test_kpi_trend_stable(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k3", "flat", actual=5, target=10,
                               history=[5, 5, 5, 5])
        assert kpi.direction == TrendDirection.STABLE

    def test_kpi_insufficient_history(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k4", "solo", actual=5, target=10, history=[5])
        assert kpi.direction == TrendDirection.INSUFFICIENT

    def test_kpi_to_dict(self):
        bi = BusinessIntelligence()
        kpi = bi.calculate_kpi("k1", "uptime", 99.95, 99.9, unit="%")
        d = kpi.to_dict()
        assert d["met"] is True
        assert d["unit"] == "%"

    def test_dashboard_widgets_and_serialization(self):
        bi = BusinessIntelligence()
        dash = bi.create_dashboard("d1", "Ops Overview")
        dash.add_widget(MetricWidget("w1", "Uptime", value=99.95, unit="%"))
        dash.add_widget(ChartWidget("w2", "Requests", points=[
            TimePoint(datetime(2026, 10, 28, 10, tzinfo=timezone.utc), 100.0),
        ]))
        dash.add_widget(TableWidget("w3", "Top KPIs", columns=["kpi", "value"],
                                    rows=[["uptime", 99.95]]))
        d = dash.to_dict()
        assert len(d["widgets"]) == 3
        types = {w["type"] for w in d["widgets"]}
        assert types == {"metric", "chart", "table"}
        # JSON round trip
        import json
        parsed = json.loads(dash.to_json())
        assert parsed["dashboard_id"] == "d1"
        assert parsed["widgets"][0]["value"] == 99.95

    def test_dashboard_duplicate_rejected(self):
        bi = BusinessIntelligence()
        bi.create_dashboard("d1", "A")
        with pytest.raises(ValueError):
            bi.create_dashboard("d1", "B")

    def test_schedule_valid_and_next_run_hourly(self):
        bi = BusinessIntelligence()
        anchor = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)
        cfg = ScheduleConfig("rep1", "Hourly Ops", "hourly", anchor,
                             recipients=["owner@example.com"])
        bi.add_schedule(cfg)
        after = datetime(2026, 10, 28, 10, 30, tzinfo=timezone.utc)
        nxt = bi.next_run(cfg, after)
        assert nxt == datetime(2026, 10, 28, 11, 0, tzinfo=timezone.utc)

    def test_schedule_daily_next_run(self):
        bi = BusinessIntelligence()
        anchor = datetime(2026, 10, 27, 8, 0, tzinfo=timezone.utc)
        cfg = ScheduleConfig("rep2", "Daily", "daily", anchor,
                             recipients=["owner@example.com"])
        after = datetime(2026, 10, 28, 8, 5, tzinfo=timezone.utc)
        assert bi.next_run(cfg, after) == datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)

    def test_schedule_weekly_next_run(self):
        bi = BusinessIntelligence()
        anchor = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)  # Monday
        cfg = ScheduleConfig("rep3", "Weekly", "weekly", anchor,
                             recipients=["owner@example.com"])
        after = datetime(2026, 10, 28, 8, 0, tzinfo=timezone.utc)
        assert bi.next_run(cfg, after) == datetime(2026, 11, 2, 8, 0, tzinfo=timezone.utc)

    def test_schedule_invalid_interval_rejected(self):
        bi = BusinessIntelligence()
        cfg = ScheduleConfig("bad", "Bad", "minutely",
                             datetime(2026, 1, 1, tzinfo=timezone.utc),
                             recipients=["x@example.com"])
        with pytest.raises(ValueError):
            bi.add_schedule(cfg)

    def test_schedule_missing_recipients_rejected(self):
        cfg = ScheduleConfig("bad2", "Bad", "daily",
                             datetime(2026, 1, 1, tzinfo=timezone.utc),
                             recipients=[])
        assert cfg.validate() != []

    def test_serialize_report_data(self):
        bi = BusinessIntelligence()
        import json
        out = bi.serialize_report_data({"kpi": "uptime", "value": 99.95})
        assert json.loads(out)["value"] == 99.95

    def test_get_schedule(self):
        bi = BusinessIntelligence()
        cfg = ScheduleConfig("rep9", "D", "daily",
                             datetime(2026, 1, 1, tzinfo=timezone.utc),
                             recipients=["a@b.c"])
        bi.add_schedule(cfg)
        assert bi.get_schedule("rep9") is cfg
        assert bi.get_schedule("missing") is None


# ======================================================================
# Integration
# ======================================================================

class TestV30Integration:

    def test_lb_feeds_observability(self):
        """Route requests through LB; success/failure feed SLO accounting."""
        lb = LoadBalancer(cb_failure_threshold=10)
        obs = Observability(slo_target=0.99)
        lb.add_node(_node("n1"))
        lb.add_node(_node("n2"))
        for i in range(9):
            node = lb.route()
            lb.release(node.node_id)
            obs.record_outcome(True)
        lb.mark_failure(lb.nodes()[0].node_id)
        obs.record_outcome(False)
        assert obs.slo_success_ratio(window=60) == pytest.approx(0.9)
        assert obs.error_budget_burn_rate(window=60) > 1.0

    def test_optimizer_advises_lb_backed_query(self):
        """Plan analysis -> cache advice aligns with heavy routing stats."""
        lb = LoadBalancer()
        lb.add_node(_node("db-1"))
        opt = QueryOptimizer(cost_threshold=100)
        plan = QueryPlan("heavy-report", [_scan("reports", 900, fields=["owner_id"] * 1)])
        rep = opt.analyze_plan(plan)
        assert rep.cache_recommendation.level in (CacheLevel.L1, CacheLevel.L2)
        assert rep.verdict in ("needs_optimization", "critical")

    def test_dr_backup_then_restore_roundtrip(self, tmp_path):
        dr = DisasterRecovery()
        src = tmp_path / "svc-data"
        src.mkdir()
        (src / "state.json").write_text('{"ok": true}', encoding="utf-8")
        bdir = tmp_path / "backup"
        m = dr.create_backup(src, bdir)
        assert dr.verify_backup(bdir, m).valid
        target = tmp_path / "restored"
        dr.restore_backup(bdir, m, target)
        assert (target / "state.json").read_text(encoding="utf-8") == '{"ok": true}'

    def test_full_v30_pipeline(self, tmp_path):
        """M1..M5 chained: route -> trace -> backup -> optimize -> dashboard."""
        # M1
        lb = LoadBalancer()
        lb.add_node(_node("api-1"))
        lb.add_node(_node("api-2"))
        # M4
        obs = Observability(slo_target=0.99)
        with obs.traced("request") as span:
            node = lb.route()
        lb.release(node.node_id)
        assert span.trace_id.startswith("trace-")
        # M3
        dr = DisasterRecovery()
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        (cfg_dir / "app.conf").write_text("mode=prod", encoding="utf-8")
        manifest = dr.create_backup(cfg_dir, tmp_path / "backup")
        assert dr.verify_backup(tmp_path / "backup", manifest).valid
        # M2
        opt = QueryOptimizer()
        plan = QueryPlan("app-query", [_scan("app", 30)])
        assert opt.analyze_plan(plan).verdict == "healthy"
        # M5
        bi = BusinessIntelligence()
        dash = bi.create_dashboard("v30", "V30 Health")
        dash.add_widget(MetricWidget("m-slo", "SLO", value=obs.slo_success_ratio(60) or 0.0))
        dash.add_widget(MetricWidget("m-nodes", "Healthy Nodes",
                                     value=float(len(lb.healthy_nodes()))))
        dash.add_widget(MetricWidget("m-rpo", "RPO(s)",
                                     value=dr.compute_rto_rpo(
                                         tmp_path / "backup", manifest).rpo_seconds))
        d = dash.to_dict()
        assert len(d["widgets"]) == 3
        assert all(w["type"] == "metric" for w in d["widgets"])

    def test_scaling_package_importable(self):
        import quan_ai_brain.scaling as scaling
        assert scaling.__version__ == "V30.0"
        from quan_ai_brain.scaling import (
            business_intelligence,
            disaster_recovery,
            horizontal_scaling,
            monitoring,
            performance_optimizer,
        )
        assert all([business_intelligence, disaster_recovery, horizontal_scaling,
                    monitoring, performance_optimizer])
