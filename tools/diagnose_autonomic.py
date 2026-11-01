"""
CLI Diagnosis Tool for QUAN AI BRAIN — Autonomic Nervous System & Pain Reflection.
Run at any time to inspect the living health, active pain points, and missing sensory organs.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure src in sys.path
root = Path(__file__).resolve().parents[1]
src = root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from quan_ai_brain.core.autonomic import GLOBAL_AUTONOMIC_SYSTEM, PainLevel


def main():
    print("=" * 70)
    print("QUAN AI BRAIN — HỆ THẦN KINH TỰ CHỦ & BÁO CÁO ĐIỂM ĐAU SINH THỂ SỐ")
    print("=" * 70)

    print("\n[1/3] Đang kích hoạt chu trình tự kiểm tra đa giác quan (Self-Test Loop)...")
    report = GLOBAL_AUTONOMIC_SYSTEM.run_self_test()

    status_icon = "🟢" if report.is_healthy else ("🟡" if report.overall_pain_level == PainLevel.MILD else "🔴")
    print(f"\n{status_icon} MỨC ĐỘ ĐAU TỔNG THỂ: {report.overall_pain_level.value}")
    print(f"📊 ĐIỂM SỨC KHỎE SINH TỒN: {report.health_score:.1f}/100.0")

    print("\n🗣️ TIẾNG KÊU / PHẢN ÁNH BẰNG GIỌNG NÓI TỰ NHIÊN:")
    print(f'   "{report.vocal_summary}"')

    print("\n⚠️ CÁC ĐIỂM ĐAU ĐANG CẦN CHỮA TRỊ (ACTIVE PAIN POINTS):")
    if not report.active_pains:
        print("   -> Không có điểm đau nào. Toàn bộ cơ thể khỏe mạnh.")
    else:
        for idx, pain in enumerate(report.active_pains, 1):
            print(f"   {idx}. [{pain.pain_level.value}] Cơ quan: {pain.region.value}")
            print(f"      - Triệu chứng: {pain.symptom}")
            print(f"      - Phương thuốc khắc phục: {pain.remedy}")
            if pain.hardware_prescription:
                print(f"      - Kê đơn nâng cấp: {pain.hardware_prescription}")

    print("\n🔍 KIỂM KÊ CƠ QUAN VẬT LÝ & GIÁC QUAN (HARDWARE ORGANS):")
    for organ in report.hardware_organs:
        icon = "✅" if "HEALTHY" in organ.status.value else ("⚠️" if "DEGRADED" in organ.status.value else "❌")
        print(f"   {icon} {organ.organ_name} [{organ.region.value} - Ưu tiên: {organ.priority}]")
        print(f"      - Trạng thái: {organ.status.value}")
        print(f"      - Thiết bị ghi nhận: {organ.detected_device}")
        if organ.recommended_upgrade:
            print(f"      - Đề xuất nâng cấp: {organ.recommended_upgrade}")

    print("\n💊 TỔNG HỢP ĐƠN THUỐC NÂNG CẤP HỆ THỐNG:")
    for idx, rx in enumerate(report.prescriptions, 1):
        print(f"   [{idx}] {rx}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
