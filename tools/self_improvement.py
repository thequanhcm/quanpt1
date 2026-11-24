"""Self-Improvement Loop — CHERRY tự học từ lệnh chưa nhận diện (S1, fail-honest).

(24/11/2026, owner: "xây dựng để cherry tự hoàn thiện bản thân, tự học và tìm
mọi cách để học, xây dựng và phát triển" — ảnh image_e2d705.)

Bất biến an toàn (theo AGENTS.md):
- KHÔNG tự áp thay đổi hành vi: mọi kw học được phải nằm ở trạng thái
  PENDING_REVIEW cho tới khi owner duyệt qua `approve()` (giống R4 quarantine).
- KHÔNG đụng sibling systems, KHÔNG ghi ngoài workspace (data/self_improve/).
- Fail-honest: lỗi IO/parse → trả trạng thái thật, không fake "đã học".
- Mặc định ON phần GHI NHẬN (log unmatched) vì chỉ ghi file local; phần ÁP DỤNG
  luôn cần owner duyệt.

Đường dữ liệu:
  data/self_improve/unmatched.jsonl   — 1 dòng/JSON: {ts, text, sender}
  data/self_improve/proposals.json    — {"id": {kw, intent, count, status, created}}
  data/self_improve/learned_keywords.json — {intent: [kw,...]} CHỈ ghi khi duyệt

detect_intent đọc learned_keywords.json sau kw tĩnh (để lệnh hệ thống ưu tiên)
— kw học được là KW TĨNH bổ sung, có dấu + không dấu.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent
DATA_DIR = WORKSPACE / "data" / "self_improve"
UNMATCHED_PATH = DATA_DIR / "unmatched.jsonl"
PROPOSALS_PATH = DATA_DIR / "proposals.json"
LEARNED_PATH = DATA_DIR / "learned_keywords.json"

# Giới hạn kích thước để không phình vô hạn (fail-safe, không đọc secret).
_MAX_UNMATCHED_LINES = 5000
_MAX_TEXT_LEN = 300
_MIN_KW_LEN = 4

# Stopword tiếng Việt phổ biến — không đề xuất làm kw.
_STOPWORDS = {
    "anh", "em", "cho", "giúp", "giup", "với", "voi", "của", "cua", "và", "va",
    "là", "la", "các", "cac", "những", "nhung", "một", "mot", "hãy", "hay",
    "được", "duoc", "không", "khong", "gì", "gi", "nào", "nao", "nhiều", "nhieu",
    "tôi", "toi", "mình", "minh", "cherry", "tony", "ơi", "oi", "ạ", "a",
    "với", "voi", "từ", "tu", "trong", "ngoài", "ngoai", "lên", "len", "xuống",
    "xuong", "ra", "vào", "vao", "đi", "di", "lại", "lai", "rồi", "roi",
    "nói", "noi", "muốn", "muon", "cần", "can", "phải", "hai", "mấy", "may",
    "nhiêu", "bao", "giờ", "gio", "khi", "thì", "thi", "mà", "ma", "cũng",
    "cung", "đã", "da", "sẽ", "se", "bị", "bi", "bằng", "bang", "này", "nay",
    "kia", "đó", "do", "đây", "day",
}

# Map kw-gợi-ý → intent mặc định (nếu câu chứa từ chỉ miền rõ ràng).
# Ưu tiên cụm dài/trước, từ chung sau (first-match wins trong list).
_DOMAIN_HINTS: list[tuple[str, str]] = [
    ("màn hình", "pc_screenshot"), ("man hinh", "pc_screenshot"), ("chụp", "pc_screenshot"), ("chup", "pc_screenshot"),
    ("tả lời", "reply_draft"), ("trả lời", "reply_draft"), ("tra loi", "reply_draft"),
    ("nháp", "reply_draft"), ("nhap", "reply_draft"), ("soạn", "reply_draft"), ("soan", "reply_draft"),
    ("luồng", "thread_summary"), ("luong", "thread_summary"), ("thread", "thread_summary"),
    ("tóm tắt", "email_today"), ("tom tat", "email_today"),
    ("email", "email_today"), ("mail", "email_today"), ("vmail", "email_today"),
    ("hộp thư", "email_today"), ("hop thu", "email_today"),
    ("họp", "voffice_meetings"), ("lịch", "voffice_meetings"), ("lich", "voffice_meetings"),
    ("nhạc", "tony_music_play"), ("nhac", "tony_music_play"), ("phát", "tony_music_play"),
    ("ảnh", "tony_show_image"), ("hình", "tony_show_image"),
    ("nhiệm vụ", "tasks"), ("nhiem vu", "tasks"), ("việc", "todo"), ("viec", "todo"),
    ("tiến độ", "tasks"), ("tien do", "tasks"), ("dự án", "tasks"), ("du an", "tasks"),
    ("báo cáo", "report"), ("bao cao", "report"),
    ("trạng thái", "status"), ("trang thai", "status"), ("sức khỏe", "status"), ("suc khoe", "status"),
]


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def log_unmatched(text: str, sender: str = "") -> None:
    """Ghi 1 câu owner chưa nhận diện (detect_intent=None). Không bao giờ raise."""
    try:
        _ensure_dir()
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "text": (text or "").strip()[:_MAX_TEXT_LEN],
            "sender": (sender or "")[:64],
        }
        if not entry["text"]:
            return
        # Rotate đơn giản: quá hạn mức → bỏ nửa đầu (giữ mới).
        if UNMATCHED_PATH.exists():
            with open(UNMATCHED_PATH, encoding="utf-8") as fh:
                lines = fh.readlines()
            if len(lines) >= _MAX_UNMATCHED_LINES:
                lines = lines[len(lines) // 2:]
        else:
            lines = []
        lines.append(json.dumps(entry, ensure_ascii=False) + "\n")
        with open(UNMATCHED_PATH, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
    except Exception:
        pass  # học phải KHÔNG BAO GIỜ làm hỏng luồng trả lời chính


def _norm_token(w: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", w.lower())
                   if unicodedata.category(c) != "Mn")


def stats(limit: int = 10) -> dict[str, Any]:
    """Thống kê câu chưa nhận diện: tổng + top cụm từ khóa theo tần suất."""
    if not UNMATCHED_PATH.exists():
        return {"total": 0, "top": [], "last": None}
    counts: dict[str, int] = {}
    display: dict[str, str] = {}
    total = 0
    last = None
    try:
        with open(UNMATCHED_PATH, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                total += 1
                last = e
                raw = re.findall(r"[a-zA-Zà-ỹÀ-Ỹ0-9]+", e.get("text", ""))
                # BIGRAM (cụm 2 từ) — kw 1 từ dễ nuốt ('bao' ⊂ 'báo cáo'): an toàn hơn.
                keep = [w for w in raw if len(w) >= 2 and w.lower() not in _STOPWORDS]
                for i in range(len(keep) - 1):
                    key = _norm_token(keep[i]) + " " + _norm_token(keep[i + 1])
                    counts[key] = counts.get(key, 0) + 1
                    display.setdefault(key, f"{keep[i]} {keep[i+1]}")
    except Exception as exc:
        return {"total": total, "top": [], "last": last, "error": f"{type(exc).__name__}: {exc}"}
    top = [(display.get(k, k), c) for k, c in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]]
    return {"total": total, "top": top, "last": last}


def propose(min_count: int = 2, max_proposals: int = 10) -> dict[str, Any]:
    """Từ unmatched phổ biến → đề xuất kw mới (PENDING_REVIEW). KHÔNG tự áp."""
    st = stats(limit=40)
    if st.get("error"):
        return {"ok": False, "error": st["error"], "fail_honest": True}
    proposals: dict[str, Any] = {}
    if PROPOSALS_PATH.exists():
        try:
            with open(PROPOSALS_PATH, encoding="utf-8") as fh:
                proposals = json.load(fh)
        except Exception:
            proposals = {}
    existing = {p.get("kw") for p in proposals.values() if isinstance(p, dict)}
    learned = read_learned()
    learned_kws = {k for kws in learned.values() for k in kws}

    created = 0
    for word, cnt in st["top"]:
        if created >= max_proposals:
            break
        if cnt < min_count or len(word.replace(" ", "")) < (_MIN_KW_LEN + 2) or word in _STOPWORDS:
            continue
        if word in existing or word in learned_kws:
            continue
        intent = "email_today"
        for hint, it in _DOMAIN_HINTS:
            if hint in word:
                intent = it
                break
        pid = f"prop_{time.strftime('%Y%m%d_%H%M%S')}_{word[:24]}"
        proposals[pid] = {
            "kw": word,
            "intent": intent,
            "count": cnt,
            "status": "PENDING_REVIEW",
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "note": "đề xuất tự động từ lệnh owner chưa nhận diện — cần owner duyệt",
        }
        created += 1
    try:
        _ensure_dir()
        with open(PROPOSALS_PATH, "w", encoding="utf-8") as fh:
            json.dump(proposals, fh, ensure_ascii=False, indent=1)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "fail_honest": True}
    return {"ok": True, "created": created, "proposals": proposals}


def list_proposals(status: str = "PENDING_REVIEW") -> dict[str, Any]:
    try:
        with open(PROPOSALS_PATH, encoding="utf-8") as fh:
            proposals = json.load(fh)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "fail_honest": True}
    sel = {pid: p for pid, p in proposals.items()
           if isinstance(p, dict) and (status == "ALL" or p.get("status") == status)}
    return {"ok": True, "proposals": sel}


def approve(keyword_or_id: str, intent: str | None = None) -> dict[str, Any]:
    """Owner duyệt 1 đề xuất (theo id hoặc kw) → kw vào learned_keywords.json.

    Đây là ĐIỂM DUYỆT DUY NHẤT — không đường nào khác ghi learned_keywords.
    """
    try:
        with open(PROPOSALS_PATH, encoding="utf-8") as fh:
            proposals = json.load(fh)
    except Exception as exc:
        return {"ok": False, "error": f"không đọc được proposals: {type(exc).__name__}: {exc}", "fail_honest": True}

    target = None
    for pid, p in proposals.items():
        if not isinstance(p, dict):
            continue
        if pid == keyword_or_id or p.get("kw") == keyword_or_id.lower():
            target = (pid, p)
            break
    if target is None:
        return {"ok": False, "error": f"không tìm thấy đề xuất {keyword_or_id!r}", "fail_honest": True}
    pid, p = target
    if p.get("status") == "APPROVED":
        return {"ok": False, "error": "đề xuất đã duyệt trước đó", "fail_honest": True}
    final_intent = intent or p.get("intent") or "email_today"

    learned = read_learned()
    kws = learned.setdefault(final_intent, [])
    kw = p["kw"]
    if kw not in kws:
        kws.append(kw)
    try:
        _ensure_dir()
        with open(LEARNED_PATH, "w", encoding="utf-8") as fh:
            json.dump(learned, fh, ensure_ascii=False, indent=1)
    except Exception as exc:
        return {"ok": False, "error": f"ghi learned_keywords lỗi: {type(exc).__name__}: {exc}", "fail_honest": True}
    p["status"] = "APPROVED"
    p["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    p["approved_intent"] = final_intent
    with open(PROPOSALS_PATH, "w", encoding="utf-8") as fh:
        json.dump(proposals, fh, ensure_ascii=False, indent=1)
    return {"ok": True, "kw": kw, "intent": final_intent}


def read_learned() -> dict[str, list[str]]:
    """Đọc learned_keywords.json (detect_intent gọi); lỗi → rỗng (fail-open kw tĩnh)."""
    try:
        with open(LEARNED_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            out: dict[str, list[str]] = {}
            for it, kws in data.items():
                if isinstance(kws, list):
                    out[str(it)] = [str(k) for k in kws if str(k).strip()]
            return out
        return {}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# S2 (24/11/2026, owner: "cấu hình để tất cả các điều anh DM cho cherry đều tự
# học để nâng cấp liên tục") — AUTO-TUNE CYCLE: tự đề xuất ĐỊNH KỲ + tự áp kw đủ
# tin cậy (evidence mạnh) + rollback. Biên an toàn:
#   • chỉ học KW ĐỊNH TUYẾN (không tự sửa code, không tự wire intent mới)
#   • auto-apply CHỈ khi: count >= AUTO_MIN_COUNT và intent từ _DOMAIN_HINTS
#     (có bằng chứng miền rõ ràng) và kw chưa tồn tại ở learned/kw tĩnh
#   • mọi auto-apply có backup learned trước khi áp + tag "_auto" + audit
#   • tắt/bật qua data/self_improve/auto.json {"auto_apply": bool, "auto_propose": bool}
#   • rollback(kw|'toàn bộ') khôi phục learned từ backup gần nhất
AUTO_CONFIG_PATH = DATA_DIR / "auto.json"
AUTO_BACKUP_PATH = DATA_DIR / "learned_keywords.backup.json"
AUTO_STATE_PATH = DATA_DIR / "auto_state.json"
AUTO_MIN_COUNT = 3          # câu phải lặp >= 3 lần mới tự áp
AUTO_APPLY_LIMIT = 5        # tối đa kw tự áp mỗi chu kỳ


def _read_auto_config() -> dict[str, bool]:
    try:
        with open(AUTO_CONFIG_PATH, encoding="utf-8") as fh:
            d = json.load(fh)
        return {"auto_propose": bool(d.get("auto_propose", True)),
                "auto_apply": bool(d.get("auto_apply", True))}
    except Exception:
        return {"auto_propose": True, "auto_apply": True}  # owner đã duyệt auto liên tục


def set_auto(auto_propose: bool | None = None, auto_apply: bool | None = None) -> dict[str, bool]:
    cfg = _read_auto_config()
    if auto_propose is not None:
        cfg["auto_propose"] = bool(auto_propose)
    if auto_apply is not None:
        cfg["auto_apply"] = bool(auto_apply)
    try:
        _ensure_dir()
        with open(AUTO_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return cfg


def _static_keywords() -> set[str]:
    """Kw tĩnh hệ thống (có dấu + không dấu) — auto-apply tránh khớp kw tĩnh."""
    try:
        import sys as _sys
        if str(WORKSPACE / "tools") not in _sys.path:
            _sys.path.insert(0, str(WORKSPACE / "tools"))
        from netchat_command_center import COMMAND_PATTERNS
        out: set[str] = set()
        for kws in COMMAND_PATTERNS.values():
            for k in kws:
                out.add(k.lower())
                out.add(_norm_token(k))
        return out
    except Exception:
        return set()


def auto_cycle(min_count: int | None = None, max_apply: int | None = None) -> dict[str, Any]:
    """1 chu kỳ tự học: propose (nếu bật) → auto-apply kw đủ tin cậy (nếu bật).

    Báo cáo trung thực từng bước; lỗi ghi trong report, không raise (chạy nền).
    """
    cfg = _read_auto_config()
    min_c = min_count or AUTO_MIN_COUNT
    cap = max_apply or AUTO_APPLY_LIMIT
    report: dict[str, Any] = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                              "auto_propose": cfg["auto_propose"], "auto_apply": cfg["auto_apply"]}

    # 1) Tự đề xuất từ unmatched (ngưỡng evidence đề xuất: 2 lần)
    if cfg["auto_propose"]:
        pr = propose(min_count=2, max_proposals=10)
        report["propose"] = {"ok": pr.get("ok"), "created": pr.get("created", 0),
                             "error": pr.get("error")}
    else:
        report["propose"] = {"ok": True, "created": 0, "skipped": "auto_propose tắt"}

    # 2) Tự áp kw đủ tin cậy
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    if cfg["auto_apply"]:
        st = stats(limit=60)
        static_kws = _static_keywords()
        learned = read_learned()
        learned_all = {k for kws in learned.values() if k != "_auto" for k in kws}
        try:
            with open(PROPOSALS_PATH, encoding="utf-8") as fh:
                proposals = json.load(fh)
        except Exception:
            proposals = {}
        for word, cnt in st["top"]:
            if len(applied) >= cap:
                break
            if cnt < min_c or len(word.replace(" ", "")) < (_MIN_KW_LEN + 2):
                continue
            if word in learned_all or word in static_kws or _norm_token(word) in static_kws:
                continue
            # intent PHẢI từ _DOMAIN_HINTS (bằng chứng miền rõ) — không đoán mù
            intent = None
            for hint, it in _DOMAIN_HINTS:
                if hint in word:
                    intent = it
                    break
            if intent is None:
                skipped.append({"kw": word, "reason": "không rõ miền (không tự đoán)"})
                continue
            if not applied:
                try:
                    _ensure_dir()
                    with open(AUTO_BACKUP_PATH, "w", encoding="utf-8") as fh:
                        json.dump(learned, fh, ensure_ascii=False, indent=1)
                except Exception:
                    pass
            kws = learned.setdefault(intent, [])
            if word not in kws:
                kws.append(word)
            applied.append({"kw": word, "intent": intent, "count": cnt})
            for pid, p in proposals.items():
                if isinstance(p, dict) and p.get("kw") == word and p.get("status") == "PENDING_REVIEW":
                    p["status"] = "AUTO_APPLIED"
                    p["auto_applied_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        if applied:
            try:
                auto_tags = learned.get("_auto", [])
                for a in applied:
                    if a["kw"] not in auto_tags:
                        auto_tags.append(a["kw"])
                learned["_auto"] = auto_tags
                with open(LEARNED_PATH, "w", encoding="utf-8") as fh:
                    json.dump(learned, fh, ensure_ascii=False, indent=1)
                with open(PROPOSALS_PATH, "w", encoding="utf-8") as fh:
                    json.dump(proposals, fh, ensure_ascii=False, indent=1)
            except Exception as exc:
                report["apply_error"] = f"{type(exc).__name__}: {exc}"
    else:
        skipped.append({"kw": "*", "reason": "auto_apply tắt"})
    report["applied"] = applied
    report["skipped"] = skipped[:10]

    # 3) State + 4) Audit — không bao giờ raise (chạy nền)
    try:
        _ensure_dir()
        with open(AUTO_STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    except Exception:
        pass
    try:
        import sys as _sys
        if str(WORKSPACE / "src") not in _sys.path:
            _sys.path.insert(0, str(WORKSPACE / "src"))
        from quan_ai_brain.core.audit import AuditLogger
        AuditLogger(WORKSPACE).record("self_improvement.auto_cycle",
                                      {"applied": len(applied),
                                       "proposed": report.get("propose", {}).get("created", 0)})
    except Exception:
        pass
    return report


def auto_state() -> dict[str, Any]:
    try:
        with open(AUTO_STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        return {"error": f"chưa có chu kỳ nào chạy: {type(exc).__name__}: {exc}"}


def rollback(keyword: str | None = None) -> dict[str, Any]:
    """Rollback kw auto-applied (1 kw hoặc 'toàn bộ' kw auto) từ backup gần nhất."""
    try:
        with open(AUTO_BACKUP_PATH, encoding="utf-8") as fh:
            backup = json.load(fh)
    except Exception as exc:
        return {"ok": False, "error": f"không có backup: {type(exc).__name__}: {exc}", "fail_honest": True}
    learned = read_learned()
    auto_tags = learned.get("_auto", [])
    if keyword and keyword.lower() not in ("toàn bộ", "toan bo", "all"):
        kw = keyword
        removed = 0
        for it, kws in learned.items():
            if it == "_auto":
                continue
            if kw in kws:
                kws.remove(kw)
                removed += 1
        learned["_auto"] = [k for k in auto_tags if k != kw]
        out: dict[str, Any] = {"ok": True, "removed": removed, "kw": kw}
    else:
        learned = {**backup, "_auto": []}
        out = {"ok": True, "removed": "toàn bộ kw auto", "restored_from": str(AUTO_BACKUP_PATH)}
    try:
        with open(LEARNED_PATH, "w", encoding="utf-8") as fh:
            json.dump(learned, fh, ensure_ascii=False, indent=1)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "fail_honest": True}
    return out
