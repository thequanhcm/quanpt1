# -*- coding: utf-8 -*-
"""Test Lịch trực FT — duty_roster (07/11/2026, owner yêu cầu đọc kho_tai_lieu).

Dùng file LỊCH TRỰC THẬT trong kho (read-only) cho E2E; các case fail-honest
trả trạng thái rõ ràng. Không sửa file nguồn, không đụng DB production.
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quan_ai_brain.knowledge import duty_roster as dr  # noqa: E402


def test_find_roster_file_nov_2026():
    f = dr.find_roster_file(11, 2026)
    assert f is not None and f.name.startswith("LICH_TRUC")


def test_no_file_for_far_future_month():
    assert dr.find_roster_file(12, 2030) is None


def test_get_duty_07_nov_matches_owner_example():
    """Đối chiếu ví dụ owner: ca ngày 6 tên đúng thứ tự."""
    res = dr.get_duty_for_date(7, 11, 2026)
    assert res["status"] == "OK"
    day_names = [p["name"] for p in res["day_shift"]]
    assert day_names == ["Dương Đức Thịnh", "Bùi Hữu Hiệu", "Nguyễn Quốc Đại",
                         "Phạm Hoàng Tùng", "Nguyễn Đức Mạnh", "Trịnh Đình Linh"]
    night_names = [p["name"] for p in res["night_shift"]]
    for must in ("Nhạc Quốc Khánh", "Bùi Hữu Hiệu", "Nguyễn Bá Quản"):
        assert must in night_names


def test_every_person_has_chuc_vu_and_phone():
    res = dr.get_duty_for_date(7, 11, 2026)
    for p in res["day_shift"] + res["night_shift"]:
        assert p["chuc_vu"] and p["chuc_vu"] != "Chưa rõ"
        assert p["dien_thoai"][:2] in ("09", "03", "08", "07", "05", "02")


def test_person_not_on_duty_reported_honestly():
    r = dr.find_person_shift("Phạm Thế Quân", 7, 11, 2026)
    assert r["status"] == "OK" and r["found"] is True and r["on_duty"] is False
    assert "KHÔNG trực" in r["message"]


def test_person_on_duty_returns_shift_and_contact():
    r = dr.find_person_shift("Nguyễn Quốc Đại", 7, 11, 2026)
    assert r["status"] == "OK" and r["on_duty"] is True
    assert r["shift"] == "ca ngày"
    assert r["person"]["dien_thoai"] == "0984755239"


def test_ambiguous_short_name_asks_back():
    """'quan' sau bỏ dấu trùng quân/quản → hỏi lại, KHÔNG đoán."""
    r = dr.find_person_shift("Quân", 7, 11, 2026)
    assert r["status"] == "AMBIGUOUS"
    assert "Nguyễn Bá Quản" in r["message"] and "Phạm Thế Quân" in r["message"]


def test_unknown_name_not_found():
    r = dr.find_person_shift("Nguyễn Văn Không Có", 7, 11, 2026)
    assert r["status"] == "OK" and r["found"] is False


def test_format_report_contains_both_shifts():
    res = dr.get_duty_for_date(8, 11, 2026)
    txt = dr.format_daily_report(res)
    assert "Lịch trực ngày 08/11/2026" in txt
    assert "Ca ngày" in txt and "Ca đêm" in txt


def test_format_report_fail_honest():
    txt = dr.format_daily_report({"status": "NO_FILE", "message": "Không tìm thấy file"})
    assert "⚠️" in txt and "Không tìm thấy file" in txt


def test_bad_date_rejected():
    res = dr.get_duty_for_date(40, 11, 2026)
    assert res["status"] in ("BAD_DATE", "NO_COLUMN")


def test_parse_marks_variants():
    assert dr._parse_marks("N+Đ") == {"N", "Đ"}
    assert dr._parse_marks("12hN") == {"N"}
    assert dr._parse_marks("N'") == {"N"}
    assert dr._parse_marks("Nghỉ phép") == set()
    assert dr._parse_marks("Học") == set()
