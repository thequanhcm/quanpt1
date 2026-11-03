# MASTER PROMPT
# TONY – UNIVERSAL AGENT MASTERY & EMBODIMENT PROGRAM
## UAME V2.0 — XÂY DỰNG NĂNG LỰC LÀM VIỆC VỚI TOÀN BỘ THẾ GIỚI AGENT
### (Kế thừa UAIIF v1.0 + SENTINEL AI v1.0 — phát hành 02/11/2026)

---

# 0. BỐI CẢNH HIỆN TRẠNG — ĐIỂM XUẤT PHÁT BẮT BUỘC

Prompt này KHÔNG viết trên giấy trắng. Trước khi triển khai bất kỳ giai đoạn nào,
trình thực thi PHẢI khảo sát và tái sử dụng các thành phần đã tồn tại và đã được
kiểm chứng trong workspace `E:\BRAIN` (nhánh `feat/deom-m1-m2-task-lifecycle`):

## Đã có và ĐÃ TEST (không được xây lại, không được trùng lặp):

| Thành phần | Vị trí | Trạng thái kiểm chứng |
|---|---|---|
| Cognitive Core QUAN AI BRAIN | `src/quan_ai_brain/` | Toàn bộ não: nhận thức, planning, memory, audit |
| Tool Registry + ToolDefinition | `src/quan_ai_brain/tools/registry.py` | R0–R5, input_schema, requires_owner_approval |
| Approval Cards (gate phê duyệt owner) | `src/quan_ai_brain/governance/approval_cards.py` | R-gated, consumed-one-time |
| SENTINEL Giai đoạn 1 | `src/quan_ai_brain/security/` (agent_identity A–F, threat_levels L0–L4, containment 3 cấp) | 38/38 test; regression 3.442 |
| Liên bang (Federation) | `src/quan_ai_brain/federation/` (NodeRegistry, LanScanner, CloudConnector) | 22/22 test; E2E cảnh báo nút chết |
| UAIIF Giai đoạn 1 | `src/quan_ai_brain/uaiif/` (agent_knowledge 7 layer × 20 nhóm, agent_discovery 7 bước, agent_profile 24 trường, qpig skeleton) | 34/34 test; scorecard trung thực |
| Edge API phía lõi | pair / heartbeat / alert endpoints | Edge client đã code sẵn |
| Watchdog 24/7 | `tools/watchdog.py` (SEC + FED + SENTINEL cycle) | LIVE trên máy QUANPT |
| Kênh DM owner | `tools/netchat_security_center.py` + bot_tony | DM 2 bước xác nhận hash |
| Pi5 deploy script | `pi5_deploy/tony_pi5_all_in_one.sh` | Chờ owner chạy 1 bước vật lý |
| Test nền | `tests/` | 3.442 PASS / 0 FAIL / 45 skip |

## Chưa có — chính là đối tượng của prompt này:
1. **QEP (QUAN Embodiment Protocol)** — chuẩn giao tiếp thống nhất giữa trí tuệ và
   các cơ thể: CHƯA TỒN TẠI trong codebase (đã grep xác nhận 02/11/2026).
2. QPIG phía thiết bị (Pi5 chạy thật tool gateway) — hiện chỉ có skeleton phía lõi.
3. Continuous Learning Engine tự động (chu trình DISCOVER→...→REVIEW chưa chạy tự động).
4. MCP client / A2A protocol adapter — communication tool của QPIG mới chỉ probe được
   kênh federation đã đăng ký.
5. Bộ 200 kịch bản kiểm thử theo mục XI của UAIIF v1.0.

## Nguyên tắc bất di bất dịch (giữ nguyên 100% từ UAIIF v1.0 mục II):
- QUAN AI BRAIN là COGNITIVE CORE DUY NHẤT. Không tạo bộ não thứ hai. Mọi module
  mới trong chương trình này là NĂNG LỰC CHUYÊN MÔN MỞ RỘNG của core.
- Pi5 là Physical Interaction Gateway — cánh tay, đôi mắt, đôi tai. Không đưa logic
  quản trị vào Pi5. Không để dữ liệu quan trọng chỉ tồn tại trên Pi5.
- Không đồng nhất Tool với Cognitive Core.
- SENTINEL là Security Authority trong phạm vi ủy quyền; không agent nào tự ý vô
  hiệu hóa SENTINEL; không hành động nào thiếu bằng chứng và nhật ký kiểm toán.
- Owner (Phạm Thế Quân) là quyền quyết định tối cao. R3+ phải qua approval card.
- Không tự cấp quyền, không tự sửa chính sách để mở rộng quyền hạn.
- Trung thực tuyệt đối: không tuyên bố VERIFIED/ACTIVE khi chưa có bằng chứng kiểm
  thử thật; Unknown phải ghi là Unknown.

---

# I. ĐÍCH ĐẾN (END STATE) — MỤC TIÊU TỐI THƯỢNG

Khi chương trình UAME hoàn thành, hệ thống đạt trạng thái:

```
QUAN AI BRAIN  = Một trí tuệ thống nhất (cognitive core duy nhất).
TONY           = Một nhân sự số có hiểu biết rộng về thế giới Agent,
                 năng lực điều hành, khả năng học tập không ngừng.
Pi5            = Cổng tiếp xúc và tác nghiệp với thế giới bên ngoài
                 (QPIG chạy thật trên thiết bị).
SENTINEL AI    = Lực lượng bảo vệ và kiểm soát an ninh (GĐ2: M02/M07/M08,
                 GĐ3: M09/M10/M12 — theo SENTINEL AI v1.0).
QEP            = Hệ thống giao tiếp thống nhất giữa trí tuệ và mọi cơ thể.
Tool Registry  = Danh mục năng lực tác nghiệp thống nhất (mọi tool đều
                 đăng ký, có risk level, có schema, có audit).
```

Hệ quả kiểm chứng được của đích đến (phải test được, không phải khẩu hiệu):

- **H1 — Plug-in Agent**: thêm 1 Agent mới (ví dụ 1 coding agent, 1 research agent)
  chỉ cần: (a) đăng ký vào ToolRegistry hoặc federation, (b) chạy Discovery 7 bước
  tạo Universal Agent Profile. KHÔNG phải sửa core, KHÔNG phải viết code nhận thức mới.
- **H2 — Plug-in Body**: thêm 1 hình thể mới (Pi5 thứ hai, ESP32, robot có ROS 2)
  chỉ cần: chạy QEP endpoint trên thiết bị + đăng ký nút federation. TONY điều
  khiển qua cùng một bộ QPIG tool, không đổi logic.
- **H3 — Core bất biến dưới sự cố cơ thể**: rút Pi5 khỏi mạng → TONY mất capability
  vật lý nhưng nhận thức, bộ nhớ, planning, SENTINEL, DM owner vẫn hoạt động đầy đủ
  (test bằng cách tắt node thật).
- **H4 — Hiểu trước, can thiệp sau**: không thể gọi tool can thiệp (Control) lên một
  agent chưa có Universal Agent Profile đạt ngưỡng tin cậy — SENTINEL chặn và log.
- **H5 — Học liên tục có kiểm soát**: kiến thức mới tự động vào kho ở trạng thái
  INFERRED/OBSERVED; chỉ owner hoặc bằng chứng kiểm thử mới promote lên VERIFIED.

---

# II. KIẾN TRÚC MỤC TIÊU — 5 TẦNG

```
┌─────────────────────────────────────────────────────────────┐
│  TẦNG 5 — LEARNING & MASTERY (UAME Engine)                  │
│  Continuous Learning Engine · Scorecard tự động · Kho kiến  │
│  thức 7 layer × 20 nhóm · 200 kịch bản kiểm thử             │
├─────────────────────────────────────────────────────────────┤
│  TẦNG 4 — GOVERNANCE & SECURITY (SENTINEL)                  │
│  Identity A–F · Threat L0–L4 · Containment 3 cấp · Behavior │
│  monitoring M02 · Prompt/Memory security M07 · Tool gate M08│
├─────────────────────────────────────────────────────────────┤
│  TẦNG 3 — COGNITION & ORCHESTRATION (QUAN AI BRAIN core)    │
│  Planning · Memory · Audit · Approval cards R0–R5 · DM owner│
├─────────────────────────────────────────────────────────────┤
│  TẦNG 2 — AGENT MASTERY (UAIIF)                             │
│  Discovery 7 bước · Universal Agent Profile 24 trường ·     │
│  Knowledge 7 layer × 20 nhóm · QPIG 6 nhóm tool             │
├─────────────────────────────────────────────────────────────┤
│  TẦNG 1 — EMBODIMENT (QEP + Pi5 + federation)               │
│  QEP envelope · Capability advertisement · Task contract ·  │
│  Telemetry · Secure handshake · Pi5 runtime · Edge nút      │
└─────────────────────────────────────────────────────────────┘
```

Nguyên tắc đọc kiến trúc: tầng trên CHỈ được gọi tầng dưới thông qua interface
đã đăng ký (Tool Registry cho tool, QEP cho cơ thể, federation cho nút mạng).
Không nhảy tầng (Tầng 5 không được gọi thẳng SSH vào Pi5 — phải qua QPIG tool).

---

# III. QEP — QUAN EMBODIMENT PROTOCOL (ĐỊNH NGHĨA CHUẨN)

QEP là hợp đồng giao tiếp BẮT BUỘC giữa QUAN AI BRAIN (trí tuệ) và MỌI cơ thể
(Pi5, robot, thiết bị edge, agent có hình thể). QEP KHÔNG thay thế MCP/A2A —
QEP là lớp hợp đồng riêng cho embodiment, có thể chạy TRÊN nhiều vận chuyển
(HTTP LAN, MQTT, serial) và TƯƠNG THÍCH MCP ở tầng message.

## III.1. QEP Message Envelope (bắt buộc, versioned)

```json
{
  "qep_version": "1.0",
  "message_id": "<uuid>",
  "timestamp_utc": "<iso8601>",
  "origin": {"node_id": "core_pc", "role": "COGNITIVE"},
  "target": {"node_id": "edge_pi5", "role": "EMBODIMENT"},
  "kind": "COMMAND | QUERY | EVENT | HEARTBEAT | CAPABILITY_ADVERT | TASK_ASSIGN | TASK_RESULT",
  "payload": { },
  "security": {
    "identity_token": "<đã cấp khi pair>",
    "risk_level": "R0..R5",
    "requires_owner_approval": false,
    "approval_card_id": null
  },
  "correlation_id": "<uuid nhiệm vụ cha, nếu có>"
}
```

Quy tắc bắt buộc:
- Mọi message PHẢI có `qep_version`. Core từ chối envelope không hợp lệ (fail-closed).
- `security.risk_level` đi theo đúng thang R0–R5 của policy.py — không chế thang riêng.
- `kind=COMMAND` với risk ≥ R3 KHÔNG THỰC THI nếu thiếu `approval_card_id` hợp lệ,
  chưa consumed, và còn hạn.
- Mọi message PHẢI được ghi audit (event_type="qep_message") — không ngoại lệ.

## III.2. CAPABILITY_ADVERT — cơ thể tự khai năng lực khi pair/định kỳ

Cơ thể gửi danh sách capability, mỗi capability:

```json
{
  "capability_id": "camera.snapshot",
  "category": "INSPECTION",
  "risk_level": "R1",
  "input_schema": {...},
  "description": "Chụp 1 frame từ camera CSI",
  "requires_owner_approval": false
}
```

Core nhận advert → tự đăng ký vào ToolRegistry dạng
`qpig_<node>_<capability_id>` với handler route qua QEP. Như vậy:
**cơ thể mới cắm vào là tool mới xuất hiện** — không viết code core (thỏa H2).
Cơ thể KHÔNG ĐƯỢC tự nâng risk_level thấp hơn khai báo lần trước mà không có
lệnh từ core (chống downgrade gian lận — SENTINEL kiểm tra).

## III.3. TASK CONTRACT qua QEP (tái sử dụng TaskContract của SEC-S1)

Nhiệm vụ giao cho cơ thể phải là TaskContract đã có trong hệ thống:
subject = node_id cơ thể, allowed_actions = capability được ủy quyền,
scope giới hạn. Watcher SEC cycle mở rộng: so hành vi QEP của cơ thể với
contract — vi phạm → SENTINEL apply_violation (dùng nguyên văn cơ chế S3).

## III.4. TELEMENTRY & DEGRADATION

- Heartbeat QEP 60s (tái dùng chu kỳ FED). Mất 3 nhịp → EVENT node_down →
  DM owner + profile Operational_Status=UNREACHABLE (không xóa profile —
  lịch sử giữ nguyên).
- Pi5 mất kết nối: mọi tool QPIG trỏ về node đó trả
  `{"success": false, "error": "QEP_TARGET_UNREACHABLE"}` — core tiếp tục chạy
  (thỏa H3); KHÔNG có cơ chế nào "treo" core chờ cơ thể.

## III.5. QEP Security Handshake

Pair lần đầu = phê duyệt owner (DM xác nhận 2 bước như hiện tại) → cấp
identity_token lưu hai đầu. Token THỜI HẠN, revoke qua DM `thu hồi <node>`.
Mọi handshake bắt tay lại khi node offline > 24h. SENTINEL giám sát: node
gửi advert sai lệch lớn so với hồ sơ → cờ UNKNOWN/SUSPICIOUS theo A–F.

---

# IV. LỘ TRÌNH TRIỂN KHAI — 4 GIAI ĐOẠN (mỗi giai đoạn: card duyệt → code → test → E2E → báo cáo → chờ commit)

## GIAI ĐOẠN A — QEP CORE (mã sprint: UAME-S5) — Ưu tiên cao nhất
**Mục tiêu**: QEP sống phía lõi + mô phỏng cơ thể, trước khi cần phần cứng.

1. `src/quan_ai_brain/qep/envelope.py` — QEPEnvelope: validate, sign-check,
   audit hook. Schema versioned.
2. `src/quan_ai_brain/qep/capability.py` — CapabilityAdvert + validator;
   chống downgrade risk_level.
3. `src/quan_ai_brain/qep/router.py` — QEPRouter: route envelope ↔ node
   federation; ghi audit từng message; trả QEP_TARGET_UNREACHABLE đúng III.4.
4. `src/quan_ai_brain/qep/task_bridge.py` — cầu TaskContract (SEC-S1) ↔ QEP
   TASK_ASSIGN/TASK_RESULT.
5. API endpoints mở rộng trong server hiện có (8765/8766): `/api/qep/inbox`,
   `/api/qep/outbox`, `/api/qep/advert`.
6. **Mock embodiment** cho test: `tests/fakes/fake_body.py` — cơ thể giả nói
   QEP đầy đủ (pair → advert → nhận lệnh → trả result → heartbeat → chết).
7. Test suite `tests/test_uame_s5_qep.py` ≥ 30 kịch bản: envelope sai version
   bị từ chối; COMMAND R3 thiếu approval card bị refuse; downgrade advert bị
   cờ; node chết → UNREACHABLE không treo; audit đủ mọi message.
8. **Tiêu chí nghiệm thu**: toàn bộ test mới PASS; regression nền không giảm;
   E2E: fake_body pair thật qua API thật → core gọi tool QPIG sinh tự động từ
   advert → nhận result thật → kill fake_body → DM cảnh báo thật.

## GIAI ĐOẠN B — QPIG TRÊN PI5 THẬT (UAME-S6) — chờ owner bật SSH Pi5
1. Port `pi5_deploy/tony_pi5_all_in_one.sh` thành QEP body runtime: chạy
   client nhỏ (Python stdlib) — pair, gửi CAPABILITY_ADVERT (kiosk, audio,
   camera nếu có), nhận TASK_ASSIGN, thực thi trong allowlist, trả result.
2. Pi5 KHÔNG chứa não: chỉ runtime thực thi capability + cache không quan trọng.
3. 3 capability đầu tiên (đề xuất): `system.status` (R0), `camera.snapshot`
   (R1), `audio.play` (R2) — mỗi cái có input_schema thật.
4. E2E thật: từ core, `qpig_pi5_system_status` trả dữ liệu thật của Pi5;
   rút dây mạng Pi5 → H3 được chứng minh live.
5. **Tiêu chí nghiệm thu**: screenshot/capture thật gắn evidence; profile Pi5
   24 trường được điền từ Unknown → Observed/Verified (cập nhật bằng Discovery
   chạy lại, không sửa tay).

## GIAI ĐOẠN C — AGENT MASTERY SÂU (UAME-S7): MCP + A2A + Behavior
1. MCP client adapter: kết nối 1 MCP server thật (ưu tiên: server nội bộ hoặc
   local stdio server), discover tools, đăng ký vào ToolRegistry qua QPIG
   COMMUNICATION — mở rộng kho kiến thức layer L03 từ INFERRED → OBSERVED.
2. A2A adapter (đọc spec, PoC sandbox) — chỉ nghiên cứu + test sandbox, không
   kết nối agent ngoài chưa có owner duyệt.
3. SENTINEL M02 Behavior Monitoring: mở rộng watcher hiện có phân tích CHUỖI
   hành động (không chỉ vi phạm đơn) — sequence từ QEP audit log + task log;
   phát hiện vượt phạm vi contract, truy cập dữ liệu không phép.
4. SENTINEL M07/M08: prompt/memory security + tool execution gate (mọi tool
   call đi qua ToolRegistry đã có risk gate — bổ sung gate theo danh tính agent).
5. **Tiêu chí nghiệm thu**: MCP thật discover ≥ 1 tool; behavior test bắt được
   chuỗi vi phạm mô phỏng (không bắt được = không nghiệm thu, trung thực ghi FAIL).

## GIAI ĐOẠN D — LEARNING ENGINE + 200 KỊCH BẢN (UAME-S8)
1. `src/quan_ai_brain/uaiif/learning_engine.py` — chu trình
   DISCOVER→STUDY→UNDERSTAND→TEST→VERIFY→REMEMBER→APPLY→REVIEW chạy định kỳ
   (chu kỳ trong watchdog, mặc định 1 lần/ngày): mỗi chu kỳ chọn 1 chủ đề,
   tra nguồn (web/docs đã duyệt), ghi vào kho ở INFERRED, sinh bài kiểm tra,
   chỉ owner promote VERIFIED.
2. Agent Intelligence Scorecard tự động hàng tuần → DM owner.
3. Bộ 200 kịch bản theo mục XI UAIIF v1.0 (20×10 nhóm) — trong đó bắt buộc
   đủ các tình huống: Pi5 mất kết nối, agent đổi API, agent giả mạo danh tính,
   tool trả dữ liệu sai, nhiều agent đồng thời.
4. **Tiêu chí nghiệm thu**: ≥ 180/200 kịch bản PASS; mỗi kịch bản có evidence;
   scorecard tuần có bằng chứng tương ứng.

## Thứ tự và phụ thuộc
```
A (QEP core + fake body)  →  B (Pi5 thật)  →  C (MCP/A2A/Behavior)  →  D (Learning + 200)
        └──────── A có thể bắt đầu NGAY, không phụ thuộc phần cứng ───────┘
B phụ thuộc: owner chạy script trên Pi5 (SSH đang đóng).
C/D có thể chồng lên B nếu A hoàn thành.
Song song: SENTINEL GĐ2 (S4 cũ: M02/M07/M08) nằm trong Giai đoạn C.
```

---

# V. QUY ĐỊNH CHẤT LƯỢNG & KIỂM SOÁT (BẮT BUỘC CHO MỌI GIAI ĐOẠN)

1. **Không module trùng lặp**: trước khi viết file mới, grep codebase; module
   có sẵn ở `federation/`, `security/`, `uaiif/`, `tools/`, `governance/`
   phải được import, không copy lại.
2. **Mọi tool đi qua ToolRegistry** — không có lệnh ngoài registry, không
   hardcoded executor trong QPIG/QEP handler.
3. **Mọi hành động có audit**: envelope, capability, task, containment đều
   ghi AuditLogger — kiểm tra bằng test đọc lại log.
4. **Fail-closed**: envelope sai → từ chối; token hết hạn → từ chối; risk thiếu →
   coi là R5.
5. **Fail-honest trong báo cáo**: test FAIL phải xuất hiện trong báo cáo; chưa
   test phần cứng thật thì ghi "chưa xác minh trên phần cứng".
6. **Mỗi giai đoạn**: ≥ 25 test mới; full regression `pytest tests/ -q` phải
   ≥ baseline hiện tại (3.442) + đúng số test mới, 0 FAIL; lưu
   `reports/TEST_RUN_UAME_<S>.txt`.
7. **Báo cáo kỹ thuật tự động** sau mỗi tác vụ (quy chế 02/11): gọi
   `tools/technical_report_generator.py generate_report()` — 10 mục, lưu
   thư mục tháng. DM owner tin chính + tin regression (xác nhận 2 bước).
8. **Chờ duyệt trước commit**: git add từng file cụ thể, không `git add .`,
   không commit `data/` runtime và secret.
9. **Rollback plan**: mỗi giai đoạn ghi rõ 1 lệnh revert (git revert của commit
   tương ứng hoặc tắt chu kỳ trong watchdog) — không có rollback = không deploy.

---

# VI. ĐO LƯỜNG THÀNH CÔNG — KPI BẮT BUỘC

| KPI | Hiện tại (02/11) | Đích sau UAME |
|---|---|---|
| Scorecard Agent Intelligence | 60/100 | ≥ 85/100 (đủ bằng chứng, không cảm tính) |
| Nhóm Agent có kiến thức ≥ INFERRED | 7/20 | ≥ 16/20 |
| Layer có kiến thức ≥ INFERRED | 5/7 | 7/7 |
| Cơ thể điều khiển được qua QEP | 0 (chỉ probe) | ≥ 2 (Pi5 + fake/test harness) |
| Universal Agent Profile hoàn thành | 1 (16/24 Unknown) | Pi5 ≥ 20/24 trường Observed+ |
| Kịch bản kiểm thử UAME | 34 | ≥ 200 |
| MCP tool discover được | 0 | ≥ 1 server thật |
| SENTINEL module | M01/M04/M05/M06 | + M02/M07/M08 (GĐ2) |
| Thời gian tích hợp 1 cơ thể mới | — | ≤ 1 giờ (pair + advert, không sửa core) |
| Thời gian tích hợp 1 agent mới | — | ≤ 30 phút (discovery + profile, không sửa core) |

KPI cuối cùng là bài test "PLUG-IN": đưa 1 cơ thể/agent MỚI chưa từng gặp
(người chủ chọn) vào hệ thống — chỉ dùng pair + discovery, không sửa code core.
Đây là bài kiểm tra quyết định nghiệm thu chương trình.

---

# VII. RÀNG BUỘC CUỐI (KHÔNG THƯƠNG LƯỢNG)

- Không tạo bộ não mới. Không phân mảnh trí tuệ. Không vượt quyền điều hành.
- TONY không tự coi mình có quyền điều khiển một Agent chỉ vì kết nối được —
  chỉ can thiệp khi có quyền quản trị, được ủy quyền, hoặc owner phê duyệt.
- TONY không tự ý vô hiệu hóa SENTINEL. SENTINEL không thay thế quyền điều hành
  của TONY và owner — SENTINEL bảo vệ hệ thống, không nắm quyền tối cao.
- Mọi kiến thức chưa xác minh phải mang trạng thái chưa xác minh — kể cả khi
  nó đến từ tài liệu chính thức.
- Mọi tuyên bố trạng thái phải đi kèm bằng chứng kiểm thử còn giá trị tại thời
  điểm tuyên bố.

HẾT — UAME V2.0. Trình thực thi bắt đầu bằng Giai đoạn A sau khi owner duyệt
card TASK-UAME-S5.
