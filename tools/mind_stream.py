"""
CLI Stream of Consciousness Monitor for QUAN AI BRAIN — Autonomous Mind.
Run at any time to inspect the assistant's internal monologue, active focus,
and trigger autonomous thinking cycles.
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

from quan_ai_brain.cognition.autonomous_mind import GLOBAL_AUTONOMOUS_MIND, CogitationMode


def main():
    print("=" * 70)
    print("QUAN AI BRAIN — DÒNG Ý THỨC NỘI TÂM & TÂM TRÍ TỰ THÂN (AUTONOMOUS MIND)")
    print("=" * 70)

    print("\n[1/3] Kích hoạt 1 chu trình tự suy nghĩ chủ động (Autonomous Cogitation)...")
    thought = GLOBAL_AUTONOMOUS_MIND.cogitate(trigger="IDLE_REFLECTION")

    state = GLOBAL_AUTONOMOUS_MIND.get_state()
    print(f"\n🧠 TRẠNG THÁI TÂM TRÍ: {state['mode']}")
    print(f"🎯 TIÊU ĐIỂM QUAN TÂM HIỆN TẠI: {state['active_focus']}")
    print(f"🔢 TỔNG SỐ LƯỢT SUY NGHĨ NỘI TÂM: {state['total_thoughts']}")

    print("\n💭 SUY NGHĨ NỘI TÂM MỚI NHẤT (LATEST INTERNAL MONOLOGUE):")
    print(f"   - Mã suy nghĩ: {thought.thought_id}")
    print(f"   - Chủ đề: {thought.topic}")
    print(f"   - Động lực kích hoạt: {thought.trigger}")
    print(f"   - Sắc thái tư duy: {thought.sentiment}")
    print(f'   - Lời độc thoại nội tâm:\n     "{thought.inner_monologue}"')
    if thought.actionable_idea:
        print(f"   - Ý tưởng hành động / Sáng kiến rút ra:\n     -> {thought.actionable_idea}")

    print("\n⚡ XUNG NHỊP GIỮ ẤM NƠ-RON (NEURAL KEEP-WARM PULSE):")
    is_warm = GLOBAL_AUTONOMOUS_MIND.keep_warm_pulse()
    status_icon = "🔥 SẴN SÀNG" if is_warm else "❄️ NGUỘI"
    print(f"   - Trạng thái VRAM/Ollama: {status_icon} (Đã phát xung: {GLOBAL_AUTONOMOUS_MIND._keep_warm_count} lần)")

    print("\n📜 LỊCH SỬ DÒNG SUY NGHĨ GẦN ĐÂY (STREAM OF CONSCIOUSNESS):")
    recent = GLOBAL_AUTONOMOUS_MIND.get_recent_thoughts(limit=5)
    for idx, t in enumerate(recent, 1):
        print(f"   [{idx}] [{t['created_at_utc'][11:19]}] ({t['trigger']}) {t['topic']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
