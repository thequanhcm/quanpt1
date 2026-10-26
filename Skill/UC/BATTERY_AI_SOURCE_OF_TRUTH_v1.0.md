# BATTERY AI SOURCE OF TRUTH

## Phiên bản 1.0 --- Hồ sơ kiến trúc, nghiệp vụ, AI và lộ trình

**Tên hệ thống:** BATTERY AI\
**Tên đầy đủ:** Nền tảng AI đánh giá, chẩn đoán và dự báo sức khỏe ắc
quy cho Tổng trạm/Data Center\
**Domain:** Battery / DC Power / UPS / REC\
**Kiến trúc cấp trên:** DC-COMMAND / Data Center AI Operating System\
**Đơn vị/Phạm vi định hướng:** VTNet / các Tổng trạm có VDCIM, UPS/REC,
BMS\
**Phiên bản tài liệu:** 1.0\
**Mục đích:** Source of Truth dùng làm nguồn đầu vào thống nhất cho các
Skill tạo hồ sơ UC AI, báo cáo thuyết minh, slide/presentation và
video/storyboard.

------------------------------------------------------------------------

## 0. QUY TẮC SỬ DỤNG TÀI LIỆU

Đây là tài liệu chuẩn hóa kiến thức về BATTERY AI. Các Skill phía trên
phải sử dụng tài liệu này làm nguồn tham chiếu trước khi tạo sản phẩm.

### 0.1. Nguyên tắc chống bịa thông tin

Không tự tạo: - số liệu vận hành chưa có bằng chứng; - kết quả AI chưa
được kiểm thử; - thông số phần cứng chưa được xác nhận; - KPI/ROI chưa
có dữ liệu; - trạng thái "Production" nếu tài liệu nguồn chỉ chứng minh
PoC/Pilot; - chứng nhận tiêu chuẩn nếu chưa có hồ sơ chứng minh.

Khi chưa đủ bằng chứng, dùng một trong bốn nhãn: - **ĐÃ XÁC NHẬN /
VERIFIED** - **ĐANG TRIỂN KHAI / IN PROGRESS** - **POC/PILOT** - **ĐỀ
XUẤT / ROADMAP**

### 0.2. Nguyên tắc kiến trúc

BATTERY AI V4/BIC là Domain Brain của hệ thống Battery. DC-COMMAND là
lớp điều hành cấp trên. Không xây lại BATTERY AI V4 từ đầu nếu không có
lý do kỹ thuật; ưu tiên: **WRAP + EXTEND + ORCHESTRATE + INTEGRATE.**

### 0.3. Nguyên tắc an toàn

AI được phép quan sát, phân tích, dự báo, mô phỏng và đề xuất. Các hành
động có tác động Production phải đi qua Policy/Authority/Governance và
cơ chế phê duyệt phù hợp. LLM không được là nguồn quyết định duy nhất.

------------------------------------------------------------------------

# 1. EXECUTIVE SUMMARY

BATTERY AI là một nền tảng chuyên gia AI cho nguồn DC/UPS/REC, chuyển mô
hình vận hành từ:

**Giám sát ngưỡng tĩnh → Phát hiện bất thường → Chẩn đoán nguyên nhân →
Đánh giá SOH → Dự báo RUL/Risk → Khuyến nghị bảo trì → Học từ Ground
Truth.**

Hệ thống được định hướng tích hợp vào VDCIM và DC-COMMAND, đồng thời hỗ
trợ NetChat/AI Assistant để kỹ sư truy vấn dữ liệu và tri thức vận hành
bằng ngôn ngữ tự nhiên.

Các năng lực cốt lõi: 1. Realtime battery monitoring. 2. Historical
trend analysis. 3. Cell/String imbalance detection. 4.
Internal-resistance anomaly detection. 5. Temperature anomaly and
thermal analysis. 6. SOH estimation. 7. RUL prediction. 8. Risk scoring.
9. Root Cause Analysis (RCA). 10. Battery discharge-test feedback. 11.
KEDB/RAG/engineering knowledge. 12. Digital Twin / What-if analysis. 13.
AI Assistant/Ops Copilot. 14. Smart Alerting. 15. Task/maintenance
recommendation. 16. Continual learning và memory. 17. Evidence-based
governance. 18. Tích hợp với VDCIM/DC-COMMAND/NetChat.

------------------------------------------------------------------------

# 2. BÀI TOÁN NGHIỆP VỤ

## 2.1. Hiện trạng

VDCIM đã hỗ trợ giám sát tập trung các thiết bị cơ điện, BATU/BATR/UPS,
heatmap phòng/rack, alarm và visualization. Tuy nhiên, bài toán đánh giá
chất lượng ắc quy chuyên sâu cần khai thác đồng thời dữ liệu realtime và
lịch sử.

Các hạn chế nghiệp vụ cần giải quyết: - Alarm chủ yếu dựa trên ngưỡng
tĩnh. - Test discharge còn có tính thủ công. - Khó nhận biết xu hướng
suy giảm trước khi vượt ngưỡng. - Phụ thuộc nhiều vào kinh nghiệm BO/kỹ
thuật viên. - Khó ưu tiên nguồn lực bảo trì theo mức rủi ro. - Khó truy
nguyên nguyên nhân từ cell → string → UPS → môi trường. - Tri thức xử lý
sự cố dễ phân tán trong logfile, SOP và kinh nghiệm cá nhân.

## 2.2. Bài toán mục tiêu

BATTERY AI phải trả lời được: - Bình/string nào đang bất thường? - Bất
thường ở mức cell, string hay thiết bị? - Xu hướng đang xấu lên hay ổn
định? - SOH hiện tại ước lượng thế nào? - RUL còn bao lâu theo các kịch
bản? - Xác suất/rủi ro sự cố là gì? - Nguyên nhân có khả năng là gì? -
Cần kiểm tra gì tiếp theo? - Có cần test discharge không? - Có cần bảo
trì/thay thế không? - Bằng chứng nào hỗ trợ kết luận? - Kết quả dự báo
trước đây đúng/sai ra sao?

------------------------------------------------------------------------

# 3. PHẠM VI HỆ THỐNG

## 3.1. Đối tượng giám sát

-   Battery cell.
-   Battery string.
-   UPS.
-   REC.
-   DC system.
-   BMS/Battery monitoring.
-   Nguồn và môi trường liên quan.

## 3.2. Phạm vi triển khai định hướng

Tài liệu yêu cầu VDCIM nêu phạm vi áp dụng cho các đơn vị VTNet và các
Tổng trạm/điểm mạng có hệ thống ắc quy, UPS/REC, BMS. Đối tượng gồm BO
khu vực, quản lý ca trực, kỹ thuật viên vận hành/bảo dưỡng và cán bộ
theo dõi nguồn điện/UPS/ắc quy.

Quy mô tham chiếu trong phiếu yêu cầu: - khoảng 2.000 người dùng dự
kiến; - khoảng 200 người dùng đồng thời.

Các con số này là **quy mô yêu cầu/thiết kế tham chiếu**, không mặc định
là quy mô Production thực tế.

------------------------------------------------------------------------

# 4. KIẾN TRÚC LOGIC

``` text
                         HUMAN / OPERATOR
                                |
                                v
                    +------------------------+
                    |      DC-COMMAND        |
                    | Command / Mission Brain|
                    +-----------+------------+
                                |
                         Command/Event Bus
                                |
                                v
                    +------------------------+
                    |   BATTERY COMMANDER    |
                    +-----------+------------+
                                |
                    +-----------v------------+
                    |   BATTERY AI V4 / BIC  |
                    |      DOMAIN BRAIN       |
                    +-----------+------------+
                                |
          +----------+----------+----------+----------+
          |          |          |          |          |
         SOH        RUL      Anomaly      RCA       KEDB
          |          |          |          |          |
          +----------+----------+----------+----------+
                                |
                         Evidence / Result
                                |
              +-----------------+------------------+
              |                 |                  |
            VDCIM            NetChat          Dashboard
              |                 |                  |
              +-----------------+------------------+
                                |
                         Feedback / Ground Truth
                                |
                                v
                      Continual Learning
```

------------------------------------------------------------------------

# 5. DATA FABRIC

## 5.1. Nguồn dữ liệu

Nguồn có thể gồm: - VDCIM realtime API. - VDCIM historical API. - BMS. -
UPS/REC. - DC source. - logfile ắc quy. - Excel/CSV/JSON/TXT/LOG. -
Sensor/telemetry. - Maintenance history. - Alarm/event history. -
Discharge-test results.

## 5.2. Dữ liệu tối thiểu

-   Site ID.
-   Device ID.
-   String ID.
-   Cell ID.
-   Timestamp.
-   Cell/String voltage.
-   Temperature.
-   Internal resistance.
-   Charge/float current.
-   Discharge current.
-   Alarm status.
-   Operating time.
-   Manufacturing/year of service.
-   Vendor/model.
-   Maintenance history.

## 5.3. Pipeline dữ liệu

``` text
Raw Data
   ↓
Ingestion
   ↓
Normalization
   ↓
Validation / Data Trust
   ↓
Contextualization
   ↓
Time-series / Historical Store
   ↓
Feature Engineering
   ↓
AI Analytics
   ↓
Evidence
   ↓
Decision / Recommendation
```

------------------------------------------------------------------------

# 6. BATTERY AI V4

BATTERY_AI_V4 là nền tảng chuyên gia Battery được xây dựng trên Python
Backend, với các nhóm chức năng: - Core APIs: Auth, realtime input,
dashboard. - Analytics & Prediction Engine. - SOH. - RUL. - RCA
Analyzer. - Battery Advisor / Chatbot. - SQLite telemetry databases,
trong đó có `battery_data.db` và `battery_ups_v4.db`.

V4 là nền tảng phân tích/dự báo cốt lõi. Các lớp orchestration,
governance, memory và continual learning ở cấp cao phải tích hợp thông
qua adapter/bridge thay vì phá bỏ lõi.

------------------------------------------------------------------------

# 7. BATTERY AI V5 / CONTINUAL INTELLIGENCE

Kiến trúc tiến hóa bổ sung Knowledge & Experience Learning Engine.

## 7.1. 5 lớp memory tham chiếu

1.  **Episodic Memory:** ghi nhận sự kiện đã xảy ra.
2.  **Semantic Memory:** tổng hợp sự kiện thành pattern/knowledge.
3.  **Procedural Memory:** ghi nhớ quy trình xử lý.
4.  **Working Memory:** context phiên làm việc.
5.  **Fleet Memory:** liên kết từ Cell → String → UPS → Fleet.

## 7.2. Learning Loop

``` text
Telemetry / Incident
        ↓
Memory Consolidation
        ↓
Knowledge Graph Update
        ↓
Context Refinement
        ↓
Prediction vs Ground Truth
        ↓
Error / Calibration
        ↓
Pattern Confidence Update
        ↓
Verified Lesson
```

Một PoC đã ghi nhận trường hợp AI dự đoán "hỏng cell" do IR tăng nhưng
kỹ thuật viên xác nhận nguyên nhân là lỏng chốt cực; lesson được ghi
nhận và đánh dấu VERIFIED. Giá trị Experience Score 82.5/100 chỉ nên
được sử dụng khi dẫn nguồn PoC tương ứng, không coi là KPI Production.

------------------------------------------------------------------------

# 8. AI ANALYTICS

## 8.1. Anomaly Detection

Phát hiện: - lệch điện áp; - điện áp trôi; - nhiệt độ cao; - nội trở
tăng; - nội trở tăng đột biến; - mất cân bằng cell/string; - dấu hiệu
quá sạc; - biến động bất thường; - sensor drift/data quality issue.

## 8.2. Health / SOH

SOH là chỉ số đánh giá trạng thái sức khỏe ắc quy dựa trên dữ liệu đo,
lịch sử, xu hướng và các đặc trưng liên quan.

Có thể sử dụng các mô hình ML như Random Forest/XGBoost/LightGBM khi phù
hợp dữ liệu. Việc chọn model Production phải dựa trên validation thực
tế.

## 8.3. RUL

RUL = Remaining Useful Life.

Hệ thống có định hướng dự báo theo các horizon: - 30 ngày; - 90 ngày; -
180 ngày; - 365 ngày;

và có thể biểu diễn các phân vị P10/P50/P90 để thể hiện bất định.

RUL phải luôn đi kèm: - confidence/uncertainty; - dữ liệu đầu vào; -
thời điểm dự báo; - điều kiện vận hành; - phương pháp/model; - actual
outcome khi có Ground Truth.

## 8.4. Risk Scoring

Risk nên kết hợp: - Probability; - Impact; - Criticality; -
Confidence; - Evidence; - Asset context; - Historical behavior.

Đầu ra nghiệp vụ tối thiểu: - OK / WARNING / REPLACE; - Critical / High
/ Medium / Low.

Không coi risk score là xác suất hỏng nếu chưa có calibration chứng
minh.

------------------------------------------------------------------------

# 9. RCA --- ROOT CAUSE ANALYSIS

RCA phân tích các nhóm nguyên nhân: - overcharge; - cell/string
imbalance; - high temperature; - rapid IR increase; - aging; - loose
connection; - sensor/data quality; - các nguyên nhân liên quan
UPS/DC/environment.

RCA phải tạo: 1. Hypothesis. 2. Evidence. 3. Confidence. 4. Asset scope.
5. Suggested verification. 6. Recommended action. 7. Link tới
incident/KEDB/SOP nếu có.

LLM không được tự bịa quy trình kỹ thuật.

------------------------------------------------------------------------

# 10. BATTERY DISCHARGE TEST & GROUND TRUTH

Discharge test là nguồn Ground Truth quan trọng để: - hiệu chỉnh SOH; -
hiệu chỉnh RUL; - kiểm tra khả năng duy trì tải; - đánh giá độ tin cậy
mô hình; - calibration prediction error.

Chu trình:

``` text
AI Prediction
     ↓
Low Confidence / High Risk
     ↓
Recommend Discharge Test
     ↓
Actual Test Result
     ↓
Compare Prediction vs Actual
     ↓
Calibration
     ↓
Verified Learning
```

------------------------------------------------------------------------

# 11. KEDB / RAG / KNOWLEDGE FABRIC

Knowledge Fabric gồm: - KEDB; - RAG; - SOP; - Manual; - Standard; -
Historical Incident; - Maintenance Record; - Engineering Knowledge.

Mỗi câu trả lời kỹ thuật của Knowledge Agent nên có: - Answer; -
Evidence; - Source; - Confidence; - Applicable Asset; - Applicable
Model.

Mục tiêu là giảm việc AI trả lời dựa trên "kiến thức chung" khi đã có
tài liệu nội bộ phù hợp.

------------------------------------------------------------------------

# 12. DIGITAL TWIN

Mô hình tài sản:

``` text
SITE
  ↓
ROOM
  ↓
SYSTEM
  ↓
ASSET
  ↓
COMPONENT
  ↓
STRING
  ↓
CELL
```

Ví dụ:

``` text
PDL
 └── UPS-03
      └── Battery String
           └── Battery #17
```

Digital Twin hỗ trợ: - What-if; - mô phỏng mất điện; - ước lượng thời
gian duy trì; - kiểm tra tác động của thay đổi điều kiện; - hỗ trợ
decision trước action.

Ví dụ: **Mất điện lưới → mô phỏng tải → battery degradation → thời gian
backup → risk.**

------------------------------------------------------------------------

# 13. VDCIM INTEGRATION

BATTERY AI được thiết kế để tích hợp vào VDCIM như một module AI chuyên
sâu.

## 13.1. Luồng

``` text
VDCIM / BMS / UPS / REC
          ↓
     API / Data Layer
          ↓
      Battery AI
          ↓
SOH / RUL / Risk / RCA / Alert
          ↓
        VDCIM
```

## 13.2. Menu/chức năng

### Dashboard Home

-   số site/device/string/cell;
-   alarm;
-   heatmap;
-   drill-down site → device → string → cell.

### Voltage Trend

-   voltage;
-   temperature;
-   internal resistance;
-   trend theo thời gian;
-   comparison giữa string/site.

### Predictions

-   risk;
-   RUL;
-   probability;
-   confidence;
-   priority list.

### RCA

-   nguyên nhân;
-   evidence;
-   checklist;
-   recommended action.

### AI Chat

-   hỏi đáp tiếng Việt;
-   realtime + history;
-   logfile;
-   voice/wake-word khi được triển khai.

### Alert Center

-   xác nhận;
-   ẩn;
-   lịch sử;
-   nhóm theo thiết bị;
-   ưu tiên.

### Task Board

-   giao việc;
-   người phụ trách;
-   deadline;
-   trạng thái;
-   bàn giao ca.

### Import/Export

-   Excel;
-   CSV;
-   JSON;
-   TXT;
-   LOG;
-   báo cáo phân tích.

------------------------------------------------------------------------

# 14. DC-COMMAND INTEGRATION

DC-COMMAND là lớp điều hành cấp trên, còn BATTERY AI V4 là Battery
Domain Brain.

## 14.1. Battery AI V4 Adapter

Adapter chịu trách nhiệm: - gọi API; - nhận kết quả; - chuẩn hóa dữ
liệu; - chuyển command/event/mission; - quản lý version; - health
check; - fallback; - audit.

## 14.2. Mission

Ví dụ:

``` text
“Đánh giá toàn bộ các tổ Battery và xác định
các tổ có nguy cơ cao cần ưu tiên kiểm tra.”
```

Mission được phân rã:

``` text
Collect
 → Validate
 → Analyze
 → Detect Anomaly
 → SOH
 → RUL
 → Risk
 → Compare
 → Prioritize
 → Recommend
 → Report
```

## 14.3. Planning

Planner có thể sử dụng: - Goal; - Constraints; - Assets; - Policies; -
Available Agents; - Current System State.

Ví dụ chain: TelemetryAgent → ValidationAgent → AnomalyAgent → SOHAgent
→ RULAgent → RiskAgent → DiagnosticAgent → MaintenanceAgent →
ReportAgent.

------------------------------------------------------------------------

# 15. AGENT PLATFORM

Agent phải được quản lý qua registry.

Thông tin chuẩn:

``` json
{
  "agent_id": "",
  "name": "",
  "domain": "battery",
  "version": "",
  "status": "",
  "capabilities": [],
  "permissions": [],
  "risk_level": "",
  "health_score": 0,
  "confidence_score": 0,
  "dependencies": [],
  "tools": [],
  "model": "",
  "owner": "",
  "last_heartbeat": ""
}
```

Lifecycle:

``` text
DISCOVER → REGISTER → INITIALIZE → HEALTH CHECK
→ READY → RUNNING → DEGRADED → FAILED
→ RECOVERING → RETIRED
```

------------------------------------------------------------------------

# 16. DECISION / POLICY / GOVERNANCE

## 16.1. Decision

Quyết định không được dựa riêng vào LLM.

Nguyên tắc:

**EVIDENCE + POLICY + MODEL + RULE + CONTEXT + HUMAN APPROVAL**

## 16.2. Autonomy

Thang tham chiếu:

``` text
L0 Observe
L1 Recommend
L2 Human Approval
L3 Controlled Autonomous
L4 Autonomous
```

Battery AI V4 ban đầu ưu tiên L0--L2. Chỉ mở rộng quyền khi có đủ bằng
chứng về độ tin cậy, kiểm thử và policy.

## 16.3. Risk / Authority

SKILL_BAT_AI có nền tảng quản trị R0--R5.

Ví dụ: - R0: đọc log/metrics/health check. - R1: restart process an toàn
theo SOP. - R4: thay đổi IP quan trọng, thay đổi cấu trúc Production,
thao tác phá hủy DB --- cần phê duyệt. - R5: hành động bị cấm tuyệt đối,
gồm self-promotion/self-authorization và thao tác phá hủy trái policy.

------------------------------------------------------------------------

# 17. EVIDENCE & AUDIT

Mọi mission/command quan trọng phải truy vết:

``` text
WHO
WHAT
WHEN
WHY
WHICH AGENT
WHICH MODEL
WHICH DATA
WHICH POLICY
WHICH EVIDENCE
WHAT DECISION
WHAT ACTION
WHAT RESULT
```

Evidence phải được ưu tiên hơn self-report của Agent.

------------------------------------------------------------------------

# 18. NETCHAT / AI ASSISTANT

NetChat là kênh tương tác hai chiều: - nhận yêu cầu; - truy vấn trạng
thái; - trả cảnh báo; - trả kết quả AI; - hỗ trợ điều phối.

Các lớp bảo vệ anti-loop đã được mô tả trong kiến trúc: 1. User ID
filter. 2. Sender name filter. 3. Message signature filter. 4.
`from_bot` / `from_webhook` flag.

Không đưa "cognitive trace" nội bộ/chuỗi suy luận bí mật vào hồ sơ công
khai. Khi trình bày với người dùng, chỉ hiển thị **lý do tóm tắt, bằng
chứng và căn cứ quyết định**.

------------------------------------------------------------------------

# 19. LOCAL AI / BẢO MẬT

Kiến trúc hiện tại có định hướng Local LLM/Ollama để: - bảo vệ dữ
liệu; - giảm phụ thuộc dịch vụ bên ngoài; - phục vụ reasoning/RAG nội
bộ.

Một trạng thái hệ thống trước đây ghi nhận Qwen2.5:7b trong AI/RAG
Engine. Khi đưa vào hồ sơ nộp chính thức, chỉ ghi là "Local LLM/RAG"
hoặc ghi chính xác model nếu môi trường hiện tại đã xác nhận lại.

------------------------------------------------------------------------

# 20. HẠ TẦNG TRIỂN KHAI

## 20.1. Kiến trúc thư mục tham chiếu

``` text
E:\AI\
├── battery-ai-
│   └── BATTERY_AI_V4
├── DATA CENTER AI OPERATING SYSTEM
│   └── data_fabric
├── N8N
│   └── BATTERY_AI_MASTER_V4.json
├── Ollama
├── _Raw_Data
└── _Tools_And_Backups
```

BATTERY AI V4 được xác định là hệ thống độc lập có thể chạy độc lập hoặc
tích hợp DC-COMMAND.

## 20.2. Edge

Raspberry Pi 5 được định hướng làm Edge Data Collector: - lấy dữ liệu; -
đọc sensor/protocol; - chuẩn hóa sơ bộ; - đẩy dữ liệu về AI backend.

Edge không nhất thiết chạy toàn bộ AI reasoning nặng.

------------------------------------------------------------------------

# 21. PROTOCOL / CONNECTIVITY

Các giao thức/nguồn được kiến trúc hỗ trợ: - RS485 / Modbus; - Modbus
TCP; - BACnet; - SNMP; - MQTT; - REST API; - WebSocket; -
CSV/Excel/log; - historian/telemetry/event/alarm.

Kết nối SCADA/BMS trực tiếp qua Modbus TCP/SNMP là hướng mở rộng khi hạ
tầng cho phép.

------------------------------------------------------------------------

# 22. DASHBOARD

Dashboard mục tiêu:

``` text
SYSTEM HEALTH
SYSTEM RISK
ACTIVE ALERTS
CRITICAL BATTERIES
SOH
RUL
PREDICTED FAILURES
CELL HEATMAP
TREND
RCA
ACTIVE TASKS
AI RECOMMENDATIONS
```

Drill-down:

``` text
Fleet
 ↓
Site
 ↓
Room
 ↓
UPS/REC
 ↓
String
 ↓
Cell
```

------------------------------------------------------------------------

# 23. END-TO-END OPERATING LOOP

``` text
1. OBSERVE / TELEMETRY
        ↓
2. DATA TRUST
        ↓
3. EVIDENCE
        ↓
4. RCA / CAUSAL ANALYSIS
        ↓
5. MEMORY RETRIEVAL
        ↓
6. PRIMARY REASONING
        ↓
7. ADVERSARIAL CHECK
        ↓
8. SELF-CRITIQUE
        ↓
9. WHAT-IF
        ↓
10. DIGITAL TWIN
        ↓
11. UNCERTAINTY / CALIBRATION
        ↓
12. DECISION
        ↓
13. SAFETY GATE
        ↓
14. HUMAN / POLICY APPROVAL
        ↓
15. ACTION / RECOMMENDATION
        ↓
16. VERIFICATION
        ↓
17. ACTUAL OUTCOME
        ↓
18. LEARNING
        ↓
19. MEMORY UPDATE
```

Không phải tất cả bước đều bắt buộc chạy cho mọi truy vấn; mức độ sâu
phụ thuộc risk/criticality.

------------------------------------------------------------------------

# 24. CONTINUOUS LEARNING

Learning phải theo nguyên tắc:

``` text
Prediction
   ↓
Actual Outcome
   ↓
Error
   ↓
Calibration
   ↓
Lesson
   ↓
Verification
   ↓
Knowledge Update
```

Không cho phép "tự học" đồng nghĩa với tự sửa Production.

Các thay đổi model/rule/policy phải: 1. tạo draft; 2. test; 3. compare
với baseline; 4. đánh giá regression; 5. được phê duyệt theo policy; 6.
mới promote.

------------------------------------------------------------------------

# 25. KẾT QUẢ / BẰNG CHỨNG ĐÃ CÓ

Các tài liệu hiện có ghi nhận: - BATTERY AI V4 có Core API,
Analytics/Prediction, RCA, Advisor/Chatbot và SQLite telemetry. - VDCIM
integration yêu cầu realtime/historical data, RUL, risk scoring, anomaly
detection, RCA và AI Assistant. - Một báo cáo hệ thống ghi nhận quy mô
tham chiếu 53 tủ nguồn, 95 strings và 3.900+ cells trong tập dữ liệu
được quản lý. - Một báo cáo DC-COMMAND ghi nhận bộ kiểm thử 46 suites
với 331/331 test cases PASS trong môi trường báo cáo tại thời điểm
lập. - Một PoC learning loop ghi nhận lesson về "lỏng chốt cực" và
Experience Score 82.5/100. - SKILL_BAT_AI evaluation foundation ghi nhận
8/8 test cases passed cho nền tảng governance/evaluation. - Kiến trúc
SKILL_BAT_AI có KWSR: Knowledge, Workflow, Skills/Agents, Rules và lớp
Evaluation.

**Lưu ý:** các con số trên là bằng chứng từ các báo cáo kỹ thuật hiện có
tại thời điểm lập báo cáo; khi dùng trong hồ sơ nghiệm thu/nộp chính
thức cần gắn với biên bản/test evidence tương ứng.

------------------------------------------------------------------------

# 26. HIỆU QUẢ MỤC TIÊU

Không tự khẳng định KPI đã đạt nếu chưa có baseline đo lường.

Các KPI nên đo: - False Alarm Rate. - Detection Lead Time. - Mean Time
To Detect. - Mean Time To Diagnose. - Mean Time To Resolve. - RUL MAE /
RMSE. - SOH estimation error. - Prediction calibration. - Mission
success rate. - Agent reliability. - Human intervention rate. - System
availability. - Auditability. - Explainability. - Prevented failure /
avoided downtime khi có evidence. - Maintenance optimization.

------------------------------------------------------------------------

# 27. LỘ TRÌNH

## Phase 1 --- Foundation

-   Chuẩn hóa data.
-   API.
-   Dashboard.
-   Anomaly detection.
-   SOH/RUL baseline.
-   RCA.
-   KEDB/RAG.

## Phase 2 --- Integration

-   VDCIM.
-   NetChat.
-   Task Board.
-   Alert Center.
-   Battery AI V4 Adapter.
-   DC-COMMAND integration.

## Phase 3 --- Intelligence

-   Digital Twin.
-   Ground Truth loop.
-   Prediction calibration.
-   Continual learning.
-   Fleet intelligence.

## Phase 4 --- Controlled Autonomy

-   Policy engine.
-   Evidence gate.
-   Risk engine.
-   Human approval.
-   Controlled autonomous workflows.

## Phase 5 --- Multi-Domain

Mở rộng từ Battery sang: - UPS; - DC Power; - AC Power; - PDU; - ATS; -
Cooling/PAC/CRAC; - Energy; - Environment; - Facility.

------------------------------------------------------------------------

# 28. AN TOÀN / FAIL-SAFE

Khi xảy ra: - LLM down; - Agent down; - Database down; - Network down; -
model error; - sensor error;

hệ thống phải chuyển sang trạng thái an toàn: - không thực hiện hành
động nguy hiểm; - giảm confidence; - fallback; - retry; - escalate; -
yêu cầu human intervention khi cần.

AI không được làm mất an toàn của hệ thống DC/UPS.

------------------------------------------------------------------------

# 29. BACKUP / DR / AUDIT

Kiến trúc cần duy trì: - backup source code; - backup database; -
versioned model; - versioned prompt/rule; - audit trail; - incident
history; - rollback; - disaster recovery plan.

Các thay đổi Production phải có khả năng truy vết và rollback.

------------------------------------------------------------------------

# 30. BỘ TÀI LIỆU ĐẦU RA ĐỂ NỘP

Source of Truth này là nguồn cho bộ hồ sơ hoàn chỉnh:

## Nhóm A --- Hồ sơ UC AI

1.  `Ho_so_Don_vi_Battery_AI.docx`
2.  `Ho_so_Don_vi_Battery_AI.pdf`

## Nhóm B --- Báo cáo thuyết minh

3.  `Bao_cao_Thuyet_minh_Battery_AI.docx`
4.  `Bao_cao_Thuyet_minh_Battery_AI.pdf`

## Nhóm C --- Presentation

5.  `Slide_Battery_AI.pptx`
6.  `Slide_Battery_AI.pdf`

## Nhóm D --- Architecture

7.  `Battery_AI_System_Architecture.md`
8.  `Battery_AI_Data_Flow.md`
9.  `Battery_AI_AI_Architecture.md`
10. `Battery_AI_Integration_VDCIM.md`

## Nhóm E --- Evidence

11. Test plan.
12. Test cases.
13. Test result.
14. Demo screenshots.
15. Sample datasets.
16. Model evaluation.
17. Ground Truth / discharge-test evidence.

## Nhóm F --- Video

18. Storyboard.
19. Voice-over script.
20. Video prompt.
21. Demo scenario.

------------------------------------------------------------------------

# 31. CÁCH DÙNG VỚI 3 SKILL

## Skill 1 --- `vt...usecase-dossier-builder`

Input: `BATTERY_AI_SOURCE_OF_TRUTH.md`

Nhiệm vụ: - xây hồ sơ UC AI; - chuẩn hóa nghiệp vụ; - tạo Executive
Summary; - tạo mô tả hiện trạng/mục tiêu; - tạo architecture; - tạo
KPI; - tạo roadmap; - tạo bản mô tả chính thức.

## Skill 2 --- `ai-video-production-director`

Input: - Source of Truth; - Hồ sơ UC AI; - Báo cáo thuyết minh.

Nhiệm vụ: - storyline; - storyboard; - video concept; - voice-over; -
visual sequence; - demo flow; - presentation narrative.

## Skill 3 --- `viettel-slide-layout`

Input: - nội dung đã duyệt từ Skill 1; - storyline từ Skill 2; -
architecture/diagram.

Nhiệm vụ: - chuẩn hóa bố cục slide; - Viettel-style layout; -
typography; - diagram; - chart; - visual hierarchy; - speaker notes; -
xuất PowerPoint/PDF.

------------------------------------------------------------------------

# 32. PROMPT CHUẨN CHO AGENT

``` text
Bạn đang xây dựng hồ sơ chính thức cho hệ thống BATTERY AI.

SOURCE OF TRUTH:
BATTERY_AI_SOURCE_OF_TRUTH.md

QUY TẮC:
1. Đây là nguồn dữ liệu chuẩn.
2. Không bịa thông tin.
3. Không biến đề xuất thành tính năng đã triển khai.
4. Phân biệt VERIFIED / IN PROGRESS / POC-PILOT / ROADMAP.
5. Không thay đổi kiến trúc BATTERY AI V4 nếu không có lý do kỹ thuật.
6. BATTERY AI V4 là Battery Domain Brain.
7. DC-COMMAND là lớp orchestration cấp trên.
8. VDCIM là nền tảng tích hợp/hiển thị vận hành.
9. NetChat là kênh tương tác/cảnh báo.
10. Mọi kết luận AI quan trọng phải có Evidence + Confidence.
11. Không cho LLM tự bịa quy trình kỹ thuật.
12. Không cho AI tự ý thay đổi Production.
13. Mọi KPI phải chỉ rõ là measured, reference, target hoặc proposed.
14. Khi thiếu bằng chứng, ghi rõ “CHƯA CÓ BẰNG CHỨNG TRONG SOURCE OF TRUTH”.

Mục tiêu cuối:
Tạo một bộ hồ sơ Battery AI hoàn chỉnh, có thể dùng cho:
- hồ sơ UC AI;
- báo cáo kỹ thuật;
- trình bày lãnh đạo;
- đánh giá giải pháp;
- demo/pilot;
- nghiệm thu;
- roadmap phát triển.
```

------------------------------------------------------------------------

# 33. CHECKLIST TRƯỚC KHI NỘP

### Nội dung

-   [ ] Executive Summary.
-   [ ] Problem statement.
-   [ ] Business value.
-   [ ] Current state.
-   [ ] Target state.
-   [ ] Architecture.
-   [ ] Data flow.
-   [ ] AI models.
-   [ ] SOH.
-   [ ] RUL.
-   [ ] Risk.
-   [ ] RCA.
-   [ ] KEDB/RAG.
-   [ ] Digital Twin.
-   [ ] VDCIM.
-   [ ] NetChat.
-   [ ] DC-COMMAND.
-   [ ] Governance.
-   [ ] Security.
-   [ ] Testing.
-   [ ] Evidence.
-   [ ] KPI.
-   [ ] Roadmap.

### Hồ sơ

-   [ ] DOCX.
-   [ ] PDF.
-   [ ] PPTX.
-   [ ] PDF slide.
-   [ ] Architecture diagram.
-   [ ] Workflow diagram.
-   [ ] Demo script.
-   [ ] Test evidence.

### Kiểm soát tính trung thực

-   [ ] Không dùng KPI chưa đo như kết quả đã đạt.
-   [ ] Không gọi POC là Production.
-   [ ] Không gọi roadmap là feature hiện hữu.
-   [ ] Không đưa thông tin bí mật/credential.
-   [ ] Không đưa chain-of-thought nội bộ vào hồ sơ.
-   [ ] Mọi claim quan trọng có evidence.

------------------------------------------------------------------------

# 34. KẾT LUẬN

BATTERY AI được định vị là **Battery Domain Intelligence Platform**
trong kiến trúc Data Center AI.

Giá trị cốt lõi không chỉ nằm ở việc dự báo một chỉ số, mà ở chuỗi:

**DATA → TRUST → ANALYTICS → DIAGNOSIS → PREDICTION → RISK →
RECOMMENDATION → VERIFICATION → LEARNING.**

Kiến trúc mở cho phép BATTERY AI hoạt động độc lập, tích hợp VDCIM hoặc
trở thành Domain Brain của DC-COMMAND.

Source of Truth này là phiên bản nền tảng 1.0 để ba Skill phía trên tạo
ra bộ hồ sơ hoàn chỉnh. Các phiên bản sau phải cập nhật theo evidence
thực tế, test result, architecture change và approved roadmap; không
chỉnh sửa ngược lịch sử mà không ghi version/change log.

------------------------------------------------------------------------

## CHANGE LOG

  ----------------------------------------------------------------------------------
  Version                 Date                    Change
  ----------------------- ----------------------- ----------------------------------
  1.0                     18/09/2026              Chuẩn hóa Source of Truth từ các
                                                  tài liệu Battery
                                                  AI/VDCIM/DC-COMMAND/SKILL_BAT_AI
                                                  hiện có

  ----------------------------------------------------------------------------------
