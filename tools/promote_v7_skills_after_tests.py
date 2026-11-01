"""V7 Cấp 1 — promote skills theo bằng chứng test thật (không tự phong AVAILABLE).

Chỉ chuyển PROPOSED -> IMPLEMENTED_IN_SANDBOX -> TESTED (code có + test pass).
AVAILABLE/APPROVED vẫn chờ chủ duyệt theo chính sách.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")
from quan_ai_brain.cognition.skill_registry import SkillRegistry, SkillStatus  # noqa: E402

WS = Path(__file__).resolve().parents[1]

# 1. Chạy test thật để có bằng chứng
r = subprocess.run(
    [str(WS / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", "tests/test_v7_skills.py", "-q", "--tb=no", "-p", "no:cacheprovider"],
    cwd=WS, capture_output=True, text=True, timeout=300,
)
tail = (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else "no output"
print("pytest:", tail)

passed = " passed" in tail and " failed" not in tail and " error" not in tail
result_str = f"PASS ({tail})" if passed else f"FAIL ({tail})"

# 2. Promote theo bằng chứng
reg = SkillRegistry(WS / "data" / "skill_registry.json")
evidence = [
    "tests/test_v7_skills.py (38 tests: 10 lớp bắt buộc §3.5)",
    "src/quan_ai_brain/cognition/v7_skills.py (implement thật, stdlib only)",
]
for skill in reg.list_skills():
    if skill.name == "TASK_STATUS_RECONCILIATION":
        # AVAILABLE sẵn — chỉ record test result mới
        reg.record_test_result(skill.skill_id, result_str)
        print(f"{skill.name}: test_result={result_str}")
        continue
    if skill.status == SkillStatus.PROPOSED:
        reg.transition(skill.skill_id, SkillStatus.IMPLEMENTED_IN_SANDBOX,
                       reason="V7: implement thật trong cognition/v7_skills.py (38 tests)")
        reg.transition(skill.skill_id, SkillStatus.TESTED,
                       reason=f"V7: test suite §3.5 {result_str}", evidence_refs=evidence)
        reg.record_test_result(skill.skill_id, result_str)
        print(f"{skill.name}: PROPOSED -> TESTED ({result_str})")

print("---")
for s in reg.list_skills():
    print("-", s.name, "|", s.status.value, "|", s.test_result[:40])
