# -*- coding: utf-8 -*-
"""Test 13/11: nút CHERRY/STOP vật lý + lệnh DM bật/tắt hình thể.

Nguồn gốc (owner 13/11): 'kiểm tra trên pi5 anh ấn nut cherry và stop đều
không có tác dụng. hãy cài đặt để anh ra lệnh bật hình thể hoặc tắt hình thể
trên netchat là hệ thống sẽ thực hiện đúng'.

2 nhóm:
  A) detect_intent nhận lệnh DM mọi biến thể ('cherry ơi ...' gồm cả 'ơi')
  B) handle_tony_on/handle_tony_off gọi edge API đúng action (mock
     _edge_control; E2E thật đã chạy trên Pi5: tắt→kiosk_running=False,
     bật→kiosk_running=True).
"""
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import netchat_command_center as cc


# ---------------------------------------------------------------------------
# A) detect_intent — lệnh bật/tắt hình thể qua DM
# ---------------------------------------------------------------------------

def test_detect_cherry_oi_tat_hinh_the():
    assert cc.detect_intent("cherry ơi tắt hình thể") == "tony_off"

def test_detect_cherry_oi_bat_hinh_the():
    assert cc.detect_intent("cherry ơi bật hình thể") == "tony_on"

def test_detect_tat_hinh_the_dau_cau():
    assert cc.detect_intent("tắt hình thể") == "tony_off"

def test_detect_bat_hinh_the_dau_cau():
    assert cc.detect_intent("bật hình thể") == "tony_on"

def test_detect_cherry_giup_anh():
    assert cc.detect_intent("cherry tắt hình thể giúp anh") == "tony_off"

def test_detect_cherry_bat_hinh_the():
    assert cc.detect_intent("cherry bật hình thể") == "tony_on"

def test_goi_don_cherry_oi_khong_phai_lenh():
    assert cc.detect_intent("cherry ơi") is None

def test_cau_hoi_hinh_the_van_tra_status():
    # câu hỏi bắt đầu bằng 'hình thể' (read-only) → status là thiết kế đúng
    assert cc.detect_intent("hình thể hiện thế nào") == "tony_status"

def test_regres_noi_dung_la_gi_khong_nuot():
    # regression 13/11: alias 'dung' không nuốt 'nội dung'
    assert cc.detect_intent("nội dung là gì") is None

def test_music_stop_van_uu_tien():
    assert cc.detect_intent("cherry ơi dừng nhạc") == "tony_music_stop"


# ---------------------------------------------------------------------------
# B) handle_tony_on/off — gọi _edge_control đúng action (mock)
# ---------------------------------------------------------------------------

def test_tony_off_goi_close_kiosk():
    with mock.patch.object(cc, "_edge_control", return_value=(True, "ok")) as m:
        out = cc.handle_tony_off("")
    m.assert_called_once()
    assert m.call_args[0][0] == {"action": "close_kiosk"}
    assert "🌙" in out


def test_tony_on_goi_start_kiosk():
    with mock.patch.object(cc, "_edge_control", return_value=(True, "ok")) as m:
        out = cc.handle_tony_on("")
    m.assert_called_once()
    assert m.call_args[0][0] == {"action": "start_kiosk"}
    assert "🤖" in out


def test_tony_off_bao_loi_khi_api_fail():
    with mock.patch.object(cc, "_edge_control", return_value=(False, "kiosk busy")):
        out = cc.handle_tony_off("")
    assert "⚠️" in out, "fail-honest: API fail phải báo lỗi"
    assert "kiosk busy" in out


def test_tony_on_bao_loi_khi_api_fail():
    with mock.patch.object(cc, "_edge_control", return_value=(False, "timeout")):
        out = cc.handle_tony_on("")
    assert "⚠️" in out
    assert "timeout" in out
