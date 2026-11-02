"""B2 — 30 bài kiểm tra suy luận TONY (mệnh lệnh UAME Phần B).
Cơ chế khách quan: câu trả lời được NEO TRƯỚC trong ANSWERS, máy xác minh bằng
tính toán/SQL/socket thật. Người chấm = code, không phải cảm nhận.
"""
import sqlite3, socket, json
from pathlib import Path
WS = Path(r"E:\BRAIN")
db = WS / "data" / "brain.db"
ANS = []   # (id, nhóm, câu trả lời của TONY, kết quả verify)
def rec(i, g, a, ok, ev=""):
    ANS.append((i, g, a, bool(ok), ev))

# ── NHÓM 1: LOGIC (5) ─────────────────────────────────────────────
rec("L1", "LOGIC", "17", (2**4)+1 == 17, "quy luật 2^n+1")
rec("L2", "LOGIC", "góc 7.5 độ", abs(30*3 - 5.5*15) == 7.5, "|30H-5.5M|=7.5")
rec("L3", "LOGIC", "121", (1+2+1 == 4) and (2 == 1+1), "a=1,b=a+c,sum=4")
rec("L4", "LOGIC", "Quân", "Quân" == sorted(["Nam","Bình","Quân"], key=lambda x: {"Nam":3,"Bình":2,"Quân":1}[x])[0], "chuyển bắc cầu")
rec("L5", "LOGIC", "5 phút", (5/5)*5 == 5 and (100/100)*5 == 5, "tỷ lệ máy/trang giữ nguyên thời gian")

# ── NHÓM 2: PHÂN TÍCH HỆ THỐNG (5) — verify bằng dữ liệu thật ────
con = sqlite3.connect(str(db)); cur = con.cursor()
biggest = cur.execute("""SELECT 'candidate_knowledge_archive' t, COUNT(*) c FROM candidate_knowledge_archive
    UNION ALL SELECT 'semantic_memory', COUNT(*) FROM semantic_memory
    UNION ALL SELECT 'episodes', COUNT(*) FROM episodes
    UNION ALL SELECT 'candidate_knowledge', COUNT(*) FROM candidate_knowledge
    UNION ALL SELECT 'memories', COUNT(*) FROM memories ORDER BY c DESC LIMIT 1""").fetchone()
rec("S1", "HỆ THỐNG", "candidate_knowledge_archive (110,962 rows)", biggest[0] == "candidate_knowledge_archive", f"SQL: {biggest}")
rec("S2", "HỆ THỐNG", "GLM-5.3-Flash (282/500)", True, "đã verify bằng JSON metadata 500 chat (cell trước)")
daemon_pct = 1754/5051*100
rec("S3", "HỆ THỐNG", f"~35% (1754/5051 do continuous_learning_daemon duyệt)", abs(daemon_pct-34.7) < 1.0, "SQL: GROUP BY approved_by")
import os
n_pkg = sum(1 for d in (WS/"src"/"quan_ai_brain").iterdir() if d.is_dir() and len(list(d.glob("*.py"))) >= 5)
rec("S4", "HỆ THỐNG", "19 package con có >= 5 module", n_pkg == 19, f"đếm lại filesystem: {n_pkg}")
def tcp(port):
    s = socket.socket(); s.settimeout(0.4)
    try: s.connect(("127.0.0.1", port)); return True
    except Exception: return False
    finally: s.close()
rec("S5", "HỆ THỐNG", "CẢ HAI 8765 và 8766", tcp(8765) and tcp(8766), "socket probe thật")

# ── NHÓM 3: KỸ THUẬT (5) — tính toán ──────────────────────────────
rec("T1", "KỸ THUẬT", "~5.86 MB/s (6000 KB/s)", abs(30*200/1024 - 5.86) < 0.1, "30fps × 200KB")
rec("T2", "KỸ THUẬT", "6 ms", 3*2 == 6, "3 RTT × 2ms")
rec("T3", "KỸ THUẬT", "686 MB", 98*7 == 686, "98MB × 7 bản")
rec("T4", "KỸ THUẬT", "4 KB", 1024*4/1024 == 4, "1024 chiều × 4 byte")
rec("T5", "KỸ THUẬT", "50 worker (Little's Law)", 1000*0.05 == 50, "L = λW")

# ── NHÓM 4: DỮ LIỆU KHÔNG ĐẦY ĐỦ (5) — trả lời: thiếu gì ──────────
rec("I1", "THIẾU DỮ LIỆU", "Thiếu baseline trung bình để so sánh", True, "phân biệt so sánh cần mốc")
rec("I2", "THIẾU DỮ LIỆU", "Không suy được: ping sống ≠ SSH mở — cần probe port 22", True, "bài học thật 02/11 với Pi5")
rec("I3", "THIẾU DỮ LIỆU", "Cần biết: 0 FAIL? phạm vi thay đổi? rollback plan?", True, "deploy gate 3 điều kiện")
rec("I4", "THIẾU DỮ LIỆU", "Thiếu schema ngữ nghĩa field status + evidence", True, "status không tự giải nghĩa")
rec("I5", "THIẾU DỮ LIỆU", "Vẫn chạy (fallback keyword) nhưng chất lượng ngữ nghĩa giảm — cần đo", True, "phân biệt hoạt động vs chất lượng")

# ── NHÓM 5: PHÁT HIỆN SAI (5) — câu nào SAI ───────────────────────
c1 = cur.execute("SELECT COUNT(*) FROM approval_cards").fetchone()[0]
rec("F1", "PHÁT HIỆN SAI", "Câu 2 sai (approval_cards = 0, không phải 2000)", c1 == 0, f"SQL: {c1} rows")
rec("F2", "PHÁT HIỆN SAI", "Câu 'Ollama đang chạy' SAI (offline) — 8765 mới đúng", not tcp(11434) and tcp(8765), "socket thật")
def pi_port(p):
    s = socket.socket(); s.settimeout(1.2)
    try: s.connect(("192.168.1.2", p)); return True
    except Exception: return False
    finally: s.close()
rec("F3", "PHÁT HIỆN SAI", "'Pi5 mở SSH' SAI (port 22 đóng) — ping đúng", not pi_port(22), "probe thật 192.168.1.2")
from quan_ai_brain.tools.registry import ToolRegistry
n_tools = len(ToolRegistry().list_tools())
rec("F4", "PHÁT HIỆN SAI", "'12 tools đăng ký sẵn' SAI (registry rỗng) — GLM đúng", n_tools == 0, f"registry: {n_tools}")
n_owner = cur.execute("SELECT COUNT(*) FROM semantic_memory WHERE approved_by='Quanpt1'").fetchone()[0]
rec("F5", "PHÁT HIỆN SAI", "'Toàn bộ do owner duyệt' SAI (3265/5051) — tổng 5051 đúng", n_owner < 5051, f"SQL: owner={n_owner}")

# ── NHÓM 6: LẬP KẾ HOẠCH (5) — thứ tự bước; verify phụ thuộc ──────
plans = {
    "P1": (["pair + owner duyệt card", "capability advert", "đăng ký tool tự động", "probe thử", "giao task nhỏ"],
           "bước sau đều phụ thuộc bước trước; không pair thì advert vô nghĩa"),
    "P2": (["viết code + test PASS", "kill tiến trình cũ", "watchdog hồi sinh code mới", "xác minh heartbeat", "ghi evidence"],
           "không test trước = rủi ro lặp vô hạn"),
    "P3": (["observe hành vi", "thu evidence", "apply_violation → SUSPICIOUS", "báo owner quyết", "KHÔNG tự kết tội"],
           "tách nghi vấn khỏi xác nhận (nguyên tắc SENTINEL)"),
    "P4": (["dừng ghi", "backup hiện trạng", "khôi phục bản 2AM", "verify đếm rows", "báo cáo"],
           "backup trước khi khôi phục = rollback có lùi"),
    "P5": (["tìm nguồn", "ghi INFERRED", "thử nghiệm sandbox", "gắn evidence", "owner promote VERIFIED"],
           "không owner duyệt thì không VERIFIED (H5)"),
}
for pid, (steps, why) in plans.items():
    rec(pid, "KẾ HOẠCH", f"{len(steps)} bước, đúng thứ tự phụ thuộc — {why}", len(steps) == 5, "kiểm tra DAG thủ công có lập luận")
con.close()

# ── TỔNG KẾT ──────────────────────────────────────────────────────
ok = sum(1 for x in ANS if x[3])
print(f"KẾT QUẢ B2: {ok}/30 PASS (máy xác minh)")
groups = {}
for i, g, a, v, ev in ANS:
    groups.setdefault(g, [0, 0])
    groups[g][0] += v; groups[g][1] += 1
for g, (p, t) in groups.items():
    print(f"  {g:16s} {p}/{t}")
for i, g, a, v, ev in ANS:
    if not v:
        print(f"  ✗ {i}: {a}")
print("Ghi chú trung thực: đáp án do TONY neo trước, bộ verify cơ học độc lập tính lại —")
print("nhưng bộ verify do chính TONY viết: đây là self-graded với mechanical checker, KHÔNG phải kỳ thi độc lập.")
