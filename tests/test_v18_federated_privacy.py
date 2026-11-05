"""V18 tests — Federated Learning & Privacy-Preserving Memory (20 tests)."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from quan_ai_brain.learning.federated_learning import (
    FederatedAggregator, FederatedNode, ModelUpdate, TrainingSession,
    DifferentialPrivacy
)
from quan_ai_brain.memory.privacy_preserving import (
    DifferentialPrivacyMechanism, KAnonymity, LDiversity,
    SecureComputation, PrivacyCompliance
)


@pytest.fixture
def federated_db():
    """Create temporary federated learning database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_v18_federated.db"


@pytest.fixture
def privacy_db():
    """Create temporary privacy database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_v18_privacy.db"


class TestFederatedAggregator:
    """Tests for federated learning aggregator."""
    
    def test_register_node(self, federated_db):
        """Register federated node."""
        aggregator = FederatedAggregator(str(federated_db))
        node = FederatedNode(
            node_id="client1",
            role="client",
            capabilities=["training", "inference"]
        )
        result = aggregator.register_node(node)
        assert result is True
        
        clients = aggregator.get_active_clients()
        assert len(clients) == 1
        assert clients[0].node_id == "client1"
        aggregator.close()
    
    def test_start_training(self, federated_db):
        """Start federated training session."""
        aggregator = FederatedAggregator(str(federated_db))
        session = aggregator.start_training(rounds=10, clients_per_round=3)
        
        assert session.rounds == 10
        assert session.clients_per_round == 3
        assert session.current_round == 0
        aggregator.close()
    
    def test_local_train(self, federated_db):
        """Simulate local training."""
        aggregator = FederatedAggregator(str(federated_db))
        aggregator.register_node(FederatedNode("client1", "client", []))
        
        model = {"weight1": 0.5, "weight2": 0.3}
        update = aggregator.local_train("client1", model, epochs=5)
        
        assert update.node_id == "client1"
        assert update.model_version == 0
        assert update.loss is not None
        assert update.accuracy is not None
        aggregator.close()
    
    def test_fedavg_aggregate(self, federated_db):
        """Test FedAvg aggregation."""
        aggregator = FederatedAggregator(str(federated_db))
        
        updates = [
            ModelUpdate("u1", "client1", 0, {"w1": 0.5, "w2": 0.3}, None, 0.4, 0.85, 100),
            ModelUpdate("u2", "client2", 0, {"w1": 0.6, "w2": 0.4}, None, 0.3, 0.90, 200)
        ]
        
        aggregated = aggregator.aggregate_updates(updates, strategy='fedavg')
        
        # Weighted average: client1 (100/300), client2 (200/300)
        assert abs(aggregated["w1"] - 0.567) < 0.01  # (0.5*100 + 0.6*200) / 300
        aggregator.close()
    
    def test_distribute_model(self, federated_db):
        """Distribute global model to nodes."""
        aggregator = FederatedAggregator(str(federated_db))
        aggregator.register_node(FederatedNode("client1", "client", []))
        aggregator.register_node(FederatedNode("client2", "client", []))

        result = aggregator.distribute_global_model(["client1", "client2"])
        assert result is True

        # Sau distribute: last_sync cập nhật mới → không ai là straggler
        stragglers_after = aggregator.handle_stragglers(["client1", "client2"], timeout=300)
        assert stragglers_after == []

        # Giả lập node nghẽn: đẩy last_sync lùi 400s > timeout 300
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
        aggregator._conn.execute(
            "UPDATE federated_nodes SET last_sync = ? WHERE node_id = 'client1'", (old,))
        aggregator._conn.commit()
        stragglers = aggregator.handle_stragglers(["client1", "client2"], timeout=300)
        assert stragglers == ["client1"]
        aggregator.close()
    
    def test_evaluate_model(self, federated_db):
        """Evaluate global model."""
        aggregator = FederatedAggregator(str(federated_db))
        aggregator.register_node(FederatedNode("client1", "client", []))
        aggregator.register_node(FederatedNode("client2", "client", []))
        
        eval_result = aggregator.evaluate_global_model(["client1", "client2"])
        
        assert 'evaluations' in eval_result
        assert 'avg_loss' in eval_result
        assert 'avg_accuracy' in eval_result
        aggregator.close()
    
    def test_check_convergence(self, federated_db):
        """Check training convergence."""
        aggregator = FederatedAggregator(str(federated_db))

        # Loss dao động lớn → chưa hội tụ
        assert aggregator.check_convergence([1.0, 0.8, 0.95, 0.7], threshold=0.01) is False
        # Loss ổn định dưới ngưỡng → hội tụ
        assert aggregator.check_convergence([0.50, 0.498, 0.499, 0.4985], threshold=0.01) is True
        # Lịch sử quá ngắn (<2) → không kết luận được hội tụ
        assert aggregator.check_convergence([0.5], threshold=0.01) is False
        aggregator.close()
    
    def test_detect_poisoning(self, federated_db):
        """Detect poisoned updates."""
        aggregator = FederatedAggregator(str(federated_db))

        # <3 updates: thuật toán từ chối kết luận (tránh false positive)
        small = [
            ModelUpdate("u1", "client1", 0, {"w1": 0.5}, None, 0.4, 0.85, 100),
            ModelUpdate("u2", "client2", 0, {"w1": 0.6}, None, 0.5, 0.80, 100),
        ]
        assert aggregator.detect_poisoning(small) == []

        # 4 updates bình thường + 1 outlier loss cực lớn → bị phát hiện
        normal = [
            ModelUpdate(f"u{i}", f"client{i}", 0, {"w1": 0.5}, None, 0.40 + 0.01 * i, 0.85, 100)
            for i in range(1, 5)
        ]
        poison = ModelUpdate("u9", "bad_client", 0, {"w1": 99.0}, None, 50.0, 0.05, 100)
        flagged = aggregator.detect_poisoning(normal + [poison])
        assert "bad_client" in flagged
        assert all(f"client{i}" not in flagged for i in range(1, 5))
        aggregator.close()


class TestDifferentialPrivacy:
    """Tests for differential privacy."""
    
    def test_add_laplace_noise(self, federated_db):
        """Add Laplace noise."""
        dp = DifferentialPrivacy(epsilon=1.0)

        # Nhiễu phải thay đổi giá trị (xác suất gần 1 với scale đủ lớn)
        noisy = [dp.add_laplace_noise(100.0, sensitivity=10.0) for _ in range(50)]
        assert any(abs(n - 100.0) > 1e-9 for n in noisy)
        # Noise trung bình gần 0 (Laplace đối xứng, 50 mẫu, tol rộng)
        mean_shift = sum(n - 100.0 for n in noisy) / len(noisy)
        assert abs(mean_shift) < 10.0
        # Epsilon nhỏ → nhiễu mạnh hơn (độ phân tán tăng)
        dp_strong = DifferentialPrivacy(epsilon=0.1)
        spread_strong = max(abs(dp_strong.add_laplace_noise(0.0, 10.0)) for _ in range(200))
        spread_weak = max(abs(dp.add_laplace_noise(0.0, 10.0)) for _ in range(200))
        assert spread_strong >= spread_weak
    
    def test_add_gaussian_noise(self, federated_db):
        """Add Gaussian noise."""
        dp = DifferentialPrivacy(epsilon=1.0, delta=1e-5)

        # Bug-fix verification: noise PHẢI được cộng vào giá trị (trước đây
        # code trả về value + value — nhiễu Gaussian không bao giờ được áp dụng)
        noisy = [dp.add_gaussian_noise(100.0, sensitivity=5.0) for _ in range(50)]
        assert any(abs(n - 100.0) > 1e-9 for n in noisy)
        # Gaussian đối xứng → trung bình gần giá trị gốc
        mean_shift = sum(n - 100.0 for n in noisy) / len(noisy)
        assert abs(mean_shift) < 10.0
        # Giá trị không âm đi quá xa về phía âm (sigma nhỏ với sensitivity 5)
        assert all(n > 90.0 - 5 * 20 for n in noisy)
    
    def test_clip_gradients(self, federated_db):
        """Clip gradients."""
        dp = DifferentialPrivacy()

        grads = {"w1": 3.0, "w2": 4.0}  # norm = 5.0
        clipped = dp.clip_gradients(grads, max_norm=2.5)
        norm_after = sum(g ** 2 for g in clipped.values()) ** 0.5
        assert abs(norm_after - 2.5) < 1e-9
        # Tỉ lệ giữ nguyên hướng (3/4 = 1.5/2.0)
        assert abs(clipped["w1"] - 1.5) < 1e-9
        assert abs(clipped["w2"] - 2.0) < 1e-9
        # Norm nhỏ hơn max_norm → giữ nguyên
        unchanged = dp.clip_gradients({"w1": 0.1}, max_norm=2.5)
        assert unchanged["w1"] == 0.1
    
    def test_track_privacy_budget(self, federated_db):
        """Track privacy budget."""
        dp = DifferentialPrivacy(epsilon=1.0)

        dp.track_privacy_budget(0.3)
        dp.track_privacy_budget(0.2)
        assert abs(dp.privacy_budget_used - 0.5) < 1e-9
        assert abs(dp.remaining_budget() - 0.5) < 1e-9
        assert len(dp.operations) == 2
        # Vượt budget → remaining không âm (floor 0)
        dp.track_privacy_budget(0.9)
        assert dp.remaining_budget() == 0.0
        # Report đầy đủ trường
        report = dp.privacy_report()
        assert report["used"] == pytest.approx(1.4)
        assert report["remaining"] == 0.0
        assert len(report["operations"]) == 3


class TestKAnonymity:
    """Tests for k-anonymity."""
    
    def test_generalize_data(self, privacy_db):
        """Generalize data for k-anonymity."""
        k_anon = KAnonymity(k=3)
        
        data = [
            {"age": 25, "location": "Hanoi"},
            {"age": 30, "location": "Hanoi"},
            {"age": 35, "location": "Hanoi"},
            {"age": 40, "location": "HCMC"}
        ]
        
        rules = {"age": 1, "location": 1}
        anonymized = k_anon.generalize(data, rules)
        
        assert len(anonymized) >= 0  # Some may be suppressed
        assert all(r.k_value >= 3 for r in anonymized)
    
    def test_check_k_anonymity(self, privacy_db):
        """Check k-anonymity satisfaction."""
        k_anon = KAnonymity(k=3)

        # 4 bản ghi cùng nhóm quasi-identifier (k=3 thỏa)
        safe = [
            {"age": "20-40", "location": "Hanoi"},
            {"age": "20-40", "location": "Hanoi"},
            {"age": "20-40", "location": "Hanoi"},
            {"age": "20-40", "location": "Hanoi"},
        ]
        assert k_anon.check_k_anonymity(safe, ["age", "location"]) is True

        # Mỗi nhóm chỉ 1 bản ghi → vi phạm k=3
        unsafe = [
            {"age": 25, "location": "Hanoi"},
            {"age": 30, "location": "HCMC"},
            {"age": 35, "location": "Danang"},
        ]
        assert k_anon.check_k_anonymity(unsafe, ["age", "location"]) is False


class TestLDiversity:
    """Tests for l-diversity."""
    
    def test_check_l_diversity(self, privacy_db):
        """Check l-diversity satisfaction."""
        l_div = LDiversity(l=2)

        # Mỗi nhóm có >=2 giá trị sensitive khác nhau → thỏa
        safe = [
            {"location": "Hanoi", "diagnosis": "A"},
            {"location": "Hanoi", "diagnosis": "B"},
            {"location": "Hanoi", "diagnosis": "A"},
            {"location": "HCMC", "diagnosis": "B"},
            {"location": "HCMC", "diagnosis": "A"},
        ]
        assert l_div.check_l_diversity(safe, ["location"], "diagnosis") is True

        # Nhóm Hanoi chỉ có 1 giá trị sensitive → vi phạm l=2
        unsafe = [
            {"location": "Hanoi", "diagnosis": "A"},
            {"location": "Hanoi", "diagnosis": "A"},
            {"location": "Hanoi", "diagnosis": "A"},
        ]
        assert l_div.check_l_diversity(unsafe, ["location"], "diagnosis") is False


class TestSecureComputation:
    """Tests for secure computation."""
    
    def test_secure_sum(self, privacy_db):
        """Test secure sum."""
        secure = SecureComputation(mod=2**64)
        
        values = [10, 20, 30, 40]
        result = secure.secure_sum(values)
        
        assert result == 100
        assert result < 2**64
    
    def test_secure_average(self, privacy_db):
        """Test secure average."""
        secure = SecureComputation(mod=2**64)
        
        values = [10, 20, 30, 40]
        result = secure.secure_average(values, 4)
        
        assert result == 25.0
    
    def test_secure_comparison(self, privacy_db):
        """Test secure comparison."""
        secure = SecureComputation()
        
        result = secure.secure_comparison(10, 20)
        assert result is True  # 10 < 20
        
        result = secure.secure_comparison(30, 20)
        assert result is False  # 30 > 20


class TestPrivacyCompliance:
    """Tests for privacy compliance."""
    
    def test_audit_gdpr(self, privacy_db):
        """Audit GDPR compliance."""
        compliance = PrivacyCompliance(str(privacy_db))
        
        audit = compliance.audit_compliance(['GDPR'])
        
        assert 'GDPR' in audit
        assert 'compliant' in audit['GDPR']
        assert 'checks' in audit['GDPR']
        compliance.close()
    
    def test_audit_ccpa(self, privacy_db):
        """Audit CCPA compliance."""
        compliance = PrivacyCompliance(str(privacy_db))
        
        audit = compliance.audit_compliance(['CCPA'])
        
        assert 'CCPA' in audit
        assert 'compliant' in audit['CCPA']
        compliance.close()
    
    def test_right_to_be_forgotten(self, privacy_db):
        """Test right to be forgotten."""
        compliance = PrivacyCompliance(str(privacy_db))
        
        # Add some data first
        compliance._conn.execute(
            "INSERT INTO data_retention (record_id, user_id, created_at, expires_at, status) VALUES (?, ?, ?, ?, ?)",
            ("rec1", "user1", "2024-01-01", "2025-01-01", "active")
        )
        compliance._conn.commit()
        
        # Delete user data
        result = compliance.right_to_be_forgotten("user1")
        assert result is True
        
        # Verify deletion
        count = compliance._conn.execute(
            "SELECT COUNT(*) FROM data_retention WHERE user_id = 'user1'"
        ).fetchone()[0]
        assert count == 0
        compliance.close()
    
    def test_export_user_data(self, privacy_db):
        """Test data portability."""
        compliance = PrivacyCompliance(str(privacy_db))
        
        # Add data
        compliance._conn.execute(
            "INSERT INTO data_retention (record_id, user_id, created_at, expires_at, status) VALUES (?, ?, ?, ?, ?)",
            ("rec1", "user1", "2024-01-01", "2025-01-01", "active")
        )
        compliance._conn.commit()
        
        # Export
        exported = compliance.export_user_data("user1")
        
        assert exported['user_id'] == "user1"
        assert len(exported['records']) >= 1
        compliance.close()
    
    def test_generate_privacy_report(self, privacy_db):
        """Generate privacy report."""
        compliance = PrivacyCompliance(str(privacy_db))
        
        report = compliance.generate_privacy_report()
        
        assert 'generated_at' in report
        assert 'compliance_audit' in report
        assert 'retention_stats' in report
        assert 'consent_stats' in report
        compliance.close()