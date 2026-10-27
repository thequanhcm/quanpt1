"""V7 wire: insert progress-check chain vào chat handler (sau block TaskPipeline).

Chiến lược đã kiểm chứng (bài học V6/CLO): patch server.py phức tạp bằng script
Python + AST check, không dùng patch tool trực tiếp.
Idempotent: bỏ qua nếu đã có marker V7_CHAIN_WIRE.
"""
import ast
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
SERVER = WS / "src" / "quan_ai_brain" / "web" / "server.py"

src = SERVER.read_text(encoding="utf-8")
if "V7_CHAIN_WIRE" in src:
    print("Already wired — skip")
    sys.exit(0)

ANCHOR = '''                    except Exception as tp_err:
                        # Non-blocking: pipeline chỉ là evidence trail, không chặn chat
                        all_warnings.append(f"TaskPipeline trail: {str(tp_err)[:100]}")
                except Exception as plan_err:
                    all_warnings.append(f"Auto-planning registration: {plan_err}")'''

BLOCK = '''                    except Exception as tp_err:
                        # Non-blocking: pipeline chỉ là evidence trail, không chặn chat
                        all_warnings.append(f"TaskPipeline trail: {str(tp_err)[:100]}")
                except Exception as plan_err:
                    all_warnings.append(f"Auto-planning registration: {plan_err}")

                # V7_CHAIN_WIRE: chain skill kiểm tra tiến độ — chạy khi query khớp
                # trigger của skill TASK_STATUS_RECONCILIATION (AVAILABLE). Đọc-only,
                # fail-honest, không chặn chat (lỗi chỉ append warning).
                try:
                    from quan_ai_brain.cognition.skill_registry import SkillRegistry as _V7SR
                    from quan_ai_brain.cognition.v7_skills import run_progress_check_chain as _v7_chain

                    _v7_ws = _find_workspace_root()
                    _v7_matches = _V7SR(_v7_ws / "data" / "skill_registry.json").find_matching_skills(query or "")
                    if any(s.name == "TASK_STATUS_RECONCILIATION" for s in _v7_matches):
                        _v7_result = _v7_chain(query or "", _v7_ws)
                        response_data["progress_check"] = {
                            "chain": _v7_result["chain"],
                            "conclusion": _v7_result["reconciliation"]["conclusion"],
                            "records_matched": _v7_result["reconciliation"]["records_matched"],
                            "sources_accessed": _v7_result["reconciliation"]["sources_accessed"],
                            "sources_blocked": _v7_result["reconciliation"]["sources_blocked"],
                            "risk_summary": _v7_result["risk_summary"],
                            "report_md": _v7_result["report_md"],
                        }
                except Exception as v7_err:
                    all_warnings.append(f"V7 progress chain: {str(v7_err)[:100]}")'''

if ANCHOR not in src:
    print("ANCHOR NOT FOUND — file structure changed, abort (fail-closed)")
    sys.exit(1)

new_src = src.replace(ANCHOR, BLOCK, 1)
# AST check trước khi ghi
try:
    ast.parse(new_src)
except SyntaxError as exc:
    print(f"AST FAIL: {exc} — NOT writing (fail-closed)")
    sys.exit(1)

SERVER.write_text(new_src, encoding="utf-8")
ast.parse(SERVER.read_text(encoding="utf-8"))
print("Wired OK + AST OK")
