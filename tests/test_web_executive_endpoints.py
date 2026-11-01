"""Tests for Executive Consultation and Cockpit REST API endpoints."""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
import urllib.request

import pytest

from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture(scope="module")
def executive_server_instance(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("exec_workspace")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    # V6 hotfix (27/10/2026): isolate workspace — POST /api/executive/plan
    # ghi vào test workspace, không vào production DB.
    old_env = os.environ.get("QUAN_AI_BRAIN_WORKSPACE")
    os.environ["QUAN_AI_BRAIN_WORKSPACE"] = str(test_workspace)

    # Copy read-only assets cần cho test edge files (avatar) từ production
    # workspace sang test workspace — test chỉ GHI vào tmp.
    import shutil
    real_ws = Path(__file__).resolve().parents[1]
    src_assets = real_ws / "edge_client" / "assets" / "avatar"
    if src_assets.exists():
        shutil.copytree(src_assets, test_workspace / "edge_client" / "assets" / "avatar", dirs_exist_ok=True)

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    time.sleep(0.1)

    yield base_url

    server.shutdown()
    server.server_close()

    if old_env is None:
        os.environ.pop("QUAN_AI_BRAIN_WORKSPACE", None)
    else:
        os.environ["QUAN_AI_BRAIN_WORKSPACE"] = old_env


def test_executive_html_served(executive_server_instance: str) -> None:
    req = urllib.request.Request(f"{executive_server_instance}/executive.html")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "QUAN AI BRAIN" in content
        assert "BẢN SAO NHÂN SỰ SỐ" in content
        assert "tab-consultation" in content
        assert "tony-avatar-canvas" in content
        assert "btn-emergency-stop" in content


def test_executive_api_overview(executive_server_instance: str) -> None:
    req = urllib.request.Request(f"{executive_server_instance}/api/executive/overview")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert data["persona"]["name"] == "QUAN AI BRAIN"
        assert data["capability_count"] >= 7
        assert "pending_consultations" in data


def test_executive_api_persona(executive_server_instance: str) -> None:
    req = urllib.request.Request(f"{executive_server_instance}/api/executive/persona")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "Quanpt1" in data["owner_name"]
        assert data.get("owner_id") == "Quanpt1"
        assert len(data["directives"]) >= 5


def test_executive_api_capabilities(executive_server_instance: str) -> None:
    req = urllib.request.Request(f"{executive_server_instance}/api/executive/capabilities")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        caps = data["capabilities"]
        assert len(caps) >= 7
        cap_ids = [c["capability_id"] for c in caps]
        assert "long_term_memory" in cap_ids
        assert "self_learning_v1" in cap_ids


def test_executive_api_consultations_flow(executive_server_instance: str) -> None:
    # 1. List consultations
    req = urllib.request.Request(f"{executive_server_instance}/api/executive/consultations")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        tickets = data["tickets"]
        assert len(tickets) >= 3

    # 2. Respond to ticket
    target_id = tickets[0]["ticket_id"]
    post_data = json.dumps({
        "ticket_id": target_id,
        "decision": "APPROVE",
        "guidance": "Anh phê duyệt triển khai ngay.",
    }).encode("utf-8")
    req_post = urllib.request.Request(
        f"{executive_server_instance}/api/executive/consultations/respond",
        data=post_data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_post, timeout=5.0) as resp:
        assert resp.status == 200
        res_data = json.loads(resp.read().decode("utf-8"))
        assert res_data["success"] is True
        assert res_data["ticket"]["status"] == "APPROVED"
        assert res_data["ticket"]["owner_guidance"] == "Anh phê duyệt triển khai ngay."


def test_executive_api_learning_reports(executive_server_instance: str) -> None:
    req = urllib.request.Request(f"{executive_server_instance}/api/executive/learning/reports")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert len(data["reports"]) >= 1
        assert data["reports"][0]["cycle_number"] >= 1


def test_executive_api_supervisor_and_tasks(executive_server_instance: str) -> None:
    # Test supervisor endpoint
    req = urllib.request.Request(f"{executive_server_instance}/api/executive/supervisor")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert "state" in data
        assert "active_model" in data
        assert "edge_device" in data
        assert data["edge_device"]["device_id"].startswith("EDGE-PI5")

    # Test tasks endpoint
    req_tasks = urllib.request.Request(f"{executive_server_instance}/api/executive/tasks")
    with urllib.request.urlopen(req_tasks, timeout=5.0) as resp:
        assert resp.status == 200
        task_data = json.loads(resp.read().decode("utf-8"))
        assert task_data["success"] is True
        assert "active_tasks" in task_data
        assert "governance_bounds" in task_data
        assert task_data["governance_bounds"]["R5"] == "Hard-Blocked"


def test_executive_api_tasks_full_lifecycle(executive_server_instance: str) -> None:
    # 1. Create a new task via /api/executive/tasks/create
    create_payload = json.dumps({
        "goal": "Kiểm toán hiệu năng hệ thống và bảo mật dữ liệu điều hành",
        "autonomy_level": "LEVEL_A",
        "allow_fallback": True,
        "model": "mock",
    }).encode("utf-8")
    req_create = urllib.request.Request(
        f"{executive_server_instance}/api/executive/tasks/create",
        data=create_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_create, timeout=10.0) as resp:
        assert resp.status == 200
        create_data = json.loads(resp.read().decode("utf-8"))
        assert create_data["success"] is True
        task = create_data["task"]
        task_id = task["task_id"]
        assert task_id.startswith("task_")
        assert task["goal"] == "Kiểm toán hiệu năng hệ thống và bảo mật dữ liệu điều hành"

    # 2. Verify task listing includes steps_count and progress_pct
    req_list = urllib.request.Request(f"{executive_server_instance}/api/executive/tasks")
    with urllib.request.urlopen(req_list, timeout=5.0) as resp:
        assert resp.status == 200
        list_data = json.loads(resp.read().decode("utf-8"))
        assert list_data["success"] is True
        matching = [t for t in list_data["active_tasks"] if t["task_id"] == task_id]
        assert len(matching) == 1
        t_item = matching[0]
        assert "steps_count" in t_item
        assert "completed_steps_count" in t_item
        assert "progress_pct" in t_item
        assert t_item["steps_count"] >= 1

    # 3. Verify task detail endpoint
    req_detail = urllib.request.Request(f"{executive_server_instance}/api/executive/tasks/detail?task_id={task_id}")
    with urllib.request.urlopen(req_detail, timeout=5.0) as resp:
        assert resp.status == 200
        detail_data = json.loads(resp.read().decode("utf-8"))
        assert detail_data["success"] is True
        assert detail_data["task"]["task_id"] == task_id
        assert len(detail_data["steps"]) >= 1

    # 4. Execute task in inert mode
    exec_payload = json.dumps({"task_id": task_id, "dry_run": True}).encode("utf-8")
    req_exec = urllib.request.Request(
        f"{executive_server_instance}/api/executive/tasks/execute",
        data=exec_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_exec, timeout=15.0) as resp:
        assert resp.status == 200
        exec_data = json.loads(resp.read().decode("utf-8"))
        assert exec_data["success"] is True
        assert "outcome" in exec_data

    # 5. Check supervisor exposes current_task
    req_sup = urllib.request.Request(f"{executive_server_instance}/api/executive/supervisor")
    with urllib.request.urlopen(req_sup, timeout=5.0) as resp:
        assert resp.status == 200
        sup_data = json.loads(resp.read().decode("utf-8"))
        assert sup_data["success"] is True
        assert "current_task" in sup_data
        assert sup_data["current_task"] is not None
        assert "progress_pct" in sup_data["current_task"]

    # 6. Cancel task
    cancel_payload = json.dumps({"task_id": task_id, "reason": "Test cancel"}).encode("utf-8")
    req_cancel = urllib.request.Request(
        f"{executive_server_instance}/api/executive/tasks/cancel",
        data=cancel_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_cancel, timeout=5.0) as resp:
        assert resp.status == 200
        cancel_data = json.loads(resp.read().decode("utf-8"))
        assert cancel_data["success"] is True
        assert cancel_data["task"]["status"] == "CANCELLED"



def test_executive_api_emergency(executive_server_instance: str) -> None:
    # 1. Trigger FREEZE
    freeze_payload = json.dumps({"action": "freeze", "reason": "Test freeze from UI"}).encode("utf-8")
    req = urllib.request.Request(
        f"{executive_server_instance}/api/executive/emergency",
        data=freeze_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert data["emergency_state"] == "freeze"

    # 2. Check supervisor reflects SAFE_MODE
    req_sup = urllib.request.Request(f"{executive_server_instance}/api/executive/supervisor")
    with urllib.request.urlopen(req_sup, timeout=5.0) as resp:
        sup_data = json.loads(resp.read().decode("utf-8"))
        assert sup_data["emergency_state"] == "freeze"
        assert sup_data["state"] == "SAFE_MODE"

    # 3. Resume / Normal
    resume_payload = json.dumps({"action": "resume", "reason": "Test resume from UI"}).encode("utf-8")
    req_resume = urllib.request.Request(
        f"{executive_server_instance}/api/executive/emergency",
        data=resume_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_resume, timeout=5.0) as resp:
        assert resp.status == 200
        res_data = json.loads(resp.read().decode("utf-8"))
        assert res_data["emergency_state"] == "normal"


def test_executive_api_edge_alerts_and_status(executive_server_instance: str) -> None:
    # 1. Test edge status endpoint
    req_status = urllib.request.Request(f"{executive_server_instance}/api/executive/edge/status")
    with urllib.request.urlopen(req_status, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert "edge" in data
        assert "state" in data["edge"]

    # 2. Test edge alerts endpoint
    req_alerts = urllib.request.Request(f"{executive_server_instance}/api/executive/edge/alerts")
    with urllib.request.urlopen(req_alerts, timeout=5.0) as resp:
        assert resp.status == 200
        alert_data = json.loads(resp.read().decode("utf-8"))
        assert alert_data["success"] is True
        assert "active_alerts" in alert_data
        assert "history" in alert_data


def test_executive_api_edge_heartbeat_and_mouth_sync(executive_server_instance: str) -> None:
    # 1. Heartbeat POST
    hb_payload = json.dumps({
        "device_id": "EDGE-PI5-DESK-01",
        "rtt_ms": 12.4,
        "subsystems_ready": True,
        "telemetry": {"battery": "AC", "temp_c": 42.1},
    }).encode("utf-8")
    req_hb = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/heartbeat",
        data=hb_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_hb, timeout=5.0) as resp:
        assert resp.status == 200
        hb_data = json.loads(resp.read().decode("utf-8"))
        assert hb_data["success"] is True
        assert hb_data["edge_status"]["state"] == "READY"

    # 2. Mouth Sync POST (Generate)
    ms_payload = json.dumps({
        "action": "generate",
        "utterance_id": "utt_test_exec",
        "text": "Chào Anh Quanpt1, em sẵn sàng!",
        "duration_ms": 1500,
    }).encode("utf-8")
    req_ms = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/mouth-sync",
        data=ms_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_ms, timeout=5.0) as resp:
        assert resp.status == 200
        ms_data = json.loads(resp.read().decode("utf-8"))
        assert ms_data["success"] is True
        assert ms_data["timeline"]["utterance_id"] == "utt_test_exec"
        assert ms_data["timeline"]["total_duration_ms"] == 1500
        assert len(ms_data["timeline"]["frames"]) > 5

    # 3. Mouth Sync POST (Cancel)
    cancel_payload = json.dumps({
        "action": "cancel",
        "utterance_id": "utt_test_exec",
    }).encode("utf-8")
    req_cancel = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/mouth-sync",
        data=cancel_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_cancel, timeout=5.0) as resp:
        assert resp.status == 200
        cancel_data = json.loads(resp.read().decode("utf-8"))
        assert cancel_data["success"] is True
        assert cancel_data["cancelled"] is True


def test_executive_edge_telemetry_and_control(executive_server_instance: str) -> None:
    # 1. Edge Telemetry GET
    req_telem = urllib.request.Request(f"{executive_server_instance}/api/executive/edge/telemetry")
    with urllib.request.urlopen(req_telem, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert "packets_in" in data
        assert "packets_out" in data
        assert "rtt_history" in data

    # 2. Edge Control POST (Set Expression)
    ctrl_expr = json.dumps({"action": "set_expression", "state": "HAPPY", "transcript": "Mỉm cười chào Anh!"}).encode("utf-8")
    req_ctrl = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_expr,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_ctrl, timeout=5.0) as resp:
        assert resp.status == 200
        cdata = json.loads(resp.read().decode("utf-8"))
        assert cdata["success"] is True
        assert cdata["state"] == "HAPPY"

    # 2.5 Edge Control POST (Speak & Mouth-Sync)
    ctrl_speak = json.dumps({"action": "speak", "text": "Chào Anh Quanpt1! Em đang sẵn sàng hỗ trợ.", "duration_ms": 2500}).encode("utf-8")
    req_sp = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_speak,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_sp, timeout=5.0) as resp:
        assert resp.status == 200
        sdata = json.loads(resp.read().decode("utf-8"))
        assert sdata["success"] is True
        assert "timeline" in sdata
        assert len(sdata["timeline"]["frames"]) > 0

    # 2.6 Edge Control POST (Toggle Face-Only)
    ctrl_fo = json.dumps({"action": "toggle_face_only"}).encode("utf-8")
    req_fo = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_fo,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_fo, timeout=5.0) as resp:
        assert resp.status == 200
        fodata = json.loads(resp.read().decode("utf-8"))
        assert fodata["success"] is True
        assert "face_only_mode" in fodata

    # 3. Edge Control POST (Pause)
    ctrl_pause = json.dumps({"action": "pause"}).encode("utf-8")
    req_p = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_pause,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_p, timeout=5.0) as resp:
        assert resp.status == 200
        pdata = json.loads(resp.read().decode("utf-8"))
        assert pdata["success"] is True
        assert pdata["state"] == "SLEEPING"

    # 4. Edge Control POST (Resume)
    ctrl_resume = json.dumps({"action": "resume"}).encode("utf-8")
    req_r = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_resume,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_r, timeout=5.0) as resp:
        assert resp.status == 200
        rdata = json.loads(resp.read().decode("utf-8"))
        assert rdata["success"] is True
        assert rdata["state"] == "IDLE"

    # 5. Edge Control POST (Volume)
    ctrl_vol = json.dumps({"action": "set_volume", "volume": 80}).encode("utf-8")
    req_v = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_vol,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_v, timeout=5.0) as resp:
        assert resp.status == 200
        vdata = json.loads(resp.read().decode("utf-8"))
        assert vdata["success"] is True
        assert vdata["volume"] == 80

    # 6. Edge Control POST (Auto configure audio)
    ctrl_audio = json.dumps({"action": "auto_configure_audio"}).encode("utf-8")
    req_a = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_audio,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_a, timeout=5.0) as resp:
        assert resp.status == 200
        adata = json.loads(resp.read().decode("utf-8"))
        assert adata["success"] is True
        assert adata["action"] == "auto_configure_audio"

    # 7. Edge Control POST (Start Kiosk)
    ctrl_start = json.dumps({"action": "start_kiosk"}).encode("utf-8")
    req_s = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_start,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_s, timeout=5.0) as resp:
        assert resp.status == 200
        sdata = json.loads(resp.read().decode("utf-8"))
        assert sdata["success"] is True
        assert sdata["action"] == "start_kiosk"

    # 8. Edge Control POST (Close Kiosk)
    ctrl_close = json.dumps({"action": "close_kiosk"}).encode("utf-8")
    req_c = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_close,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_c, timeout=5.0) as resp:
        assert resp.status == 200
        cdata = json.loads(resp.read().decode("utf-8"))
        assert cdata["success"] is True
        assert cdata["action"] == "close_kiosk"

    # 8. Edge Control POST (Poweroff Pi)
    ctrl_pwr = json.dumps({"action": "poweroff_pi"}).encode("utf-8")
    req_pw = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/control",
        data=ctrl_pwr,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_pw, timeout=5.0) as resp:
        assert resp.status == 200
        pwdata = json.loads(resp.read().decode("utf-8"))
        assert pwdata["success"] is True
        assert pwdata["action"] == "poweroff_pi"


def test_executive_edge_files_and_actions(executive_server_instance: str) -> None:
    # 1. Edge Files GET
    req_f = urllib.request.Request(f"{executive_server_instance}/api/executive/edge/files")
    with urllib.request.urlopen(req_f, timeout=5.0) as resp:
        assert resp.status == 200
        fdata = json.loads(resp.read().decode("utf-8"))
        assert fdata["success"] is True
        assert "local_files" in fdata
        assert "remote_files" in fdata

    # 2. Edge File Upload POST
    import base64
    sample_b64 = base64.b64encode(b'{"test": true}').decode("ascii")
    up_payload = json.dumps({"filename": "test_asset.json", "content_b64": sample_b64}).encode("utf-8")
    req_up = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/files/upload",
        data=up_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_up, timeout=5.0) as resp:
        assert resp.status == 200
        up_data = json.loads(resp.read().decode("utf-8"))
        assert up_data["success"] is True
        assert up_data["filename"] == "test_asset.json"
        assert up_data["local_saved"] is True

    # 3. Edge Files Sync-All POST
    req_sync = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/files/sync-all",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_sync, timeout=5.0) as resp:
        assert resp.status == 200
        sync_data = json.loads(resp.read().decode("utf-8"))
        assert sync_data["success"] is True
        assert sync_data["synced_count"] >= 20

    # Clean up created local test asset safely on Windows
    test_path = Path("edge_client") / "assets" / "avatar" / "test_asset.json"
    if test_path.exists():
        for _ in range(10):
            try:
                test_path.unlink(missing_ok=True)
                break
            except OSError:
                time.sleep(0.05)


def test_executive_edge_startup_sequence(executive_server_instance: str) -> None:
    req = urllib.request.Request(
        f"{executive_server_instance}/api/executive/edge/startup-sequence",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        # When Pi 5 is offline, it gracefully returns success: False with descriptive message
        assert "pi5_online" in data




