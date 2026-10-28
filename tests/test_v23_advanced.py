"""
Tests for V23 Sprint Modules M2-M5

Covers:
- M2 FederatedOrchestrator (learning/federated_orchestrator.py)
- M3 Collaboration (cognition/collaboration.py)
- M4 PerformanceOptimizer (optimization/performance_optimizer.py)
- M5 SecurityHardening (security/hardening.py)
- Cross-module integration scenarios
"""

import math

import pytest

from quan_ai_brain.learning.federated_orchestrator import (
    DifferentialPrivacy,
    FederatedNode,
    FederatedOrchestrator,
    InsufficientNodesError,
    NodeUpdate,
    NodeUnresponsiveError,
    PrivacyBudgetExhausted,
)
from quan_ai_brain.cognition.collaboration import (
    CollaborationManager,
    ConflictEvent,
    StateEntry,
    VectorClock,
)
from quan_ai_brain.optimization.performance_optimizer import (
    OptimizationReport,
    PerformanceOptimizer,
    ProfileError,
)
from quan_ai_brain.security.hardening import (
    ConfigHardeningScanner,
    Finding,
    HardeningReport,
    RiskLevel,
)


# ===========================================================================
# M2: Federated Orchestrator
# ===========================================================================
class TestFederatedOrchestrator:
    def _make_orchestrator(self, n_nodes=3, **kw):
        nodes = [
            FederatedNode(node_id=f"node-{i}", samples=100)
            for i in range(n_nodes)
        ]
        return FederatedOrchestrator(nodes=nodes, **kw)

    @staticmethod
    def _train_ok(node_id, global_weights):
        shift = 0.0 if node_id.endswith("0") else 0.2
        return NodeUpdate(
            node_id=node_id,
            round_id=1,
            weights={"w": 1.0 + shift},
            knowledge_updates=[f"fact-{node_id}"],
            loss=0.5,
            samples=100,
        )

    # ------------------------------------------------------- registration
    def test_register_node(self):
        orch = FederatedOrchestrator()
        assert orch.register_node(FederatedNode(node_id="a")) is True

    def test_register_duplicate_node_returns_false(self):
        orch = self._make_orchestrator(n_nodes=1)
        assert orch.register_node(FederatedNode(node_id="node-0")) is False

    def test_unregister_node(self):
        orch = self._make_orchestrator(n_nodes=1)
        assert orch.unregister_node("node-0") is True
        assert orch.get_node("node-0") is None

    def test_unregister_unknown_node_returns_false(self):
        orch = FederatedOrchestrator()
        assert orch.unregister_node("ghost") is False

    def test_node_status_summary(self):
        orch = self._make_orchestrator(n_nodes=2)
        orch.nodes["node-1"].status = "unresponsive"
        summary = orch.node_status_summary()
        assert summary == {"active": 1, "unresponsive": 1}

    def test_eligible_node_ids_excludes_dropped(self):
        orch = self._make_orchestrator(n_nodes=2)
        orch.nodes["node-1"].status = "dropped"
        assert orch.eligible_node_ids() == ["node-0"]

    # ------------------------------------------------------------ voting
    def test_vote_requires_eligible_voter(self):
        orch = self._make_orchestrator(n_nodes=2)
        orch.nodes["node-0"].status = "dropped"
        assert orch.cast_vote("node-0", "node-1", accept=False) is False

    def test_vote_unknown_target_rejected(self):
        orch = self._make_orchestrator(n_nodes=2)
        assert orch.cast_vote("node-0", "ghost", accept=False) is False

    def test_vote_self_rejected(self):
        orch = self._make_orchestrator(n_nodes=2)
        assert orch.cast_vote("node-0", "node-0", accept=False) is False

    def test_majority_reject_excludes_node(self):
        orch = self._make_orchestrator(n_nodes=3)
        orch.cast_vote("node-1", "node-0", accept=False)
        orch.cast_vote("node-2", "node-0", accept=False)
        result = orch.run_round(self._train_ok)
        assert "node-0" in result.excluded_nodes
        assert "node-0" not in result.participants

    def test_majority_accept_keeps_node(self):
        orch = self._make_orchestrator(n_nodes=3)
        orch.cast_vote("node-1", "node-0", accept=True)
        orch.cast_vote("node-2", "node-0", accept=False)
        result = orch.run_round(self._train_ok)
        assert "node-0" not in result.excluded_nodes

    def test_votes_reset_after_round(self):
        orch = self._make_orchestrator(n_nodes=3)
        orch.cast_vote("node-1", "node-0", accept=False)
        orch.cast_vote("node-2", "node-0", accept=False)
        orch.run_round(self._train_ok)
        orch.run_round(self._train_ok)  # votes cleared -> node-0 back in
        assert "node-0" in orch.round_results[-1].participants

    # ---------------------------------------------------- round execution
    def test_run_round_basic_aggregation(self):
        orch = self._make_orchestrator(n_nodes=3)
        result = orch.run_round(self._train_ok)
        # 1.0, 1.2, 1.2 with equal samples -> 1.1333...
        assert math.isclose(result.aggregated_weights["w"], (1.0 + 1.2 + 1.2) / 3, rel_tol=1e-9)
        assert result.updates_received == 3
        assert result.global_model_version == 1

    def test_weighted_aggregation_by_samples(self):
        orch = FederatedOrchestrator(
            nodes=[
                FederatedNode(node_id="big", samples=1000),
                FederatedNode(node_id="small", samples=100),
            ]
        )

        def train(node_id, gw):
            return NodeUpdate(
                node_id=node_id,
                round_id=1,
                weights={"w": 2.0 if node_id == "big" else 0.0},
                samples=1000 if node_id == "big" else 100,
            )

        result = orch.run_round(train)
        expected = (2.0 * 1000 + 0.0 * 100) / 1100
        assert math.isclose(result.aggregated_weights["w"], expected, rel_tol=1e-9)

    def test_min_nodes_enforced(self):
        orch = FederatedOrchestrator(min_nodes=2)
        orch.register_node(FederatedNode(node_id="solo"))
        with pytest.raises(InsufficientNodesError):
            orch.run_round(self._train_ok)

    def test_unresponsive_node_tracked(self):
        orch = self._make_orchestrator(n_nodes=3)

        def train(node_id, gw):
            if node_id == "node-1":
                raise NodeUnresponsiveError("simulated timeout")
            return self._train_ok(node_id, gw)

        result = orch.run_round(train)
        assert result.unresponsive_nodes == ["node-1"]
        assert result.updates_received == 2
        assert orch.get_node("node-1").status == "unresponsive"

    def test_unresponsive_node_dropped_after_repeated_failures(self):
        orch = self._make_orchestrator(n_nodes=3, max_missed_rounds=2)

        def train(node_id, gw):
            if node_id == "node-1":
                raise NodeUnresponsiveError("simulated timeout")
            return self._train_ok(node_id, gw)

        orch.run_round(train)
        orch.run_round(train)
        node = orch.get_node("node-1")
        assert node.status == "dropped"
        assert node.missed_rounds == 2

    def test_responsive_node_status_reset(self):
        orch = self._make_orchestrator(n_nodes=2)
        orch.nodes["node-1"].status = "unresponsive"
        orch.run_round(self._train_ok)
        assert orch.get_node("node-1").status == "active"
        assert orch.get_node("node-1").missed_rounds == 0

    def test_knowledge_updates_merged_and_deduped(self):
        orch = self._make_orchestrator(n_nodes=2)

        def train(node_id, gw):
            return NodeUpdate(
                node_id=node_id,
                round_id=1,
                weights={"w": 1.0},
                knowledge_updates=["shared-fact", f"unique-{node_id}"],
            )

        result = orch.run_round(train)
        # 2 nodes x ('shared-fact' + unique) = 3 unique items
        assert result.knowledge_updates == ["shared-fact", "unique-node-0", "unique-node-1"]

    def test_knowledge_from_excluded_node_dropped(self):
        orch = self._make_orchestrator(n_nodes=3)
        orch.cast_vote("node-1", "node-0", accept=False)
        orch.cast_vote("node-2", "node-0", accept=False)
        result = orch.run_round(self._train_ok)
        assert "fact-node-0" not in result.knowledge_updates
        assert "fact-node-1" in result.knowledge_updates

    def test_round_result_to_dict_roundtrip(self):
        orch = self._make_orchestrator(n_nodes=2)
        result = orch.run_round(self._train_ok)
        data = result.to_dict()
        assert data["round_id"] == 1
        assert data["updates_received"] == 2
        assert isinstance(data["aggregated_weights"], dict)

    def test_global_weights_carry_to_next_round(self):
        orch = self._make_orchestrator(n_nodes=2)
        orch.run_round(self._train_ok)
        seen: list = []

        def train(node_id, gw):
            if not seen:
                seen.append(dict(gw))
            return self._train_ok(node_id, gw)

        orch.run_round(train)
        assert seen[0] == {"w": (1.0 + 1.2) / 2}

    # --------------------------------------------------------------- DP
    def test_dp_disabled_by_default(self):
        orch = self._make_orchestrator(n_nodes=2)
        result = orch.run_round(self._train_ok)
        assert result.aggregated_weights == orch.global_weights

    def test_dp_laplace_deterministic_with_seed(self):
        dp1 = DifferentialPrivacy(epsilon=1.0, seed=42)
        dp2 = DifferentialPrivacy(epsilon=1.0, seed=42)
        v1 = dp1.add_noise(10.0)
        v2 = dp2.add_noise(10.0)
        assert v1 == v2

    def test_dp_gaussian_deterministic_with_seed(self):
        dp = DifferentialPrivacy(epsilon=1.0, mechanism="gaussian", seed=7)
        value = dp.add_noise(5.0)
        assert isinstance(value, float)
        # deterministic: same seed same noise
        dp2 = DifferentialPrivacy(epsilon=1.0, mechanism="gaussian", seed=7)
        assert dp2.add_noise(5.0) == value

    def test_dp_noise_changes_value(self):
        dp = DifferentialPrivacy(epsilon=0.1, seed=1)
        values = {dp.add_noise(0.0) for _ in range(20)}
        assert len(values) > 1  # noise actually perturbs

    def test_dp_budget_exhaustion(self):
        dp = DifferentialPrivacy(epsilon=5.0, max_budget=10.0)
        dp.add_noise(1.0)
        dp.add_noise(1.0)
        with pytest.raises(PrivacyBudgetExhausted):
            dp.add_noise(1.0)  # 5+5+5 > 10

    def test_dp_budget_remaining(self):
        dp = DifferentialPrivacy(epsilon=1.0, max_budget=10.0)
        dp.add_noise(1.0, epsilon=2.0)
        assert math.isclose(dp.budget_remaining, 8.0)

    def test_dp_optional_in_rounds(self):
        dp = DifferentialPrivacy(epsilon=0.5, seed=11, max_budget=1000.0)
        orch = self._make_orchestrator(n_nodes=2, dp=dp)
        result = orch.run_round(self._train_ok)
        base = (1.0 + 1.2) / 2
        assert result.aggregated_weights["w"] != base  # noise applied
        # Budget spent once per aggregation round
        assert dp.epsilon_spent == pytest.approx(0.5)

    def test_dp_optional_in_rounds_no_dp(self):
        orch = self._make_orchestrator(n_nodes=2)
        result = orch.run_round(self._test_train_constant)
        assert result.aggregated_weights["w"] == 5.0  # no noise

    @staticmethod
    def _test_train_constant(node_id, gw):
        return NodeUpdate(node_id=node_id, round_id=1, weights={"w": 5.0})

    def test_dp_invalid_mechanism_rejected(self):
        with pytest.raises(ValueError):
            DifferentialPrivacy(mechanism="quantum")

    def test_dp_invalid_epsilon_rejected(self):
        with pytest.raises(ValueError):
            DifferentialPrivacy(epsilon=0.0)

    # -------------------------------------------------------- convergence
    def test_convergence_monitoring_true(self):
        orch = self._make_orchestrator(n_nodes=2, convergence_threshold=0.5)
        losses = [10.0, 9.8, 9.6]

        def make_train(loss):
            def train(node_id, gw):
                return NodeUpdate(
                    node_id=node_id, round_id=1, weights={"w": 1.0}, loss=loss
                )

            return train

        orch.run_round(make_train(losses[0]))
        orch.run_round(make_train(losses[1]))
        result = orch.run_round(make_train(losses[2]))
        assert result.converged is True

    def test_convergence_monitoring_false(self):
        orch = self._make_orchestrator(max_missed_rounds=99, convergence_threshold=0.01)
        losses = [10.0, 8.0, 5.0]

        def make_train(loss):
            def train(node_id, gw):
                return NodeUpdate(
                    node_id=node_id, round_id=1, weights={"w": 1.0}, loss=loss
                )

            return train

        orch.register_node(FederatedNode(node_id="n1"))
        orch.register_node(FederatedNode(node_id="n2"))
        orch.run_round(make_train(losses[0]))
        orch.run_round(make_train(losses[1]))
        result = orch.run_round(make_train(losses[2]))
        assert result.converged is False

    def test_monitor_convergence_api(self):
        orch = self._make_orchestrator(n_nodes=2, convergence_threshold=0.001)
        assert orch.monitor_convergence() is False  # no history

    def test_run_training_stops_on_convergence(self):
        orch = self._make_orchestrator(n_nodes=2, convergence_threshold=0.5)
        # Per-round loss schedule (shared by both nodes in a round; note the
        # train_fn is called once per node, so use a round-keyed dict).
        schedule = {0: 10.0, 1: 9.8, 2: 9.6, 3: 9.59}

        def train(node_id, gw):
            round_no = orch.global_model_version
            return NodeUpdate(
                node_id=node_id,
                round_id=round_no + 1,
                weights={"w": 1.0},
                loss=schedule[round_no],
            )

        results = orch.run_training(train, max_rounds=10)
        assert len(results) == 3  # stopped at 3rd round when converged
        assert results[-1].converged is True
        assert results[0].converged is False

    def test_run_training_max_rounds(self):
        orch = self._make_orchestrator(n_nodes=2, convergence_threshold=1e-9)
        # Oscillating losses never satisfy the all-deltas-shrinking condition.
        losses = iter([1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0])

        def train(node_id, gw):
            return NodeUpdate(
                node_id=node_id, round_id=1, weights={"w": 1.0}, loss=next(losses)
            )

        results = orch.run_training(train, max_rounds=4, stop_on_convergence=False)
        assert len(results) == 4
        assert orch.global_model_version == 4

    def test_run_training_stops_when_nodes_depleted(self):
        orch = FederatedOrchestrator(min_nodes=2)
        orch.register_node(FederatedNode(node_id="a"))
        orch.register_node(FederatedNode(node_id="b"))

        def train(node_id, gw):
            raise NodeUnresponsiveError("always down")

        results = orch.run_training(train, max_rounds=5)
        # both nodes drop after max_missed_rounds(2) -> round 3 raises
        assert len(results) < 5

    # ------------------------------------------------------------ edge
    def test_node_to_dict(self):
        node = FederatedNode(node_id="x", capabilities=["vision"])
        data = node.to_dict()
        assert data["node_id"] == "x"
        assert data["capabilities"] == ["vision"]

    def test_update_to_dict(self):
        update = NodeUpdate(node_id="n", round_id=1, weights={"w": 1.0})
        data = update.to_dict()
        assert data["node_id"] == "n"
        assert data["weights"] == {"w": 1.0}

    def test_aggregate_empty_updates(self):
        orch = FederatedOrchestrator(min_nodes=1)
        orch.register_node(FederatedNode(node_id="a"))
        # train_fn returns None -> treated as unresponsive, no updates
        result = orch.run_round(lambda nid, gw: None)
        assert result.aggregated_weights == {}
        assert result.aggregated_loss is None


# ===========================================================================
# M3: Collaboration
# ===========================================================================
class TestCollaboration:
    def _manager(self, **kw):
        return CollaborationManager(**kw)

    # ----------------------------------------------------------- sessions
    def test_create_session(self):
        mgr = self._manager()
        session = mgr.create_session("s1", topic="plan", owner_id="alice")
        assert session.session_id == "s1"
        assert mgr.get_session("s1") is session

    def test_create_duplicate_session_raises(self):
        mgr = self._manager()
        mgr.create_session("s1")
        with pytest.raises(ValueError):
            mgr.create_session("s1")

    def test_get_missing_session(self):
        mgr = self._manager()
        assert mgr.get_session("nope") is None

    def test_close_session(self):
        mgr = self._manager()
        mgr.create_session("s1")
        assert mgr.close_session("s1") is True
        assert mgr.get_session("s1").closed is True

    def test_close_unknown_session(self):
        mgr = self._manager()
        assert mgr.close_session("nope") is False

    # --------------------------------------------------------- membership
    def test_join_session(self):
        mgr = self._manager()
        mgr.create_session("s1")
        assert mgr.join("s1", "alice", role="owner") is True
        assert mgr.list_participants("s1") == ["alice"]

    def test_join_closed_session_rejected(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.close_session("s1")
        assert mgr.join("s1", "bob") is False

    def test_join_duplicate_rejected(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        assert mgr.join("s1", "alice") is False

    def test_join_invalid_role_raises(self):
        mgr = self._manager()
        mgr.create_session("s1")
        with pytest.raises(ValueError):
            mgr.join("s1", "bob", role="emperor")

    def test_join_unknown_session_rejected(self):
        mgr = self._manager()
        assert mgr.join("nope", "bob") is False

    def test_leave_session(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        assert mgr.leave("s1", "alice") is True
        assert mgr.list_participants("s1") == []

    def test_leave_unknown_participant(self):
        mgr = self._manager()
        mgr.create_session("s1")
        assert mgr.leave("s1", "ghost") is False

    def test_online_participants_after_close(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.join("s1", "bob")
        mgr.close_session("s1")
        assert mgr.online_participants("s1") == []

    # -------------------------------------------------------- shared state
    def test_set_and_get_state(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        applied, conflict = mgr.set_state("s1", "plan", "v1", writer_id="alice")
        assert applied is True
        assert conflict is None
        assert mgr.get_state("s1", "plan") == "v1"

    def test_set_state_requires_membership(self):
        mgr = self._manager()
        mgr.create_session("s1")
        applied, conflict = mgr.set_state("s1", "plan", "v1", writer_id="mallory")
        assert applied is False

    def test_set_state_closed_session_rejected(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.close_session("s1")
        applied, _ = mgr.set_state("s1", "plan", "v9", writer_id="alice")
        assert applied is False

    def test_state_update_emits_event(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.set_state("s1", "k", 1, writer_id="alice")
        events = mgr.activity_feed("s1")
        types = [e.event_type for e in events]
        assert "state_update" in types

    def test_lww_newer_write_wins(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.join("s1", "bob")
        mgr.set_state("s1", "k", "first", writer_id="alice")
        mgr.set_state("s1", "k", "second", writer_id="bob")
        assert mgr.get_state("s1", "k") == "second"

    def test_concurrent_writes_trigger_conflict_callback(self):
        conflicts = []
        mgr = CollaborationManager(conflict_callbacks=[conflicts.append])
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.join("s1", "bob")
        # Craft a genuinely concurrent write to simulate a racing replica:
        # the new writer's clock has synced bob=5 but never seen carol, while
        # the existing entry was written on carol's replica with stale bob=3.
        # Neither vector dominates the other -> concurrent.
        session = mgr.get_session("s1")
        session.clock.counts["bob"] = 5
        session.state["k"] = StateEntry(
            value="remote",
            writer_id="carol",
            lamport=1,
            clock={"bob": 3, "carol": 2},
        )
        applied, conflict = mgr.set_state("s1", "k", "local", writer_id="alice")
        assert applied is True
        assert conflict is not None
        assert conflict.winner_value == "local"
        assert conflict.loser_value == "remote"
        assert conflicts and conflicts[0].key == "k"

    def test_conflict_callback_exception_isolated(self):
        def bad_callback(event):
            raise RuntimeError("callback boom")

        mgr = CollaborationManager(conflict_callbacks=[bad_callback])
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        session = mgr.get_session("s1")
        session.clock.counts["bob"] = 5
        session.state["k"] = StateEntry(
            value="r", writer_id="carol", lamport=1, clock={"bob": 3, "carol": 2}
        )
        applied, conflict = mgr.set_state("s1", "k", "l", writer_id="alice")
        assert applied is True and conflict is not None  # no raise

    def test_merge_remote_state_takes_higher_lamport(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.set_state("s1", "k", "old", writer_id="alice")
        merged = mgr.merge_remote_state(
            "s1",
            {"k": StateEntry(value="new", writer_id="bob", lamport=999, clock={"bob": 5})},
        )
        assert merged == 1
        assert mgr.get_state("s1", "k") == "new"

    def test_merge_remote_state_keeps_local_if_newer(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.set_state("s1", "k", "local-new", writer_id="alice")
        merged = mgr.merge_remote_state(
            "s1",
            {"k": StateEntry(value="remote-old", writer_id="bob", lamport=0, clock={"bob": 1})},
        )
        assert merged == 0
        assert mgr.get_state("s1", "k") == "local-new"

    def test_merge_remote_state_missing_session(self):
        mgr = self._manager()
        assert mgr.merge_remote_state("nope", {}) == 0

    def test_all_state(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.set_state("s1", "a", 1, writer_id="alice")
        mgr.set_state("s1", "b", 2, writer_id="alice")
        assert mgr.all_state("s1") == {"a": 1, "b": 2}

    # ------------------------------------------------------ vector clock
    def test_vector_clock_tick(self):
        clock = VectorClock()
        snap = clock.tick("alice")
        assert snap == {"alice": 1}
        snap = clock.tick("alice")
        assert snap == {"alice": 2}

    def test_vector_clock_compare_orders(self):
        a = VectorClock({"alice": 1, "bob": 2})
        assert a.compare({"alice": 1, "bob": 2}) == "equal"
        assert a.compare({"alice": 1}) == "after"
        assert a.compare({"alice": 2, "bob": 3}) == "before"
        assert a.compare({"alice": 5, "bob": 1}) == "concurrent"

    def test_vector_clock_update_from(self):
        clock = VectorClock({"alice": 1})
        clock.update_from({"alice": 3, "bob": 1})
        assert clock.snapshot() == {"alice": 3, "bob": 1}

    def test_vector_clock_sequence_monotonic(self):
        clock = VectorClock()
        seq1 = clock.next_seq()
        seq2 = clock.next_seq()
        assert seq2 > seq1

    # ------------------------------------------------------------ events
    def test_event_callback_receives_join(self):
        events = []
        mgr = CollaborationManager(event_callbacks=[events.append])
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        types = [e.event_type for e in events]
        assert "session_created" in types and "join" in types

    def test_event_callback_exception_isolated(self):
        def bad(event):
            raise RuntimeError("boom")

        mgr = CollaborationManager(event_callbacks=[bad])
        mgr.create_session("s1")
        mgr.join("s1", "alice")  # must not raise
        assert mgr.list_participants("s1") == ["alice"]

    def test_activity_feed_order(self):
        mgr = self._manager()
        mgr.create_session("s1")
        mgr.join("s1", "alice")
        mgr.leave("s1", "alice")
        feed = mgr.activity_feed("s1")
        assert [e.event_type for e in feed] == ["session_created", "join", "leave"]

    def test_session_to_dict(self):
        mgr = self._manager()
        mgr.create_session("s1", topic="t")
        data = mgr.get_session("s1").to_dict()
        assert data["session_id"] == "s1"
        assert data["topic"] == "t"
        assert data["closed"] is False


# ===========================================================================
# M4: Performance Optimizer
# ===========================================================================
def _profile_cache_heavy():
    return {
        "functions": {
            "main": {
                "total_ms": 1000.0,
                "self_ms": 50.0,
                "calls": 1,
                "callees": ["fetch_user"],
            },
            "fetch_user": {
                "total_ms": 900.0,
                "self_ms": 300.0,
                "calls": 200,
                "callers": ["main"],
                "io_bound": True,
            },
        }
    }


def _profile_batch_heavy():
    return {
        "functions": {
            "handler": {
                "total_ms": 800.0,
                "self_ms": 100.0,
                "calls": 1,
                "callees": ["db_lookup"],
            },
            "db_lookup": {
                "total_ms": 700.0,
                "self_ms": 200.0,
                "calls": 150,
                "callers": ["handler"],
                "distinct_keys_per_call": 64,
            },
        }
    }


def _profile_parallel_heavy():
    return {
        "functions": {
            "orchestrate": {
                "total_ms": 1000.0,
                "self_ms": 50.0,
                "calls": 1,
                "callees": ["api_a", "api_b", "api_c"],
            },
            "api_a": {"total_ms": 400.0, "self_ms": 300.0, "calls": 1, "io_bound": True},
            "api_b": {"total_ms": 400.0, "self_ms": 300.0, "calls": 1, "io_bound": True},
            "api_c": {"total_ms": 400.0, "self_ms": 300.0, "calls": 1, "io_bound": True},
        }
    }


class TestPerformanceOptimizer:
    # ------------------------------------------------------------- parse
    def test_parse_rejects_empty_profile(self):
        opt = PerformanceOptimizer()
        with pytest.raises(ProfileError):
            opt.analyze({})

    def test_parse_rejects_missing_functions(self):
        opt = PerformanceOptimizer()
        with pytest.raises(ProfileError):
            opt.analyze({"foo": 1})

    def test_parse_rejects_negative_time(self):
        opt = PerformanceOptimizer()
        with pytest.raises(ProfileError):
            opt.analyze({"functions": {"f": {"total_ms": -5, "self_ms": 0, "calls": 1}}})

    def test_parse_rejects_non_numeric(self):
        opt = PerformanceOptimizer()
        with pytest.raises(ProfileError):
            opt.analyze({"functions": {"f": {"total_ms": "abc", "self_ms": 0, "calls": 1}}})

    def test_parse_accepts_alt_field_names(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(
            {
                "functions": {
                    "f": {"total_time_ms": 100.0, "self_time_ms": 50.0, "call_count": 2}
                }
            }
        )
        assert report.total_time_ms == 100.0

    # ----------------------------------------------------------- hotspots
    def test_hotspots_sorted_by_time(self):
        opt = PerformanceOptimizer()
        profile = {
            "functions": {
                "slow": {"total_ms": 900.0, "self_ms": 100.0, "calls": 1},
                "fast": {"total_ms": 100.0, "self_ms": 100.0, "calls": 1},
            }
        }
        assert opt.find_hotspots(profile)[0] == "slow"

    def test_hotspots_cover_fraction(self):
        opt = PerformanceOptimizer(hotspot_fraction=0.8)
        profile = {
            "functions": {
                "a": {"total_ms": 800.0, "self_ms": 800.0, "calls": 1},
                "b": {"total_ms": 100.0, "self_ms": 100.0, "calls": 1},
                "c": {"total_ms": 100.0, "self_ms": 100.0, "calls": 1},
            }
        }
        hotspots = opt.find_hotspots(profile)
        assert hotspots == ["a"]  # 800/1000 = 80% covers threshold

    def test_hotspots_empty_profile_zero_time(self):
        opt = PerformanceOptimizer()
        profile = {"functions": {"a": {"total_ms": 0, "self_ms": 0, "calls": 0}}}
        assert opt.find_hotspots(profile) == []

    # ----------------------------------------------------- recommendations
    def test_cache_recommendation_for_io_heavy(self):
        opt = PerformanceOptimizer()
        recs = opt.recommend(_profile_cache_heavy())
        cache_recs = [r for r in recs if r.kind == "cache"]
        assert cache_recs and cache_recs[0].target == "fetch_user"
        assert cache_recs[0].estimated_speedup > 1.0
        assert cache_recs[0].estimated_time_saved_ms > 0

    def test_batch_recommendation_for_many_small_calls(self):
        opt = PerformanceOptimizer()
        recs = opt.recommend(_profile_batch_heavy())
        batch_recs = [r for r in recs if r.kind == "batch"]
        assert batch_recs and batch_recs[0].target == "db_lookup"
        assert batch_recs[0].details["distinct_keys_per_call"] == 64

    def test_parallel_recommendation_for_io_callees(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(_profile_parallel_heavy())
        par = [r for r in report.recommendations if r.kind == "parallel"]
        assert par and par[0].target == "orchestrate"
        assert len(par[0].details["io_callees"]) == 3

    def test_no_recommendation_for_clean_profile(self):
        opt = PerformanceOptimizer()
        profile = {
            "functions": {
                "compute": {"total_ms": 500.0, "self_ms": 500.0, "calls": 2}
            }
        }
        assert opt.recommend(profile) == []

    def test_recommendations_sorted_by_time_saved(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(_profile_cache_heavy())
        saved = [r.estimated_time_saved_ms for r in report.recommendations]
        assert saved == sorted(saved, reverse=True)

    def test_recommend_top_n(self):
        opt = PerformanceOptimizer()
        profile = {
            "functions": {
                "f1": {"total_ms": 400.0, "self_ms": 100.0, "calls": 100, "io_bound": True},
                "f2": {"total_ms": 400.0, "self_ms": 100.0, "calls": 100, "io_bound": True},
                "f3": {"total_ms": 400.0, "self_ms": 100.0, "calls": 100, "io_bound": True},
                "parent": {"total_ms": 1200.0, "self_ms": 0.0, "calls": 1, "callees": ["f1", "f2", "f3"]},
            }
        }
        assert len(opt.recommend(profile, top_n=2)) == 2

    def test_analyze_returns_report_type(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(_profile_cache_heavy())
        assert isinstance(report, OptimizationReport)
        assert report.notes  # honest note about estimates

    def test_zero_time_profile_report(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(
            {"functions": {"f": {"total_ms": 0.0, "self_ms": 0.0, "calls": 0}}}
        )
        assert report.estimated_total_speedup == 1.0
        assert report.recommendations == []

    def test_cache_invalid_hit_rate_rejected(self):
        with pytest.raises(ValueError):
            PerformanceOptimizer(cache_hit_rate=1.0)

    def test_report_to_dict(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(_profile_cache_heavy())
        data = report.to_dict()
        # total_time_ms is the SUM of all function totals (main + fetch_user)
        assert data["total_time_ms"] == pytest.approx(1900.0)
        assert isinstance(data["recommendations"], list)

    # ------------------------------------------------------- speedup math
    def test_amdahl_speedup_estimate(self):
        opt = PerformanceOptimizer()
        # 50% parallelizable with 4x factor -> 1/(0.5+0.125) = 1.6
        assert opt.estimate_speedup(1000.0, 0.5, 4.0) == pytest.approx(1.6, abs=1e-3)

    def test_amdahl_no_gain_when_factor_1(self):
        opt = PerformanceOptimizer()
        assert opt.estimate_speedup(1000.0, 0.9, 1.0) == 1.0

    def test_total_speedup_at_least_best_single(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(_profile_parallel_heavy())
        if report.recommendations:
            best = max(r.estimated_speedup for r in report.recommendations)
            assert report.estimated_total_speedup >= 1.0

    def test_time_saved_never_exceeds_total(self):
        opt = PerformanceOptimizer()
        report = opt.analyze(_profile_cache_heavy())
        assert report.estimated_total_time_saved_ms <= report.total_time_ms


# ===========================================================================
# M5: Security Hardening
# ===========================================================================
class TestSecurityHardening:
    # ------------------------------------------------------------ helpers
    def test_flatten_nested_paths(self):
        scanner = ConfigHardeningScanner()
        pairs = scanner._iter_paths({"a": {"b": {"c": 1}}})
        assert ("a.b.c", 1) in pairs

    def test_flatten_list_paths(self):
        scanner = ConfigHardeningScanner()
        pairs = scanner._iter_paths({"servers": [{"host": "0.0.0.0"}]})
        assert ("servers[0].host", "0.0.0.0") in pairs

    def test_scan_requires_dict(self):
        scanner = ConfigHardeningScanner()
        with pytest.raises(TypeError):
            scanner.scan(["not", "a", "dict"])

    # ------------------------------------------------------------ timeout
    def test_timeout_zero_flagged(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"http": {"timeout": 0}})
        paths = [f.path for f in report.findings]
        assert "http.timeout" in paths
        assert any(f.risk == "high" for f in report.findings)

    def test_timeout_zero_suggested_value(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"timeout": 0})
        finding = report.findings[0]
        assert finding.suggested_value == 30

    def test_normal_timeout_not_flagged(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"timeout": 30})
        assert report.findings == []

    def test_small_timeout_low_risk(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"timeout": 0.1})
        assert report.findings[0].risk == "low"

    def test_timeout_field_name_variants(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"connect_timeout": 0, "read_timeout": 0})
        assert len(report.findings) == 2

    # ------------------------------------------------------------- retries
    def test_infinite_retry_flagged_critical(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"client": {"retries": -1}})
        assert report.findings[0].risk == "critical"

    def test_high_retry_count_medium(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"max_attempts": 100})
        assert report.findings[0].risk == "medium"

    def test_reasonable_retry_not_flagged(self):
        scanner = ConfigHardeningScanner()
        assert scanner.scan({"retries": 3}).findings == []

    # ----------------------------------------------------------- log leaks
    def test_log_format_password_pattern(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"logging": {"format": "%(password)s %(message)s"}})
        assert any(f.risk == "high" for f in report.findings)
        assert any("password" in f.issue for f in report.findings)

    def test_log_message_api_key_pattern(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"log_message": "user api_key=abc123 sent"})
        assert any(f.risk == "high" for f in report.findings)

    def test_log_bearer_token_pattern(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"log_format": "Bearer sk-12345 done"})
        assert any(f.risk == "high" for f in report.findings)

    def test_clean_log_not_flagged(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"logging": {"format": "%(asctime)s %(levelname)s %(message)s"}})
        assert report.findings == []

    def test_non_string_log_field_ignored(self):
        scanner = ConfigHardeningScanner()
        assert scanner.scan({"logging": {"format": 42}}).findings == []

    # --------------------------------------------------------- bool flags
    def test_debug_true_flagged(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"debug": True})
        assert report.findings[0].risk == "medium"

    def test_insecure_true_high(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"insecure": True})
        assert report.findings[0].risk == "high"

    def test_verify_ssl_false_critical(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"http": {"verify_ssl": False}})
        assert report.findings[0].risk == "critical"

    def test_verify_ssl_true_not_flagged(self):
        scanner = ConfigHardeningScanner()
        assert scanner.scan({"verify_ssl": True}).findings == []

    # --------------------------------------------------------------- bind
    def test_bind_all_interfaces_flagged(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"server": {"host": "0.0.0.0"}})
        assert report.findings[0].risk == "medium"

    def test_localhost_not_flagged(self):
        scanner = ConfigHardeningScanner()
        assert scanner.scan({"server": {"host": "127.0.0.1"}}).findings == []

    # ------------------------------------------------------------- scoring
    def test_risk_score_zero_clean_config(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"timeout": 30, "retries": 3})
        assert report.risk_score == 0.0
        assert report.overall_risk == "low"

    def test_risk_score_ordering(self):
        scanner = ConfigHardeningScanner()
        clean = scanner.scan({"timeout": 30})
        bad = scanner.scan({"timeout": 0, "retries": -1, "verify_ssl": False})
        assert bad.risk_score > clean.risk_score

    def test_risk_score_cap_100(self):
        scanner = ConfigHardeningScanner()
        config = {f"client{i}": {"retries": -1} for i in range(10)}
        report = scanner.scan(config)
        assert report.risk_score == 100.0

    def test_summary_counts(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"timeout": 0, "retries": -1})
        assert report.summary.get("high") == 1
        assert report.summary.get("critical") == 1

    def test_overall_risk_bands(self):
        scanner = ConfigHardeningScanner()
        assert scanner.overall_risk(0.0, 0) == "low"
        assert scanner.overall_risk(15.0, 1) == "medium"
        assert scanner.overall_risk(40.0, 2) == "high"
        assert scanner.overall_risk(70.0, 3) == "critical"

    def test_recommendations_sorted_by_severity(self):
        scanner = ConfigHardeningScanner()
        recs = scanner.recommendations({"timeout": 0, "retries": -1, "verify_ssl": False})
        assert len(recs) == 3
        # critical findings first
        assert "cap retries" in recs[0].lower()
        assert "verify" in recs[1].lower()

    def test_report_to_dict(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"timeout": 0})
        data = report.to_dict()
        assert data["scanned_paths"] == 1
        assert isinstance(data["findings"], list)

    def test_finding_to_dict(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan({"timeout": 0})
        data = report.findings[0].to_dict()
        assert data["path"] == "timeout"
        assert data["risk"] == "high"

    def test_risk_level_helpers(self):
        assert RiskLevel.is_valid("high") is True
        assert RiskLevel.is_valid("extreme") is False
        assert RiskLevel.order("critical") > RiskLevel.order("low")

    def test_nested_config_scan(self):
        scanner = ConfigHardeningScanner()
        report = scanner.scan(
            {
                "services": {
                    "api": {"timeout": 0, "retries": -1},
                    "worker": {"timeout": 5},
                }
            }
        )
        paths = [f.path for f in report.findings]
        assert "services.api.timeout" in paths
        assert "services.api.retries" in paths


# ===========================================================================
# Integration across M2-M5
# ===========================================================================
class TestV23Integration:
    def test_federated_round_then_collab_share(self):
        """Federated round output is shared into a collab session state."""
        orch = FederatedOrchestrator(
            nodes=[FederatedNode(node_id="a"), FederatedNode(node_id="b")]
        )
        result = orch.run_round(
            lambda nid, gw: NodeUpdate(
                node_id=nid, round_id=1, weights={"w": 2.0}, knowledge_updates=["k1"]
            )
        )
        mgr = CollaborationManager()
        mgr.create_session("s1")
        mgr.join("s1", "aggregator")
        applied, conflict = mgr.set_state(
            "s1", "global_weights", result.aggregated_weights, writer_id="aggregator"
        )
        assert applied and conflict is None
        assert mgr.get_state("s1", "global_weights") == {"w": 2.0}

    def test_dp_protected_weights_shared(self):
        """DP-noised weights flow into collab state; conflict recorded on race."""
        dp = DifferentialPrivacy(epsilon=1.0, seed=3, max_budget=100.0)
        orch = FederatedOrchestrator(
            nodes=[FederatedNode(node_id="a"), FederatedNode(node_id="b")], dp=dp
        )
        result = orch.run_round(
            lambda nid, gw: NodeUpdate(node_id=nid, round_id=1, weights={"w": 1.0})
        )
        mgr = CollaborationManager()
        mgr.create_session("s1")
        mgr.join("s1", "n1")
        mgr.join("s1", "n2")
        mgr.set_state("s1", "model", 0.0, writer_id="n1")
        # Craft a genuinely concurrent write (racing replica with divergent
        # vector clock: alice's fresh tick never saw carol's counter).
        session = mgr.get_session("s1")
        session.clock.counts["carol"] = 4
        session.state["model"] = StateEntry(
            value="other", writer_id="carol", lamport=1, clock={"carol": 2, "n2": 3}
        )
        applied, conflict = mgr.set_state(
            "s1", "model", result.aggregated_weights, writer_id="n1"
        )
        assert applied and conflict is not None
        # DP budget was spent for one key
        assert dp.epsilon_spent == pytest.approx(1.0)

    def test_optimizer_consumes_federated_profile(self):
        """Optimizer analyzes a profile shaped like a federated training loop."""
        opt = PerformanceOptimizer()
        profile = {
            "functions": {
                "federated_round": {
                    "total_ms": 1000.0,
                    "self_ms": 100.0,
                    "calls": 1,
                    "callees": ["node_train", "node_train2"],
                },
                "node_train": {
                    "total_ms": 400.0,
                    "self_ms": 300.0,
                    "calls": 20,
                    "io_bound": True,
                },
                "node_train2": {
                    "total_ms": 400.0,
                    "self_ms": 300.0,
                    "calls": 20,
                    "io_bound": True,
                },
            }
        }
        report = opt.analyze(profile)
        kinds = {r.kind for r in report.recommendations}
        assert "parallel" in kinds

    def test_hardening_scans_federated_config(self):
        """Hardening scanner flags a bad federated orchestrator config."""
        scanner = ConfigHardeningScanner()
        config = {
            "federated": {
                "round_timeout": 0,
                "max_retries": -1,
                "logging": {"format": "token=%(token)s"},
            }
        }
        report = scanner.scan(config)
        paths = [f.path for f in report.findings]
        assert "federated.round_timeout" in paths
        assert "federated.max_retries" in paths
        assert any("token" in f.issue for f in report.findings)
        assert report.overall_risk in ("high", "critical")

    def test_full_pipeline_round_trip(self):
        """All four modules in one simulated pipeline."""
        # M2 federated
        orch = FederatedOrchestrator(
            nodes=[FederatedNode(node_id=f"n{i}") for i in range(3)]
        )
        round_result = orch.run_round(
            lambda nid, gw: NodeUpdate(
                node_id=nid, round_id=1, weights={"w": 1.5}, loss=0.4
            )
        )
        # M3 share result
        mgr = CollaborationManager()
        mgr.create_session("pipeline")
        mgr.join("pipeline", "orchestrator")
        mgr.set_state("pipeline", "v", round_result.global_model_version, "orchestrator")
        # M4 optimize
        opt = PerformanceOptimizer()
        report = opt.analyze(
            {
                "functions": {
                    "agg": {"total_ms": 100.0, "self_ms": 100.0, "calls": 1}
                }
            }
        )
        # M5 harden the config used
        scanner = ConfigHardeningScanner()
        sec_report = scanner.scan({"round_timeout": 30, "max_retries": 3})
        assert mgr.get_state("pipeline", "v") == 1
        assert report.total_time_ms == 100.0
        assert sec_report.overall_risk == "low"
        assert round_result.global_model_version == 1
