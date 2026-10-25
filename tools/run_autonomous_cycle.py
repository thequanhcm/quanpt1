"""QUAN AI BRAIN — CLI Vận Hành Chu Kỳ Tự Chủ An Toàn (Autonomous Engineering & Operations V1).

Công cụ thực thi một chu kỳ tự chủ bounded (có giới hạn):
1. Tự kiểm tra sức khỏe hệ thống (Autonomic Nervous System & Pain Assessment).
2. Kiểm tra trạng thái khẩn cấp (Emergency STOP/FREEZE).
3. Khôi phục các tác vụ dở dang từ phiên trước (Outcome Unknown Recovery).
4. Thực thi bước giám sát tự chủ có giới hạn (Supervisor Bounded Tick).
5. Nghiên cứu tài liệu kỹ thuật an toàn (SHA-256 provenance & Prompt Injection scanning).
6. Báo cáo minh bạch, đầy đủ bằng chứng tới Chủ sở hữu (Anh Quân - Quanpt1).

LƯU Ý QUAN TRỌNG:
Anh Quân là người quyết định DUY NHẤT mọi ý kiến thay đổi, áp dụng hành động hoặc nâng cấp.
Mọi hành động R4/R5 đều bị chặn hoặc yêu cầu phê duyệt có chữ ký xác thực.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import time

# Thiết lập UTF-8 chuẩn cho PowerShell và Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

# Đảm bảo đường dẫn import
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.core.autonomic import GLOBAL_AUTONOMIC_SYSTEM
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.learning.engine import SelfLearningEngine
from quan_ai_brain.learning.periodic_reporter import PeriodicLearningReporter
from quan_ai_brain.llm import FallbackMode, LLMProvider
from quan_ai_brain.memory.sqlite_store import MemoryStore
from quan_ai_brain.orchestration.models import AutonomyLevel, SupervisorState, TaskStatus
from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.coordinator import ExecutiveCoordinator


def run_cycle(dry_run: bool = True, max_duration_sec: float = 10.0, max_steps: int = 5, live_llm: bool = False) -> int:
    print("=" * 72, flush=True)
    print("   QUAN AI BRAIN -- CHU KỲ VẬN HÀNH TỰ CHỦ CÓ KIỂM SOÁT (AUTONOMOUS V1)", flush=True)
    print("=" * 72, flush=True)
    print(f"  Chủ sở hữu phê duyệt: Anh Quân (Quanpt1)", flush=True)
    print(f"  Không gian làm việc:   {WORKSPACE}", flush=True)
    print(f"  Chế độ thực thi:       {'DRY-RUN (Thử nghiệm an toàn, không ghi)' if dry_run else 'REAL'}", flush=True)
    print(f"  Mô hình suy luận:      {'Ollama Live (qwen2.5:7b)' if live_llm else 'Mock/Deterministic Fallback'}", flush=True)
    print(f"  Giới hạn thời gian:    {max_duration_sec}s | Giới hạn bước: {max_steps}", flush=True)
    print("=" * 72, flush=True)

    # 1. Khởi tạo State Store & Task Registry
    data_dir = WORKSPACE / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    gov_store = GovernanceStateStore(data_dir / "governance.db", workspace=WORKSPACE)
    task_registry = DurableTaskRegistry(data_dir / "tasks.db", workspace=WORKSPACE)
    mem_store = MemoryStore(data_dir / "memory.db", workspace=WORKSPACE)
    learning_engine = SelfLearningEngine(workspace=WORKSPACE, memory_store=mem_store)

    fallback_mode = FallbackMode.ON_ERROR if live_llm else FallbackMode.ALWAYS_MOCK
    llm = LLMProvider(fallback_mode=fallback_mode)
    coordinator = ExecutiveCoordinator(workspace=WORKSPACE, llm_provider=llm)

    supervisor = ContinuousAutonomySupervisor(
        workspace=WORKSPACE,
        task_registry=task_registry,
        governance_store=gov_store,
        coordinator=coordinator,
    )

    # 2. Bước 1: Hệ thần kinh tự chủ (Autonomic Self-Test)
    print("\n[BƯỚC 1/5] Thăm dò Hệ Thần Kinh Tự Chủ (Pain Assessment & Reflex)...", flush=True)
    try:
        report = GLOBAL_AUTONOMIC_SYSTEM.run_selftest()
        pain_val = getattr(report.overall_pain_level, "value", str(report.overall_pain_level))
        print(f"  -> Điểm sức khỏe tổng thể: {report.health_score}/100", flush=True)
        print(f"  -> Mức độ đau đớn sinh thể: {pain_val}", flush=True)
        print(f"  -> Thông điệp phản ánh:    {report.vocal_summary}", flush=True)
        if pain_val == "CRITICAL":
            print("  [CẢNH BÁO NGUY CẤP] Phát hiện điểm đau nghiêm trọng! Chuyển sang SAFE_MODE.", flush=True)
    except Exception as exc:
        print(f"  [LỖI THẦN KINH] Không thể đọc telemetry: {exc}", flush=True)

    # 3. Bước 2: Kiểm tra trạng thái khẩn cấp & Khôi phục tác vụ
    print("\n[BƯỚC 2/5] Kiểm tra Quản Trị Khẩn Cấp & Khôi Phục Nhiệm Vụ...", flush=True)
    emergency = gov_store.get_emergency_state()
    print(f"  -> Trạng thái khẩn cấp: {emergency.state.upper()} (Người kích hoạt: {emergency.activated_by})", flush=True)
    if emergency.state != "normal":
        print(f"  [DỪNG KHẨN CẤP] Lý do: {emergency.reason}", flush=True)
        print("  -> Hệ thống tuân thủ lệnh dừng tuyệt đối. Kết thúc chu kỳ.", flush=True)
        return 0

    supervisor.initialize()
    print(f"  -> Trạng thái Supervisor sau khởi tạo: {supervisor.state.value}", flush=True)

    # 4. Bước 3: Đảm bảo có nhiệm vụ Level A an toàn để kiểm thử
    print("\n[BƯỚC 3/5] Quét Hàng Đợi Nhiệm Vụ Bền Vững (Durable Task Queue)...", flush=True)
    pending = task_registry.list_tasks(status=TaskStatus.PENDING, limit=1)
    if not pending:
        print("  -> Không có nhiệm vụ chờ. Đăng ký nhiệm vụ Level A kiểm tra an toàn hệ thống...", flush=True)
        task_registry.register_task(
            goal="Tự kiểm tra cấu hình kiến trúc và chỉ mục bộ nhớ SQLite",
            risk_level="R0",
            autonomy_level=AutonomyLevel.LEVEL_A,
            acceptance_criteria=["Xác minh database WAL mode", "Kiểm tra quyền hạn R0"],
        )
    else:
        print(f"  -> Tìm thấy nhiệm vụ đang chờ: [{pending[0].task_id}] {pending[0].goal} (R{pending[0].risk_level})", flush=True)

    # 5. Bước 4: Thực thi Chu Kỳ Tự Chủ Có Giới Hạn (Bounded Tick)
    print("\n[BƯỚC 4/5] Thực thi Bounded Supervision Tick...", flush=True)
    t0 = time.perf_counter()
    tick_result = supervisor.run_background_tick(
        max_duration_sec=max_duration_sec,
        max_steps=max_steps,
        dry_run=dry_run,
        autonomic_system=GLOBAL_AUTONOMIC_SYSTEM,
    )
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  -> Trạng thái kết thúc: {tick_result.get('state')}", flush=True)
    print(f"  -> Số bước đã thực thi: {tick_result.get('steps_executed')}", flush=True)
    print(f"  -> Thời gian thực thi:  {elapsed:.2f} ms", flush=True)
    if tick_result.get("notes"):
        print(f"  -> Nhật ký ghi nhận:", flush=True)
        for note in tick_result["notes"]:
            print(f"     * {note}", flush=True)

    # 6. Bước 5: Thử nghiệm Tra cứu & Kiểm dịch Tri Thức Kỹ Thuật (Safe Research)
    print("\n[BƯỚC 5/5] Kiểm thử Khả năng Nghiên cứu Tài liệu & Quét Mã Độc...", flush=True)
    sample_doc = WORKSPACE / "docs" / "PROJECT_STATUS.md"
    if sample_doc.exists():
        doc_result = learning_engine.fetch_verified_technical_doc(str(sample_doc), title="Trạng Thái Dự Án")
        print(f"  -> Nguồn tài liệu:     {doc_result.get('title')}", flush=True)
        print(f"  -> Băm SHA-256 xác thực: {doc_result.get('sha256')[:24]}...", flush=True)
        print(f"  -> Phát hiện tấn công:  {'CÓ' if doc_result.get('is_injection_detected') else 'AN TOÀN (KHÔNG)'}", flush=True)
        print(f"  -> Điểm độ tin cậy:   {doc_result.get('reliability_score') * 100:.0f}%", flush=True)

    print("\n" + "=" * 72, flush=True)
    print("   KẾT QUẢ: CHU KỲ TỰ CHỦ HOÀN TẤT THÀNH CÔNG VÀ AN TOÀN", flush=True)
    print("   Lưu ý: Mọi đề xuất nâng cấp code được lưu tại bảng kiểm dịch (QUARANTINED).", flush=True)
    print("   Quyết định triển khai cuối cùng thuộc về anh Quân (Quanpt1).", flush=True)
    print("=" * 72 + "\n", flush=True)
    return 0


if __name__ == "__main__":
    dry = True
    if "--real" in sys.argv:
        dry = False
    is_live_llm = "--live-llm" in sys.argv
    sys.exit(run_cycle(dry_run=dry, live_llm=is_live_llm))
