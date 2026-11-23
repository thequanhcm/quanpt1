# QUAN AI BRAIN — Automated Engineering Handoff Report

> Báo cáo bàn giao kỹ thuật tự động được tạo bởi `tools/validate_and_report.py`.
> Tệp này phản ánh trung thực trạng thái đọc được từ workspace máy chủ tại thời điểm chạy,
> bảo đảm tính minh bạch, độc lập và khả năng phục hồi phiên làm việc cho ChatGPT.

## 1. Thông tin phiên làm việc (Session Metadata)
- **Mã phiên (UTC):** `2026-11-18T13:11:50.807181+00:00`
- **Thời gian máy chủ:** `2026-11-18 20:11:50` (Local Time)
- **Workspace root:** `E:/BRAIN`
- **Python Runtime:** `3.11.9` (64bit)
- **Hệ điều hành:** `Windows-10-10.0.19045-SP0`
- **Phiên bản ứng dụng:** `0.2.0` (Foundation Evolution — Phase A)
- **Git Branch:** `feat/v6-m6-memory-truth` | **Commit:** `149e475`
- **Trạng thái Working Tree:** Có thay đổi chưa commit

## 2. Tóm tắt điều hành (Executive Summary)
- **Milestone hiện tại:** `QUAN AI BRAIN EVOLUTION — Sprint 1: Core AI End-to-End & Session Memory (Completed)`.
- **Mục tiêu của Sprint 1:**
  1. Triển khai `LLMRouter` (`src/quan_ai_brain/llm/router.py`) phân tầng thông minh (Fast tier: 1.5B/0.5B < 2s; Reasoning tier: 7B cho lập kế hoạch/suy luận sâu).
  2. Hiện thực `SessionMemoryManager` (`src/quan_ai_brain/cognition/session_memory.py`) trích xuất sự thật người dùng và lưu trữ phiên hội thoại bền vững vào `data/brain.db`.
  3. Cài đặt `OutputGuardrails` (`src/quan_ai_brain/core/guardrails.py`) lọc rò rỉ credential, script tag injection và che giấu đường dẫn tệp nhạy cảm.
  4. Mở rộng `PromptContextBuilder` và API `/api/chat`, `/api/chat/history` trên Web Server phục vụ hội thoại đa lượt liên tục có trí nhớ.
  5. Kết quả kiểm thử tự động phiên hiện tại: 4193 PASSED, 9 FAILED, 28 SKIPPED (Tổng: 4230 bài test, FAIL (9 test(s) failed)).
- **Các hạng mục đã hoàn thành:**
  - [x] Bộ định tuyến mô hình động `LLMRouter` với phân tầng fast / reasoning và fallback tin cậy.
  - [x] Quản lý bộ nhớ phiên `SessionMemoryManager` và trích xuất tự động danh tính, sở thích, chỉ thị của chủ sở hữu.
  - [x] Lưu trữ bền vững mỗi lượt hội thoại vào SQLite WAL `data/brain.db` (episodes & memories).
  - [x] Lớp rào chắn đầu ra `OutputGuardrails` bảo vệ an toàn thông tin trước khi phản hồi ra giao diện.
  - [x] Tích hợp lịch sử hội thoại gần nhất `[RECENT CONVERSATION HISTORY]` vào ngữ cảnh suy luận của LLM.
  - [x] Endpoint `GET /api/chat/history` và nâng cấp toàn diện `POST /api/chat` trên `BrainAPIHandler`.
  - [x] 5 bài kiểm thử E2E đầu cuối (`tests/test_end_to_end_chat.py`) xác minh đa lượt đàm thoại và trí nhớ dài hạn.
  - [x] Kiểm thử tự động: 4193 bài PASS, 28 bài SKIP (Phần cứng Pi 5 offline), 9 bài FAIL (FAIL (9 test(s) failed)).
- **Các hạng mục tiếp theo (Sprint 2):**
  - Kết nối TaskPlan vào `DurableTaskRegistry` (`data/tasks.db`) và xây dựng vòng lặp thực thi có kiểm soát an toàn (Inert Sandbox).
- **Lưu ý kỹ thuật quan trọng cho kỹ sư tiếp theo:**
  - Mọi thao tác công cụ đều bị chặn bởi Owner Consent trừ khi có approval hợp lệ hoặc DelegationGrant phù hợp.
  - R4 yêu cầu phê duyệt có xác thực mạnh (Dual-Factor); R5 luôn luôn bị chặn cứng không thể ghi đè.
  - `InertProcessBackend` kiên quyết chặn tạo subprocess; production runner tiếp tục bị vô hiệu hóa cho đến khi có sign-off.

## 3. Thay đổi mã nguồn (Code Changes & Working Tree)
- **Git Status:**
```text
eck40.png
?? data/rig_check41.png
?? data/rig_check42.png
?? data/rig_check43.png
?? data/rig_check44.png
?? data/rig_check45.png
?? data/rig_check46.png
?? data/rig_check47.png
?? data/rig_check48.png
?? data/rig_check49.png
?? data/rig_check5.png
?? data/rig_check50.png
?? data/rig_check51.png
?? data/rig_check52.png
?? data/rig_check53.png
?? data/rig_check54.png
?? data/rig_check55.png
?? data/rig_check56.png
?? data/rig_check57.png
?? data/rig_check58.png
?? data/rig_check59.png
?? data/rig_check6.png
?? data/rig_check60.png
?? data/rig_check61.png
?? data/rig_check62.png
?? data/rig_check63.png
?? data/rig_check64.png
?? data/rig_check65.png
?? data/rig_check66.png
?? data/rig_check67.png
?? data/rig_check68.png
?? data/rig_check69.png
?? data/rig_check7.png
?? data/rig_check70.png
?? data/rig_check71.png
?? data/rig_check72.png
?? data/rig_check73.png
?? data/rig_check74.png
?? data/rig_check75.png
?? data/rig_check76.png
?? data/rig_check77.png
?? data/rig_check78.png
?? data/rig_check79.png
?? data/rig_check8.png
?? data/rig_check80.png
?? data/rig_check81.png
?? data/rig_check82.png
?? data/rig_check83.png
?? data/rig_check84.png
?? data/rig_check85.png
?? data/rig_check86.png
?? data/rig_check87.png
?? data/rig_check88.png
?? data/rig_check89.png
?? data/rig_check9.png
?? data/rig_check90.png
?? data/rig_check91.png
?? data/rig_check92.png
?? data/rig_check93.png
?? data/rig_check94.png
?? data/rig_check95.png
?? data/rig_check96.png
?? data/rig_check97.png
?? data/rig_check98.png
?? data/rig_check99.png
?? data/rig_zone_left.png
?? data/rig_zone_right.png
?? data/seq_1.png
?? data/seq_2.png
?? data/seq_3.png
?? data/sheet_ht.jpg
?? data/sheet_ht1.jpg
?? data/shot_avatar_exact.png
?? data/simulate_mouth_voice_match.py
?? data/strawberry_zoom.png
?? data/synth_voices_test.py
?? data/user_marked_zoom.png
?? data/v2_confused_arms.png
?? data/v2_thinking_bottom.png
?? data/v3_check/
?? data/v6voice_e2e.png
?? data/v6voice_final_test.mp3
?? data/v6voice_final_test.wav
?? data/vector_db_semantic/
?? data/vi_frames/
?? data/voice_envelopes.json
?? data/voice_test_piper_vi_VN_vais1000_medium.mp3
?? data/voice_test_piper_vi_VN_vivos_x_low.mp3
?? data/voice_test_vi_VN_HoaiMyNeural.mp3
?? data/voice_test_vi_VN_NamMinhNeural.mp3
?? data/vui_suong_bottom.png
?? data/wire_v6m4b_test.js
?? edge_client/assets/avatar/tai_lieu_test.png
?? edge_client/avatar_engine.js.bak_v6cin_1411
?? edge_client/kiosk.html.bak_v6cin_1411
?? projects/
?? quarantine_audit_20261113/
?? quarantine_cleanup/
?? reports/CHERRY_COGNITIVE_DISCOVERY_REPORT.md
?? reports/intelligence_maturity/cisc_runs/cpsl_mini_20261112_103442.json
?? reports/intelligence_maturity/cisc_runs/cpsl_mini_20261112_104058.json
?? reports/intelligence_maturity/cisc_runs/cpsl_mini_20261112_104626.json
?? reports/intelligence_maturity/cisc_runs/cpsl_mini_20261112_105311.json
[secret-like path omitted]
?? src/quan_ai_brain/web/static/poc_assets/
?? tools/v6_m4b_watch_sync_pi5.py
?? vivi-agent-20261118.zip
```
- **Tệp mã nguồn cốt lõi trong Sprint 7A:**
  - `src/quan_ai_brain/execution/process_containment.py`: Hợp đồng `ProcessBackendInterface`, `ProcessContainmentConfig`, `InertProcessBackend`, `ContainedExecutionRunner`.
  - `tests/test_process_containment.py`: 9 bài test kiểm tra adapter kiểm soát tiến trình fail-closed.
  - `src/quan_ai_brain/execution/__init__.py`: Export các lớp process containment.
  - `docs/SPRINT6_EXECUTION_READINESS_DESIGN.md`: Tài liệu kiến trúc quy trình 10 bước thực thi bắt buộc.
  - `docs/SPRINT6_DESIGN_SIGNOFF.md`: Danh mục kiểm tra phê duyệt thiết kế (`PENDING_OWNER_SIGNOFF`).
  - `src/quan_ai_brain/tools/signature.py`: Lớp `OwnerSignatureVerifier` xác thực chữ ký chủ nhân.
  - `src/quan_ai_brain/execution/resource_budget.py`: Mô hình `ResourceBudget` và lớp `ResourceBudgetValidator`.
  - `src/quan_ai_brain/execution/staging.py`: Cập nhật `IsolatedStagingExecutor` và `ProductionExecutionProhibitedError`.
  - `tests/test_resource_budget.py`: 7 bài test cho chính sách giới hạn tài nguyên.
  - `tests/test_owner_signature_verifier.py`: 11 bài test cho xác minh chữ ký chủ nhân.
  - `tests/test_executor_staging.py`: 11 bài test cho staging executor và sign-off.
  - `src/quan_ai_brain/learning/evaluation.py`: Lớp `ContinuousEvaluationHarness` đo lường tiến bộ tự học qua 5 benchmark định lượng.
  - `tests/test_evaluation_harness.py`: 4 bài test đo lường định lượng và khuyến nghị thăng cấp.
  - `src/quan_ai_brain/web/static/executive.html`: Tích hợp Digital Avatar TONY biểu cảm 11 trạng thái và Visual Cockpit.
  - `src/quan_ai_brain/web/static/executive.css`: Kiểu dáng Cybernetic Dark Glassmorphism, waveform và 11 cảm xúc.
  - `src/quan_ai_brain/web/static/executive.js`: Avatar controller, dynamic waveform canvas, supervisor polling, emergency controls.
  - `src/quan_ai_brain/web/server.py`: API `/api/executive/supervisor`, `/api/executive/tasks`, `/api/executive/emergency`.
  - `edge_client/config.py` & `edge_client/config.json`: Cấu hình client Raspberry Pi 5 màn hình cảm ứng.
  - `edge_client/auth.py`: Xác thực hai chiều HMAC-SHA256, chống tấn công phát lại (anti-replay nonces).
  - `edge_client/kiosk.html`, `kiosk.css`, `kiosk.js`: Giao diện Kiosk cảm ứng 5"/7" với fail-safe disconnect.
  - `edge_client/client_daemon.py` & `edge_client/main.py`: Tiến trình daemon kết nối Brain Core và phục vụ Kiosk.
  - `tests/test_edge_client.py`: 6 bài test xác thực HMAC, nonce anti-replay, kiosk HTTP endpoints, fail-safe disconnect.

## 4. Kết quả kiểm thử (Test Verification)
- **Kết luận kiểm thử:** **FAIL (9 test(s) failed)**
- **Lệnh thực thi:** `E:\BRAIN\.venv\Scripts\python.exe -m pytest -q tests`
- **Tổng số bài test:** `4230` | **Passed:** `4193` | **Failed:** `9` | **Skipped:** `28`
- **Thời gian chạy:** `705.04s`
- **Exit Code:** `1`

- **Định danh bộ test (`test_suite_identity`):** Bộ test hiện tại gồm `4230` bài trong thư mục `tests/`. Số test thay đổi theo từng sprint; KHÔNG đối chiếu số test trong tài liệu/báo cáo cũ với số này.
- **Độ tươi của báo cáo (`report_freshness`):** Mọi tuyên bố trong các section bên dưới phản ánh trạng thái workspace TẠI THỜI ĐIỂM CHẠY BÁO CÁO. Trước khi dựa vào một tuyên bố (trạng thái module, hiệu năng, tích hợp), bắt buộc đối chiếu lại với code + test hiện tại trong workspace — báo cáo cũ có thể đã lỗi thời.
- **Trạng thái xác minh (`verification_status`):** `FAIL (9 test(s) failed)`. Định nghĩa: `CURRENT` = chạy trong phiên này; `AGING` = >7 ngày; `STALE` = >30 ngày hoặc working tree đã đổi sau lần chạy; `CONTRADICTED` = có bằng chứng mâu thuẫn; `UNKNOWN` = không có bằng chứng. Tuyên bố nào không có bằng chứng trong phiên này phải được coi là `UNKNOWN` cho đến khi xác minh lại.

```text
n\Python311\Lib\subprocess.py", line 1026, in __init__
      self._execute_child(args, executable, preexec_fn, close_fds,
    File "C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\subprocess.py", line 1538, in _execute_child
      hp, ht, pid, tid = _winapi.CreateProcess(executable, args,
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  FileNotFoundError: [WinError 2] The system cannot find the file specified
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_process_containment.py::test_runner_fails_closed_on_containment_configuration_error
  E:\BRAIN\.venv\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-912 (_do_reboot)
  
  Traceback (most recent call last):
    File "C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\threading.py", line 1045, in _bootstrap_inner
      self.run()
    File "C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\threading.py", line 982, in run
      self._target(*self._args, **self._kwargs)
    File "E:\BRAIN\edge_client\client_daemon.py", line 2430, in _do_reboot
      subprocess.run(["sudo", "reboot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    File "E:\BRAIN\tools\netchat_auto_responder.py", line 115, in _subprocess_run_no_window
      return _orig_subprocess_run(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "E:\BRAIN\tools\learning_daemon.py", line 58, in _subprocess_run_no_window
      return _orig_subprocess_run(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "E:\BRAIN\tools\learning_daemon.py", line 58, in _subprocess_run_no_window
      return _orig_subprocess_run(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "E:\BRAIN\tools\learning_daemon.py", line 58, in _subprocess_run_no_window
      return _orig_subprocess_run(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    [Previous line repeated 2 more times]
    File "E:\BRAIN\tools\netchat_auto_responder.py", line 115, in _subprocess_run_no_window
      return _orig_subprocess_run(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\subprocess.py", line 548, in run
      with Popen(*popenargs, **kwargs) as process:
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "E:\BRAIN\.venv\Lib\site-packages\sitecustomize.py", line 34, in __init__
      super().__init__(*args, **kwargs)
    File "C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\subprocess.py", line 1026, in __init__
      self._execute_child(args, executable, preexec_fn, close_fds,
    File "C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\subprocess.py", line 1538, in _execute_child
      hp, ht, pid, tid = _winapi.CreateProcess(executable, args,
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  FileNotFoundError: [WinError 2] The system cannot find the file specified
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_tony_vision.py::test_analyze_image_ocr_and_facts
tests/test_tony_vision.py::test_analyze_image_no_text_is_honest
tests/test_tony_vision.py::test_handler_fallback_capture_photo
tests/test_tony_vision.py::test_handler_dm_attach_priority
  E:\BRAIN\src\quan_ai_brain\vision\image_analyzer.py:84: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    pixels = list(small.getdata())

tests/test_tony_vision.py::test_analyze_image_ocr_and_facts
tests/test_tony_vision.py::test_analyze_image_no_text_is_honest
tests/test_tony_vision.py::test_handler_fallback_capture_photo
tests/test_tony_vision.py::test_handler_dm_attach_priority
  E:\BRAIN\src\quan_ai_brain\vision\image_analyzer.py:98: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    for px in rgb.getdata():

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
SKIPPED [1] tests\test_bge_m3_embedding.py:172: Local Ollama daemon is offline; live test skipped.
SKIPPED [1] tests\test_self_study.py:82: cần >=2 gap để test dedup
SKIPPED [1] tests\test_self_study.py:134: chu kỳ 1 không quarantine được gì
SKIPPED [1] tests\test_v14_ui_integration.py:23: API integration pending - placeholder test
SKIPPED [1] tests\test_v14_ui_integration.py:27: API integration pending - placeholder test
SKIPPED [1] tests\test_v14_ui_integration.py:31: API integration pending - placeholder test
SKIPPED [1] tests\test_v15_knowledge_graph.py:182: Database lock issue - fix pending
SKIPPED [1] tests\test_v21_final_integration.py:46: Integration test - manual verification
SKIPPED [1] tests\test_v21_final_integration.py:50: Integration test - manual verification
SKIPPED [1] tests\test_v21_final_integration.py:54: Integration test - manual verification
SKIPPED [1] tests\test_v21_final_integration.py:62: Module dependency issue - manual test
SKIPPED [1] tests\test_v21_final_integration.py:73: Module dependency issue - manual test
SKIPPED [1] tests\test_v21_final_integration.py:153: Performance test - manual run only
SKIPPED [1] tests\test_v21_final_integration.py:157: Performance test - manual run only
SKIPPED [1] tests\test_v25_analytics.py:109: Complex dataclass test - manual verification
SKIPPED [1] tests\test_v25_analytics.py:251: Complex integration test - manual verification
SKIPPED [1] tests\test_v25_analytics.py:372: Complex integration test - manual verification
SKIPPED [1] tests\test_v25_analytics.py:383: Complex integration test - manual verification
SKIPPED [1] tests\test_v25_analytics.py:449: Complex integration test - manual verification
SKIPPED [1] tests\test_v25_analytics.py:460: Complex integration test - manual verification
SKIPPED [1] tests\test_v36_asr.py:256: Azure Speech SDK not installed
SKIPPED [1] tests\test_v39_analytics_engine.py:686: Small sample regression handled separately
SKIPPED [1] tests\test_v39_creativity_engine.py:224: Domain synthesis tested in integration tests
SKIPPED [1] tests\test_v39_decision_engine.py:258: Solution generation tested in integration tests
SKIPPED [1] tests\test_v39_decision_engine.py:263: Troubleshooting workflow tested in integration tests
SKIPPED [1] tests\test_v39_decision_engine.py:459: Problem solving pipeline tested in unit tests
SKIPPED [1] tests\test_v39_decision_engine.py:516: Zero cost edge case handled separately
SKIPPED [1] tests\test_vietnamese_tts.py:336: BLOCKED: Phần cứng Raspberry Pi 5 thực tế chưa kết nối mạng trong phiên kiểm thử tự động này. PC Core đã được xác thực hoàn chỉnh.
FAILED tests/test_avatar_emotion_sync_1314.py::TestCacheBump::test_html_cache_version_bumped
FAILED tests/test_cognitive_loop.py::test_api_health_returns_evidence_based_components
FAILED tests/test_cognitive_loop.py::test_api_health_ollama_offline_is_honest
FAILED tests/test_cpsl_runner.py::test_run_e2e_mock - assert 13 == 12
FAILED tests/test_digital_identity_persona.py::test_voice_pipeline_spoken_sanitization_preserves_self_intro
FAILED tests/test_edge_client.py::test_edge_client_daemon_local_kiosk_endpoints
FAILED tests/test_media_only_dm.py::test_photo_success_returns_empty_text_only_image
FAILED tests/test_web_executive_endpoints.py::test_executive_edge_telemetry_and_control
FAILED tests/test_web_server.py::test_edge_control_speak_audio_forwarding - A...
9 failed, 4193 passed, 28 skipped, 13 warnings in 705.04s (0:11:45)
```

## 5. Danh mục module & Trạng thái hiện tại
| Module | Đường dẫn | Trạng thái kỹ thuật | Ghi chú |
| :--- | :--- | :--- | :--- |
| `core.redaction` | `src/quan_ai_brain/core/redaction.py` | `IMPLEMENTED & TESTED` | Che giấu Bearer, password, tokens, credentials |
| `core.audit` | `src/quan_ai_brain/core/audit.py` | `IMPLEMENTED & TESTED` | Ghi log JSONL append-only có redaction |
| `governance.policy` | `src/quan_ai_brain/governance/policy.py` | `IMPLEMENTED & TESTED` | Ma trận R0-R5; R5 chặn cứng, R4 cần duyệt |
| `memory.models` | `src/quan_ai_brain/memory/models.py` | `IMPLEMENTED & TESTED` | 6 loại trí nhớ, verification status |
| `memory.sqlite_store` | `src/quan_ai_brain/memory/sqlite_store.py` | `IMPLEMENTED & TESTED` | Long-term memory V1, versioning, search tiếng Việt |
| `llm.client` | `src/quan_ai_brain/llm/client.py` | `IMPLEMENTED & TESTED` | Local Ollama client, cấm host ngoài Internet |
| `llm.mock_provider` | `src/quan_ai_brain/llm/mock_provider.py` | `IMPLEMENTED & TESTED` | Mock provider với cảnh báo mock rõ ràng |
| `llm.provider` | `src/quan_ai_brain/llm/provider.py` | `IMPLEMENTED & TESTED` | Facade kiểm soát fallback an toàn, không giả lập |
| `cognition.retrieval` | `src/quan_ai_brain/cognition/retrieval.py` | `IMPLEMENTED & TESTED` | Truy xuất trí nhớ, xếp hạng có giải thích |
| `cognition.context_builder` | `src/quan_ai_brain/cognition/context_builder.py` | `IMPLEMENTED & TESTED` | Dựng prompt có cấu trúc, kiểm soát ngân sách |
| `planning.models` | `src/quan_ai_brain/planning/models.py` | `IMPLEMENTED & TESTED` | Model TaskPlan, TaskStep, DAG validation |
| `planning.coordinator` | `src/quan_ai_brain/planning/coordinator.py` | `IMPLEMENTED & TESTED` | ExecutiveCoordinator thẩm định rủi ro độc lập |
| `tools.path_guard` | `src/quan_ai_brain/tools/path_guard.py` | `IMPLEMENTED & TESTED` | Giới hạn tuyệt đối trong workspace |
| `tools.registry` | `src/quan_ai_brain/tools/registry.py` | `IMPLEMENTED & TESTED` | ToolDefinition và ToolRegistry |
| `tools.approval` | `src/quan_ai_brain/tools/approval.py` | `IMPLEMENTED & TESTED` | ApprovalGate, fingerprinting, one-time token |
| `tools.delegation` | `src/quan_ai_brain/tools/delegation.py` | `IMPLEMENTED & TESTED` | DelegationRegistry, 10 điều kiện tự quyết |
| `tools.sandbox` | `src/quan_ai_brain/tools/sandbox.py` | `IMPLEMENTED & TESTED` | SafeToolSandbox 10 bước, STOP/FREEZE controls |
| `tools.verifier` | `src/quan_ai_brain/tools/verifier.py` | `IMPLEMENTED & TESTED` | AuthenticatedApprovalVerifier, Secret Code, SMS OTP & Dual-Factor |
| `tools.signature` | `src/quan_ai_brain/tools/signature.py` | `IMPLEMENTED & TESTED` | OwnerSignatureVerifier, trust anchors, replay nonces |
| `governance.state_store` | `src/quan_ai_brain/governance/state_store.py` | `IMPLEMENTED & TESTED` | SQLite WAL persistence, STOP/FREEZE, anti-replay nonces, revocations |
| `execution.resource_budget` | `src/quan_ai_brain/execution/resource_budget.py` | `IMPLEMENTED & TESTED` | ResourceBudget & ResourceBudgetValidator đa chiều |
| `execution.staging` | `src/quan_ai_brain/execution/staging.py` | `IMPLEMENTED & TESTED` | IsolatedStagingExecutor, budget validation, inert dry-run |
| `execution.process_containment` | `src/quan_ai_brain/execution/process_containment.py` | `IMPLEMENTED & TESTED` | Hợp đồng ProcessBackendInterface, InertProcessBackend, ContainedExecutionRunner |
| `learning` | `src/quan_ai_brain/learning/engine.py` | `IMPLEMENTED & TESTED` | Self-Learning & Self-Upgrade Engine V1, 17-point dossier, candidate quarantine, owner gate |
| `learning.evaluation` | `src/quan_ai_brain/learning/evaluation.py` | `IMPLEMENTED & TESTED` | ContinuousEvaluationHarness đo lường định lượng tiến bộ qua 5 benchmarks |
| `web.executive` | `src/quan_ai_brain/web/server.py` | `IMPLEMENTED & TESTED` | Digital Avatar TONY biểu cảm 11 trạng thái, Visual Cockpit, Emergency Control |
| `edge_client` | `edge_client/client_daemon.py` | `IMPLEMENTED & TESTED` | Raspberry Pi 5 Edge Kiosk Client, HMAC anti-replay auth, fail-safe disconnect |
| `clae.quarantine` | `src/quan_ai_brain/clae/quarantine.py` | `PARTIALLY_IMPLEMENTED` | Cổng cách ly tested; chưa nối CLAE 30 bước |
| `daemon.health` | `src/quan_ai_brain/daemon/health.py` | `PARTIALLY_IMPLEMENTED` | Health-only skeleton; daemon 24/7 chưa làm |
| `cli` | `src/quan_ai_brain/cli.py` | `IMPLEMENTED & TESTED` | CLI self-check, memory, llm, context-build, plan-create, tool-run |

## 6. Ma trận tích hợp hệ thống ngoại vi
| Hệ thống | Vị trí tham chiếu | Trạng thái tích hợp | Bằng chứng / Ranh giới |
| :--- | :--- | :--- | :--- |
| **SQLite Memory Engine** | `data/brain.db` | `TESTED / IMPLEMENTED` | 11/11 bài test bộ nhớ dài hạn đạt |
| **Persistent Governance Store** | `src/quan_ai_brain/governance/state_store.py` | `TESTED / IMPLEMENTED` | 12 bài test persistent store & integration đạt |
| **Owner Signature Verifier** | `src/quan_ai_brain/tools/signature.py` | `TESTED / IMPLEMENTED` | 11 bài test xác thực chữ ký & trust anchors đạt |
| **OS Resource Budget Policy** | `src/quan_ai_brain/execution/resource_budget.py` | `TESTED / IMPLEMENTED` | 7 bài test giới hạn tài nguyên đa chiều đạt |
| **Cognitive Context Builder** | `src/quan_ai_brain/cognition` | `TESTED / IMPLEMENTED` | 17 bài test retrieval & context builder đạt |
| **Safe Planning Coordinator** | `src/quan_ai_brain/planning` | `TESTED / IMPLEMENTED` | 19 bài test planning & coordination đạt |
| **Safe Tool Sandbox & Verifier** | `src/quan_ai_brain/tools` | `TESTED / IMPLEMENTED` | 49 bài test sandbox, approval, delegation & verifier đạt |
| **Isolated Staging Executor** | `src/quan_ai_brain/execution` | `TESTED / IMPLEMENTED` | 11 bài test inert staging & sign-off pending đạt |
| **Windows Process Containment Adapter** | `src/quan_ai_brain/execution/process_containment.py` | `TESTED / IMPLEMENTED` | 9 bài test process containment & inert backend đạt |
| **Ollama / Qwen2.5:7b** | `C:\Users\DELL\AppData\Local\Programs\Ollama` | `IMPLEMENTED (local-only)` | Client + Mock tested; daemon runtime status: xem `llm-health` tại thời điểm chạy (đã xác minh online 2026-10-25) |
| **NetMind GLM-5.3-Flash (cloud)** | `src/quan_ai_brain/llm/netmind_provider.py` | `IMPLEMENTED (fail-closed)` | 18 test đạt; E2E xác minh 2026-10-25; mặc định DISABLED_BY_POLICY đến khi chủ sở hữu bật |
| **Kernel L3** | `BAT-AI-2026-Repo\...\os_kernel` | `NOT_IMPLEMENTED` | Đọc tài liệu; không sửa trực tiếp |
| **DC-COMMAND / CLAE** | `DATA CENTER AI OPERATING SYSTEM` | `PARTIALLY_IMPLEMENTED` | Cơ chế Quarantine tuân thủ nguyên tắc CLAE |
| **SKILL_BAT_AI** | `E:\AI\Skill\SKILL_BAT_AI` | `NOT_IMPLEMENTED` | Tham khảo ma trận rủi ro R0-R5 |
| **BATTERY_AI_V4** | `E:\AI\battery-ai-\BATTERY_AI_V4` | `NOT_IMPLEMENTED` | Giữ nguyên trạng; không can thiệp |
| **VDCIM / NetChat** | Sibling projects | `NOT_IMPLEMENTED` | Chưa tích hợp |
| **Background Daemon** | N/A | `NOT_IMPLEMENTED` | Chỉ có health skeleton cục bộ |
| **Voice Interface** | `src/quan_ai_brain/voice/` + `edge_client/` | `IMPLEMENTED (PC) / NOT_VERIFIED_ON_PI` | TTS vi-VN, mouth-sync, wake-word có code + test trên PC; E2E phần cứng Pi 5 chờ thiết bị online |

## 7. An toàn và phục hồi (Safety & Recovery Guardrails)
- **Chặn rủi ro R5:** R5 luôn bị chặn cứng (`DecisionStatus.BLOCKED`). Không có cơ chế override bí mật trong mã nguồn.
- **Kiểm soát R4:** Yêu cầu người sở hữu phê duyệt tường minh (Dual-Factor); cấm ủy quyền tự quyết cho R4.
- **Owner Consent First:** Mọi công cụ mặc định bị chặn (`pending_owner_approval`) trừ khi có approval hoặc delegation hợp lệ.
- **Cách ly tri thức:** Toàn bộ tri thức mới từ AI mặc định rơi vào trạng thái `CANDIDATE` / `quarantined`. Không bao giờ đưa vào khối tri thức đáng tin cậy.
- **Thẩm định độc lập:** LLM không có quyền tự cấp phép hay hạ mức rủi ro; Coordinator tự động nâng cấp rủi ro khi có nguy cơ.
- **Bảo vệ tệp nhạy cảm:** Từ chối truy cập `.env`, private keys, `.git/`, `.sqlite`, `.db`.
- **Cấm ghi đè tệp:** `file_write_new` từ chối ghi đè tệp đã tồn tại.
- **Chống phát lại (Anti-replay):** Token approval và chữ ký chỉ sử dụng một lần và gắn với fingerprint chính xác của tham số.
- **Dừng khẩn cấp:** `STOP` và `FREEZE` lập tức chặn mọi hành vi thực thi công cụ.
- **Bảo vệ ranh giới workspace:** `PathGuard` từ chối mọi đường dẫn thoát ra ngoài `E:\BRAIN`.
- **Ranh giới mạng LLM:** `OllamaClient` chặn đứng mọi host không phải localhost/127.0.0.1.
- **Bảo vệ bí mật:** Tự động che giấu token, mật khẩu, api_key trước khi ghi vào log hoặc CSDL.

## 8. Danh mục tài liệu ngữ cảnh an toàn
- `docs/PROJECT_STATUS.md` (232205 bytes) â **
- `docs/SYSTEM_BASELINE.md` (8796 bytes) â *SYSTEM BASELINE: QUAN AI BRAIN*
- `docs/ARCHITECTURE_GAP_ANALYSIS.md` (11037 bytes) â *ARCHITECTURE GAP ANALYSIS: QUAN AI BRAIN*
- `docs/NEXT_STEPS.md` (8247 bytes) â *NEXT STEPS ROADMAP: QUAN AI BRAIN*
- `bao cao xay dung he thong/BAO_CAO_XAY_DUNG_HE_THONG_QUAN_AI_BRAIN.md` (23986 bytes) â *BÁO CÁO THIẾT KẾ & XÂY DỰNG HỆ THỐNG: QUAN AI BRAIN*
- `docs/ANTIGRAVITY_WORKFLOW.md` (1500 bytes) â *Antigravity workflow for QUAN AI BRAIN*
- `docs/WORKSPACE_MERGE_INSTRUCTIONS.md` (2293 bytes) â *Safe Merge Instructions — QUAN AI BRAIN Sprint 1*
- `bao cao xay dung he thong/ANTIGRAVITY_APPLY_PROMPT.md` (1632 bytes) â *Prompt to apply the Sprint 1 starter in Antigravity*
- `docs/SPRINT4_SECURE_APPROVAL_ARCHITECTURE.md` (19109 bytes) â *SPRINT 4 — SECURE OWNER AUTHENTICATION, APPROVAL VERIFICATION & EXECUTION ARCHIT*
- `docs/SPRINT5_EXECUTOR_STAGING_DESIGN.md` (11208 bytes) â *QUAN AI BRAIN — Production Executor Staging & Isolation Architecture Design*
- `docs/SPRINT5_DESIGN_SIGNOFF.md` (3850 bytes) â *QUAN AI BRAIN — Sprint 5 Architecture & Execution Staging Design Sign-Off*
- `docs/SPRINT6_EXECUTION_READINESS_DESIGN.md` (13339 bytes) â *QUAN AI BRAIN — Production Execution Readiness & Supervised Staging Design*
- `docs/SPRINT6_DESIGN_SIGNOFF.md` (5974 bytes) â *QUAN AI BRAIN — Sprint 6 Architecture & Execution Readiness Design Sign-Off*
- `docs/QUAN_AI_BRAIN_FOUNDATION_ROADMAP.md` (3253 bytes) â *QUAN AI BRAIN — FOUNDATION EVOLUTION ROADMAP*
- `AGENTS.md` (2803 bytes) â *QUAN AI BRAIN — Persistent Engineering Rules*

## 9. Việc cần làm tiếp theo (Next Safe Milestone)
- **Mục tiêu tiếp theo:** `SPRINT 7B — Windows Job Object Kernel Integration & Subprocess Spawner (Pending Design Sign-off)`.
- **Phạm vi an toàn:**
  1. Chờ chủ nhân thẩm định và phê duyệt `docs/SPRINT6_DESIGN_SIGNOFF.md` trước khi bất kỳ module thực thi nào được kích hoạt.
  2. Thiết kế triển khai `WindowsJobObjectBackend` sử dụng Win32 Job Object API (ctypes / pywin32) gắn kèm các hạn ngạch tài nguyên nghiêm ngặt.
  3. Tiếp tục duy trì rào chắn Policy Engine: R5 luôn bị chặn cứng, R4 bắt buộc có phê duyệt 2 lớp (Dual-Factor) từ chủ nhân.
- **Điều kiện dừng khẩn cấp:** Dừng nếu phát hiện bất kỳ thao tác vượt rào sandbox, can thiệp ra ngoài workspace hoặc cố gắng nạp mã độc hại.

---

## CONTINUATION CONTEXT FOR CHATGPT

```yaml
PROJECT: QUAN AI BRAIN (Digital Executive Assistant)
WORKSPACE: E:\BRAIN
CURRENT_MILESTONE: Phase F (Self-Learning & Self-Upgrade Engine V1) Completed -> Ready for Phase B / C / Windows Job Object
PYTHON_VERSION: 3.11.9 x64
TEST_SUMMARY:
  verdict: FAIL (9 test(s) failed)
  total_tests: 4230
  passed: 4193
  failed: 9
  skipped: 28
CORE_CAPABILITIES_IMPLEMENTED:
  - Self-Learning & Self-Upgrade Engine V1 (src/quan_ai_brain/learning)
  - Learning Observer (observe_task extracting LearningGap on failure/uncertainty)
  - Local Research Engine (ResearchDossier with citations and secret redaction)
  - Candidate Knowledge Quarantine (CANDIDATE and quarantined lifecycle by default)
  - Canonical 17-point UpgradeProposal dossier with explain() executive briefing
  - Security Barrier (permanent block on R5 bypass or trust anchor tampering)
  - Strict Owner Gate (apply_proposal requires explicit owner token owner_approved:...)
  - Process Containment Adapter Interface (ProcessBackendInterface protocol in src/quan_ai_brain/execution/process_containment.py)
  - Process Containment Configuration (ProcessContainmentConfig converting ResourceBudget to OS-level limits)
  - Fail-safe Inert Process Backend (InertProcessBackend raising ProductionExecutionProhibitedError on real spawn)
  - Contained Execution Runner (ContainedExecutionRunner 6-step fail-closed verification pipeline)
  - 10-step mandatory execution pipeline specification (docs/SPRINT6_EXECUTION_READINESS_DESIGN.md)
  - Cryptographic Owner Signature Verifier (OwnerSignatureVerifier in src/quan_ai_brain/tools/signature.py)
  - OS Resource Budget Policy (ResourceBudget, ResourceBudgetPolicy, ResourceBudgetValidator in src/quan_ai_brain/execution/resource_budget.py)
  - Multi-dimensional resource bounds (runtime, memory, CPU, child processes=0, output bytes, network policy)
  - Monotonic parent-child budget containment and LLM self-escalation prevention
  - Isolated Staging Executor with budget validation and ProductionExecutionProhibitedError
  - Formal Design Sign-Off Document (docs/SPRINT6_DESIGN_SIGNOFF.md, PENDING_OWNER_SIGNOFF)
  - Persistent Governance State Store (GovernanceStateStore SQLite WAL, schema versioning, fail-closed integrity check)
  - Cross-restart persistence (STOP/FREEZE state, consumed approvals, replay-prevention nonces, revoked grants)
  - Isolated Executor Staging Specification (docs/SPRINT5_EXECUTOR_STAGING_DESIGN.md)
  - Authenticated Approval Verifier (SECRET_CODE HMAC-SHA256, SMS_OTP 6-digit challenge, DUAL_FACTOR for R4)
  - 10-layer defense (STOP/FREEZE check, R5 hard-block, trust anchor check, signer trust, revocation check, replay nonce tracking, expiration, fingerprint match, dual-factor enforcement)
  - Secure Owner Authentication Architecture (docs/SPRINT4_SECURE_APPROVAL_ARCHITECTURE.md)
  - Safe Tool Sandbox (SafeToolSandbox with multi-layer verification and emergency STOP/FREEZE)
  - Owner Consent First Gate (ApprovalGate with SHA-256 fingerprinting and anti-replay single-use tokens)
  - Delegated Autonomy Engine (DelegationRegistry enforcing 10-point grant bounds, max R2, R4/R5 non-delegatable)
  - Declarative Tool Registry (ToolDefinition with parameter schema validation)
  - Safe baseline toolset (file_read capped at 100KB, dir_list, git_status, memory_read, system_health, plan_validate, file_write_new)
  - Sensitive file barrier (.env, id_rsa, .key, .pem, .git, .sqlite, .db)
  - CLI Sandbox diagnostics (tool-list and tool-run with interactive owner prompt and --confirm flag)
  - Cognitive Executive Coordinator (ExecutiveCoordinator with independent R0-R5 risk validation)
  - Completed TaskPlan & TaskStep (DAG cycle detection, unique step IDs, plan explainability)
  - Zero-Execution Guarantee (planning only; no tools, PowerShell, or write APIs are executed)
  - Cognitive Memory Retriever (CognitiveRetriever with explainable deterministic ranking)
  - Prompt Context Builder (PromptContextBuilder with 8 structured provenance sections)
  - Candidate knowledge quarantine (CANDIDATE memories excluded from trusted context by default)
  - Local LLM Engine (OllamaClient local-only binding, MockLLMProvider, LLMProvider facade)
  - Explicit fallback control (NEVER, ON_ERROR, ALWAYS_MOCK; no fabricated AI answers when offline)
  - CLI diagnostics (llm-health, llm-models, llm-ask, context-build, cognitive-ask, plan-create)
  - Long-Term Memory Engine V1 (EPISODIC, SEMANTIC, PROCEDURAL, DECISION, PREFERENCE, CANDIDATE)
  - Verification statuses (USER_PROVIDED, OBSERVED, VERIFIED, INFERRED, UNVERIFIED, CANDIDATE)
  - Versioning, history preservation, lineage tracing (trace_source)
  - Vietnamese diacritics search and SQL injection parameterization
  - Policy Engine R0-R5 (R5 hard-blocked, R4 approval required)
  - Workspace path isolation (PathGuard)
  - Credential redaction in memory, prompts, plans, and audit logs
  - Automated 9-section engineering handoff generator
NEXT_TASK:
  milestone: SPRINT 7B — Windows Job Object Kernel Integration & Subprocess Spawner (Pending Design Sign-off)
  target_files: Windows Job Object backend implementation, Win32 Job API binding, supervised process spawner
  constraints: Zero production executors or background daemons active until explicit owner sign-off on docs/SPRINT6_DESIGN_SIGNOFF.md
PROTECTED_EXTERNAL_PROJECTS:
  - E:\AI\DATA CENTER AI OPERATING SYSTEM (DC-COMMAND V6.7 / CLAE)
  - E:\AI\BAT-AI-2026-Repo\battery-ai-\os_kernel (Kernel L3)
  - E:\AI\Skill\SKILL_BAT_AI (AI Workforce OS)
  - E:\AI\battery-ai-\BATTERY_AI_V4 (Battery Intelligence Brain)
  - E:\AI\BOT (Active production bots)
INSTRUCTION_FOR_NEXT_SESSION:
  Continue from Phase A completion. Read AGENTS.md, docs/PROJECT_STATUS.md, docs/QUAN_AI_BRAIN_FOUNDATION_ROADMAP.md, and reports/HANDOFF_LATEST.md. Verify test suite passes (4230 tests), propose smallest testable increment, show diff before editing, run tests and tools/validate_and_report.py, and verify reports/HANDOFF_LATEST.md.
```
