# -*- coding: utf-8 -*-
"""Test 13/11: audio_route.py — ưu tiên HDMI khi cắm màn, fallback BT SRS-XB33.

Nguồn gốc (owner 13/11, image_3120a8): 'em cài đặt ưu tiên loa ra HDMI nếu được
cắm màn hình, nếu không có hãy phát loa bluetooth được kết nối'.

Test logic thuần (mock subprocess/wpctl/open sysfs) — không đụng Pi5 thật,
không đụng BT thật. E2E thật đã chạy riêng: service exit 0, TTS HDMI PASS.
"""
import io
import importlib.util
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("audio_route", HERE / "edge_client" / "audio_route.py")
ar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ar)


def _patch(state):
    """state: dict với keys hdmi_a1, hdmi_a2 (str), wpctl (str), bt_info (str),
    l2ping (str), bt_connect (str), default (str|None = sink hiện default)."""
    def fake_run(cmd, shell=True, capture_output=True, text=True, timeout=20):
        class R:
            def __init__(self, out):
                self.stdout = out
                self.stderr = ""
        if not isinstance(cmd, str):
            return R("")
        if "wpctl set-default" in cmd:
            state["default"] = cmd.split()[-1]
            return R("")
        if "wpctl status" in cmd:
            return R(state["wpctl"])
        if "bluetoothctl info" in cmd:
            return R(state["bt_info"])
        if "bluetoothctl connect" in cmd:
            return R(state["bt_connect"])
        if "l2ping" in cmd:
            return R(state["l2ping"])
        return R("")

    def fake_open(path, *a, **kw):
        p = str(path)
        if "card1-HDMI-A-1/status" in p:
            return io.StringIO(state["hdmi_a1"])
        if "card1-HDMI-A-2/status" in p:
            return io.StringIO(state["hdmi_a2"])
        return mock.DEFAULT

    return mock.patch.multiple(
        "unittest.mock.sentinel",  # placeholder, replaced below
    ) if False else _apply(state, fake_run, fake_open)


def _apply(state, fake_run, fake_open):
    ctx1 = mock.patch.object(ar.subprocess, "run", fake_run)
    # audio_route đọc sysfs bằng open() nội bộ — patch builtins.open CHỈ quanh call:
    real_open = open

    def open_only_sysfs(path, *a, **kw):
        p = str(path)
        if "HDMI-A-1/status" in p or "HDMI-A-2/status" in p:
            return fake_open(path, *a, **kw)
        return real_open(path, *a, **kw)

    ctx2 = mock.patch("builtins.open", open_only_sysfs)
    return ctx1, ctx2


class _DualPatch:
    def __init__(self, ctx1, ctx2):
        self.ctx1, self.ctx2 = ctx1, ctx2

    def __enter__(self):
        self.ctx1.__enter__()
        self.ctx2.__enter__()

    def __exit__(self, *exc):
        self.ctx2.__exit__(*exc)
        self.ctx1.__exit__(*exc)


WPCTL_HDMI_ONLY = """
 ├─ Sinks:
 │  *   58. Built-in Audio Digital Stereo (HDMI) [vol: 1.00]
 │
 ├─ Sources:
"""

WPCTL_BT_DEFAULT = """
 ├─ Sinks:
 │      58. Built-in Audio Digital Stereo (HDMI) [vol: 1.00]
 │  *   71. bluez_sink.6C_47_60_58_EF_93.a2dp_sink [vol: 0.80]
 │
 ├─ Sources:
"""

# BT sink HIỆN DIỆN nhưng chưa phải default (HDMI đang *) — trạng thái cần fix:
WPCTL_HDMI_DEFAULT_BT_PRESENT = """
 ├─ Sinks:
 │  *   58. Built-in Audio Digital Stereo (HDMI) [vol: 1.00]
 │      71. bluez_sink.6C_47_60_58_EF_93.a2dp_sink [vol: 0.80]
 │
 ├─ Sources:
"""

BT_INFO_DISCONNECTED = "Device 6C:47:60:58:EF:93 SRS-XB33\n\tConnected: no"
BT_INFO_CONNECTED = "Device 6C:47:60:58:EF:93 SRS-XB33\n\tConnected: yes"


def test_hdmi_cung_man_hinh_va_default_da_la_hdmi():
    state = dict(hdmi_a1="disconnected", hdmi_a2="connected",
                 wpctl=WPCTL_HDMI_ONLY, default="58",
                 bt_info=BT_INFO_DISCONNECTED, l2ping="", bt_connect="")
    ctx1, ctx2 = _patch(state)
    with _DualPatch(ctx1, ctx2):
        assert ar.hdmi_connected() is True
        rc = ar.main()
    assert rc == 0
    assert state["default"] == "58"  # không đổi (đã đúng)


def test_hdmi_cung_man_hinh_default_sai_doi_sang_hdmi():
    # giả lập: BT đang default nhưng màn hình vừa cắm → phải đổi về HDMI
    state = dict(hdmi_a1="disconnected", hdmi_a2="connected",
                 wpctl=WPCTL_BT_DEFAULT, default="71",
                 bt_info=BT_INFO_DISCONNECTED, l2ping="", bt_connect="")
    ctx1, ctx2 = _patch(state)
    with _DualPatch(ctx1, ctx2):
        rc = ar.main()
    assert rc == 0
    assert state["default"] == "58"


def test_khong_man_hinh_bt_connected_doi_sang_bt():
    state = dict(hdmi_a1="disconnected", hdmi_a2="disconnected",
                 wpctl=WPCTL_HDMI_DEFAULT_BT_PRESENT, default="58",
                 bt_info=BT_INFO_CONNECTED, l2ping="OK", bt_connect="")
    ctx1, ctx2 = _patch(state)
    with _DualPatch(ctx1, ctx2):
        assert ar.hdmi_connected() is False
        rc = ar.main()
    assert rc == 0
    assert state["default"] == "71"


def test_khong_man_hinh_bt_chua_connect_nhung_reachable_tu_connect():
    state = dict(hdmi_a1="disconnected", hdmi_a2="disconnected",
                 wpctl=WPCTL_HDMI_ONLY, default="58",
                 bt_info=BT_INFO_DISCONNECTED, l2ping="1 bytes from",
                 bt_connect="Connection successful")
    ctx1, ctx2 = _patch(state)
    with _DualPatch(ctx1, ctx2):
        rc = ar.main()
    assert rc == 0
    # connect đã được gọi; bluez sink chưa kịp xuất hiện trong wpctl mock lần 1
    # → chạy lại với wpctl có bluez sink → phải đổi default sang BT:
    state2 = dict(state, wpctl=WPCTL_HDMI_DEFAULT_BT_PRESENT)
    ctx1b, ctx2b = _patch(state2)
    with _DualPatch(ctx1b, ctx2b):
        ar.main()
    assert state2["default"] == "71"


def test_khong_man_hinh_bt_khong_reachable_khong_doi():
    # Loa tắt nguồn — không spam retry, giữ nguyên (HDMI sink vẫn default như hiện trạng)
    state = dict(hdmi_a1="disconnected", hdmi_a2="disconnected",
                 wpctl=WPCTL_HDMI_ONLY, default="58",
                 bt_info=BT_INFO_DISCONNECTED, l2ping="Can't connect: Host is down",
                 bt_connect="")
    ctx1, ctx2 = _patch(state)
    with _DualPatch(ctx1, ctx2):
        rc = ar.main()
    assert rc == 0
    assert state["default"] == "58"


def test_hdmi_a1_connected_cung_nhan_la_co_man_hinh():
    state = dict(hdmi_a1="connected", hdmi_a2="disconnected",
                 wpctl=WPCTL_HDMI_ONLY, default="58",
                 bt_info=BT_INFO_DISCONNECTED, l2ping="", bt_connect="")
    ctx1, ctx2 = _patch(state)
    with _DualPatch(ctx1, ctx2):
        assert ar.hdmi_connected() is True
