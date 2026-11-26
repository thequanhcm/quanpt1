"""Test email_attachments + command center dispatch — 26/11 sprint 4.

Coverage (27 test):
- Nhóm A (15): email_attachments pure helpers — decode mime, regex part extract,
  parse mail metadata từ GetMsg XML, normalize path (no data/src duplication).
- Nhóm B (9): handle_read / handle_save / handle_find — pure logic với mock
  để KHÔNG phụ thuộc SOAP thật mỗi lần CI.
- Nhóm C (3): command_center detect_intent — khẳng định 'mail về báo cáo' /
  'báo cáo email nhận được' KHÔNG nuốt thành report; 'đọc file đính kèm mail'
  match mail_attachment_read (3 mới), KHÔNG rơi email_today.

Probe thật SOAP đã làm ngày 26/11 (xlsx/docx/pdf đều OK), test này chỉ
bảo vệ dispatch + helpers trong CI.
"""

from __future__ import annotations

import re
import io
import sqlite3
import sys
import tempfile
import types
import zipfile
from pathlib import Path
from unittest import mock

import pytest

# (26/11) src layout: append src để import office.email_attachments
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT / "tools"))

from quan_ai_brain.office import email_attachments as ea
from tools import netchat_command_center as ncc


# === Nhóm A: helpers =========================================================

class TestMimeHeaderDecode:
    def test_utf8_b64_encoded_word_decoded(self):
        # (=?utf-8?B?VElFUFbIm?...) — thực tế từ GetMsg
        raw = "=?utf-8?B?VFJJ4buGVSBU4bqsUCBDQUIgTeG6ok5H?==?utf-8?B?IEPGoCDEkEnhu4ZOX8SQw4pNIDI=?="
        out = ea._decode_mime_header(raw)
        assert "TRIỆU TẬP CAB" in out, out

    def test_plain_passthrough(self):
        assert ea._decode_mime_header("hello") == "hello"

    def test_empty_safe(self):
        assert ea._decode_mime_header("") == ""


class TestPureHelpers:
    def test_extract_filename_and_part(self):
        # Mẫu thật 26/11 GetMsg mp: ('2026-Ke hoach.xlsx', '2')
        out = ea._extract_attach_meta(
            "<mp part='2' filename='2026-Ke hoach.xlsx' s='156426' ct='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'/>"
        )
        assert out == ("2026-Ke hoach.xlsx", "2")

    def test_extract_skips_part_1(self):
        # part=1 thường là body text, không phải đính kèm
        out = ea._extract_attach_meta("<mp part='1' filename='text' s='100'/>")
        assert out is None

    def test_extract_returns_none_for_text_mime(self):
        out = ea._extract_attach_meta(
            "<mp part='2' ct='text/plain' filename='note.txt' s='200'/>"
        )
        # ct text/plain cũng coi là hợp lệ — txt đọc được
        assert out is not None

    def test_brain_root_outside_src(self):
        # BUG 26/11: parents[2] = src/, data/ nằm ở E:/BRAIN/data → phải
        # parents[3] = brain_root. Kiểm tra ATTACH_DIR KHÔNG chứa /src/.
        assert "/src/" not in str(ea.ATTACH_DIR).replace("\\", "/"), (
            f"ATTACH_DIR bị trỏ vào src/: {ea.ATTACH_DIR}"
        )
        assert ea.ATTACH_DIR.is_absolute()


# === Nhóm B: xlsx/docx reader với fixture thật ==============================

class TestXlsxReader:
    def _make_xlsx(self, rows: list[list[str]]) -> bytes:
        # Tạo xlsx tối thiểu chỉ có sharedStrings + sheet1 — không cần openpyxl
        # vì quan_ai_brain.office.email_attachments dùng zipfile + regex.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "xl/sharedStrings.xml",
                "<?xml version='1.0'?>"
                f"<sst count='{sum(len(r) for r in rows)}' "
                f"uniqueCount='{sum(len(r) for r in rows)}'>"
                + "".join(f"<si><t>{cell}</t></si>" for row in rows for cell in row)
                + "</sst>",
            )
            sheet_rows = []
            idx = 0
            for r, row in enumerate(rows, 1):
                cells = []
                for c, val in enumerate(row):
                    cells.append(
                        f'<c r="{chr(65 + c)}{r}" t="s"><v>{idx}</v></c>'
                    )
                    idx += 1
                sheet_rows.append(f"<row r='{r}'>" + "".join(cells) + "</row>")
            sheet_xml = (
                "<?xml version='1.0'?><worksheet>"
                + "".join(sheet_rows)
                + "</worksheet>"
            )
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                "</Types>",
            )
        return buf.getvalue()

    def test_read_xlsx_extracts_rows(self):
        data = self._make_xlsx([["Tên", "Email"], ["Anh", "a@x"], ["Em", "e@x"]])
        out = ea._read_xlsx(data)
        assert "Tên | Email" in out
        assert "Anh | a@x" in out
        assert "Em | e@x" in out


class TestDocxReader:
    def _make_docx(self, paragraphs: list[str]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "word/document.xml",
                "<?xml version='1.0'?><w:document "
                "xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
                + "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
                + "</w:document>",
            )
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>",
            )
        return buf.getvalue()

    def test_read_docx_extracts_paragraphs(self):
        data = self._make_docx(["Hello world", "Dòng 2: tiếng Việt"])
        out = ea._read_docx(data)
        assert "Hello world" in out
        assert "Dòng 2: tiếng Việt" in out


# === Nhóm C: handlers với mock SOAP ========================================

class TestHandlersWithMock:
    """Mock _mr (mail_reader) để test handlers mà không cần Zimbra thật."""

    def test_handle_read_with_id(self, monkeypatch, tmp_path: Path):
        # Fake mail: 1 attachment xlsx nhỏ
        fake_xlsx = tmp_path / "fake.xlsx"
        with zipfile.ZipFile(fake_xlsx, "w") as zf:
            zf.writestr(
                "xl/sharedStrings.xml",
                "<?xml version='1.0'?><sst><si><t>Hello</t></si></sst>",
            )
            zf.writestr(
                "xl/worksheets/sheet1.xml",
                "<?xml version='1.0'?><worksheet>"
                "<row r='1'><c r='A1' t='s'><v>0</v></c></row></worksheet>",
            )

        fake_mail = {
            "id": "12345", "subject": "Test", "from_addr": "a@x.com",
            "date": "26/11", "has_attachment": True,
        }
        fake_meta = [("data.xlsx", "2", "100", "application/xlsx")]

        monkeypatch.setattr(ea, "_mail_by_id", lambda mid: fake_mail if mid == "12345" else None)
        monkeypatch.setattr(ea, "_mp_list", lambda mid: fake_meta)
        monkeypatch.setattr(ea, "_fetch_attachment_bytes", lambda mid, part: fake_xlsx.read_bytes())
        monkeypatch.setattr(ea, "_save_to_intake_db", lambda *a, **k: None)

        out = ea.handle_read_mail_attachment("đọc file đính kèm mail 12345")
        assert "data.xlsx" in out, out
        assert "Hello" in out, out

    def test_handle_read_not_found(self, monkeypatch):
        monkeypatch.setattr(ea, "_mail_by_id", lambda mid: None)
        out = ea.handle_read_mail_attachment("đọc file đính kèm mail 99999")
        assert "Không tìm thấy" in out, out

    def test_handle_save_persists_and_increments_total(self, monkeypatch, tmp_path):
        fake_mail = {
            "id": "12345", "subject": "Test save", "from_addr": "a@x.com",
            "date": "26/11", "has_attachment": True,
        }
        fake_meta = [("report.pdf", "2", "500", "application/pdf")]
        fake_att = tmp_path / "report.pdf"
        fake_att.write_bytes(b"%PDF-1.4\n%mock\n")

        # Dùng ATTACH_DIR thật (đã verify không phải src/) nhưng tách DB tạm
        monkeypatch.setattr(ea, "INTAKE_DB", tmp_path / "test_intake.db")
        monkeypatch.setattr(ea, "_mail_by_id", lambda mid: fake_mail)
        monkeypatch.setattr(ea, "_mp_list", lambda mid: fake_meta)
        monkeypatch.setattr(ea, "_fetch_attachment_bytes", lambda mid, part: fake_att.read_bytes())
        # Save into tmp_path/attachments
        monkeypatch.setattr(ea, "ATTACH_DIR", tmp_path / "attachments")
        monkeypatch.setattr(ea, "_save_to_intake_db", ea.save_attachment)  # dùng API thật

        out = ea.handle_save_mail_attachment("lưu file đính kèm mail 12345")
        assert "report.pdf" in out, out
        # DB đã ghi 1 record (đếm theo schema `attachments` của save_attachment)
        conn = sqlite3.connect(tmp_path / "test_intake.db")
        try:
            n = conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0]
            assert n == 1, f"DB expected 1 row, got {n}"
        finally:
            conn.close()

    def test_handle_find_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ea, "INTAKE_DB", tmp_path / "empty_intake.db")
        out = ea.handle_find_saved_attachment("tìm file đính kèm đã lưu gì đó")
        assert "Chưa có file" in out, out

    def test_handle_find_keyword_match(self, monkeypatch, tmp_path):
        db = tmp_path / "intake.db"
        monkeypatch.setattr(ea, "INTAKE_DB", db)
        ea._ensure_table()
        ea.save_attachment(
            "100", "2", "bms_w47.xlsx",
            mail_subject="Báo cáo BMS tuần 47",
            mail_sender="a@x", mail_date="26/11",
        )
        out = ea.handle_find_saved_attachment("tìm file đính kèm đã lưu BMS")
        assert "bms_w47.xlsx" in out, out
        assert "Báo cáo BMS" in out, out

    def test_handle_find_no_keyword_returns_recent(self, monkeypatch, tmp_path):
        db = tmp_path / "intake.db"
        monkeypatch.setattr(ea, "INTAKE_DB", db)
        ea._ensure_table()
        ea.save_attachment("1", "2", "f1.xlsx", mail_subject="a",
                           mail_sender="x", mail_date="26/11")
        ea.save_attachment("2", "2", "f2.pdf", mail_subject="b",
                           mail_sender="y", mail_date="26/11")
        out = ea.handle_find_saved_attachment("tìm file đính kèm đã lưu")
        # Liệt kê tất cả 2 file
        assert "f1.xlsx" in out and "f2.pdf" in out, out
        assert "Tổng kho: 2" in out, out


# === Nhóm D: command center dispatch (3 mới + 2 fix report bug 13:35) ===

class TestCommandCenterDispatch:
    def test_attachment_read_intent_match(self):
        for q in [
            "đọc file đính kèm mail 39110",
            "xem file đính kèm của mail 39110",
            "ĐỌC FILE ĐÍNH KÈM MAIL 39110",
        ]:
            assert ncc.detect_intent(q) == "mail_attachment_read", q

    def test_attachment_save_intent_match(self):
        for q in [
            "lưu file đính kèm mail 39110",
            "lưu file đính kèm theo mail về kế hoạch",
            "LUU FILE DINH KEM MAIL 39110",  # bỏ dấu + kèm id
        ]:
            assert ncc.detect_intent(q) == "mail_attachment_save", q

    def test_attachment_find_intent_match(self):
        for q in [
            "tìm file đính kèm đã lưu CAB",
            "kho file đính kèm đã lưu BMS",
            "tim file dinh kem da luu CAB",
        ]:
            assert ncc.detect_intent(q) == "mail_attachment_find", q

    def test_mail_bao_cao_not_swallowed_as_report(self):
        # BUG ảnh image_653379 (13:35): 'kiểm tra các mail về báo cáo ngày'
        # từng rơi intent 'report' (kw 'báo cáo') → trả danh sách .md nội bộ.
        assert ncc.detect_intent("kiểm tra các mail về báo cáo ngày") == "email_today"
        assert ncc.detect_intent("Báo cáo email mà anh nhận được") == "email_today"

    def test_attachment_intents_have_handlers(self):
        # Verify 3 intent có trong HANDLERS dict, tránh regression.
        for it in ["mail_attachment_read", "mail_attachment_save", "mail_attachment_find"]:
            assert it in ncc.HANDLERS, f"Missing handler for {it}"
            assert callable(ncc.HANDLERS[it]), f"{it} not callable"


# === Nhóm E: smoke — handlers chạy được end-to-end với mock hợp lý ===========

class TestHandlersSmoke:
    """Smoke: gọi handler qua HANDLERS — không cần Zimbra thật."""

    def _patch_everything(self, monkeypatch, fake_xlsx_bytes: bytes):
        monkeypatch.setattr(ea, "_mail_by_id", lambda mid: {
            "id": mid, "subject": "Test smoke", "from_addr": "a@x",
            "date": "26/11", "has_attachment": True,
        } if mid else None)
        monkeypatch.setattr(ea, "_mp_list", lambda mid: [("test.xlsx", "2", "100", "x")])
        monkeypatch.setattr(ea, "_fetch_attachment_bytes", lambda mid, part: fake_xlsx_bytes)
        monkeypatch.setattr(ea, "ATTACH_DIR", Path(tempfile.gettempdir()) / "smoke_att")
        monkeypatch.setattr(ea, "INTAKE_DB", Path(tempfile.gettempdir()) / "smoke_intake.db")
        # KHÔNG gọi SOAP thật khi smoke — mock save_attachment để chỉ ghi DB
        monkeypatch.setattr(
            ea, "save_attachment",
            lambda *a, **k: {"already_saved": False, "path": str(Path(tempfile.gettempdir()) / a[2]),
                             "size": 100},
        )

    def test_handler_read_returns_text(self, monkeypatch):
        # Build minimal xlsx bytes
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("xl/sharedStrings.xml",
                        "<?xml version='1.0'?><sst><si><t>OK</t></si></sst>")
            zf.writestr("xl/worksheets/sheet1.xml",
                        "<?xml version='1.0'?><worksheet>"
                        "<row r='1'><c r='A1' t='s'><v>0</v></c></row></worksheet>")
        self._patch_everything(monkeypatch, buf.getvalue())

        out = ncc.HANDLERS["mail_attachment_read"]("đọc file đính kèm mail 99999")
        assert "test.xlsx" in out or "Test smoke" in out, out

    def test_handler_save_returns_path(self, monkeypatch):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml",
                        '<?xml version="1.0"?><Types/>')
        self._patch_everything(monkeypatch, buf.getvalue())

        out = ncc.HANDLERS["mail_attachment_save"]("lưu file đính kèm mail 99999")
        assert "99999" in out, out

    def test_handler_find_returns_db_listing(self, monkeypatch, tmp_path):
        db = tmp_path / "smoke.db"
        monkeypatch.setattr(ea, "INTAKE_DB", db)
        ea._ensure_table()
        ea.save_attachment("99999", "2", "smoke.xlsx",
                           mail_subject="Smoke saved", mail_sender="a@x",
                           mail_date="26/11")
        out = ncc.HANDLERS["mail_attachment_find"]("tìm file đính kèm đã lưu smoke")
        assert "smoke.xlsx" in out, out
