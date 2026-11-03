"""DEOM M2 — tests Natural Language Task Intake (tiếng Việt, deterministic)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.nl_intake import detect_priority, intake_task, parse_vn_deadline
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def registry() -> DurableTaskRegistry:
    return DurableTaskRegistry(":memory:")


NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestPriority:
    def test_khan_cap(self):
        assert detect_priority("KHẨN CẤP: server chết") == 1

    def test_gap(self):
        assert detect_priority("gấp kiểm tra hộ anh báo cáo") == 2

    def test_khoi_ranh(self):
        assert detect_priority("khi rảnh anh mới xem cái này") == 5

    def test_long_running_low(self):
        assert detect_priority("em theo dõi giúp anh dung lượng pin") == 4

    def test_default_normal(self):
        assert detect_priority("tổng hợp báo cáo tuần") == 3


class TestDeadline:
    def test_truoc_gio_chieu(self):
        # NOW = 01/11 12:00 UTC = 19:00 VN — "trước 5 chiều" (17:00 VN) đã qua → 17:00 mai VN
        # = 02/11 10:00 UTC
        iso = parse_vn_deadline("xong trước 5 chiều nhé", now=NOW)
        assert iso is not None
        assert "T10:00" in iso and "-11-02" in iso

    def test_sang_9h_local(self):
        # "trước 9h sáng" = 09:00 VN = 02:00 UTC; NOW 12:00 UTC → qua rồi → mai
        iso = parse_vn_deadline("trước 9 sáng nhé", now=NOW)
        assert iso is not None
        assert "T02:00" in iso and "-11-02" in iso

    def test_trong_3_ngay(self):
        iso = parse_vn_deadline("hoàn thành trong 3 ngày", now=NOW)
        assert iso is not None
        # 01/11 + 3 ngày = 04/11
        assert "-11-04" in iso

    def test_den_khi_hoan_thanh(self):
        iso = parse_vn_deadline("theo dõi đến khi hoàn thành")
        assert iso is None

    def test_khong_doan_mao(self):
        assert parse_vn_deadline("kiểm tra giúp anh") is None

    def test_gio_da_qua_chuyen_mai(self):
        iso = parse_vn_deadline("trước 7 sáng nhé", now=NOW)  # 07:00 < 12:00
        assert "-11-02" in iso  # hiểu là mai


class TestIntake:
    def test_full_sentence(self, registry):
        res = intake_task(registry, "Gấp: kiểm tra server 8765 chết chưa, trước 5 chiều")
        assert res.priority == 2
        assert res.deadline_utc is not None
        assert res.initial_status == TaskStatus.RECEIVED
        assert res.meta["task_id"].startswith("task_")
        rec = registry.get_task(res.meta["task_id"])
        assert rec is not None
        assert rec.status == TaskStatus.RECEIVED
        assert rec.source == "owner"

    def test_theo_doi_dai_han(self, registry):
        res = intake_task(registry, "em theo dõi giúp anh pin Pi5 đến khi hoàn thành")
        assert res.priority == 4
        assert res.deadline_utc is None

    def test_empty_rejected(self, registry):
        with pytest.raises(ValueError):
            intake_task(registry, "   ")
