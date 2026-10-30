"""V7 Cấp 1 — seed 5 skill mục tiêu còn lại (đúng trạng thái thật: PROPOSED).

Chạy 1 lần; idempotent via register (không check trùng tên -> chỉ chạy khi registry chưa có).
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")
from quan_ai_brain.cognition.skill_registry import SkillRegistry, SkillStatus  # noqa: E402

reg = SkillRegistry(Path("data/skill_registry.json"))

existing = {s.name for s in reg.list_skills()}
if "EMAIL_ANALYSIS" in existing:
    print("Already seeded — skip")
    sys.exit(0)

skills = [
    dict(
        name="EMAIL_ANALYSIS",
        goal="Phân tích email yêu cầu: trích xuất người gửi/nội dung/dự án/người phụ trách/thời hạn/cam kết/câu hỏi/đầu ra cần tạo; phân biệt nội dung email vs suy luận",
        trigger_patterns=["phân tích email", "email analysis", "email yêu cầu"],
        inputs={"email_text": "nguyên văn email do chủ cung cấp trực tiếp"},
        steps=[
            "Trích xuất 8 trường §4.2.A",
            "Phân biệt trực tiếp vs suy luận",
            "Trả về cấu trúc chuẩn; trường không rõ -> UNKNOWN",
        ],
        tools=["stdlib re/json"],
        acceptance_criteria=[
            "Trích xuất đủ 8 trường A",
            "Không gán suy luận thành nội dung email",
            "UNKNOWN khi trường không rõ",
        ],
        initial_status=SkillStatus.PROPOSED,
        input_schema={"email_text": "string >= 20 chars"},
        output_schema={"analysis": "object 8 trường", "inferences": "list (đánh dấu là suy luận)"},
        permissions_required=[],
        data_sources=["email_text do chủ cung cấp trực tiếp"],
        timeout_policy="10s",
        error_policy="fail_honest",
        risk_level=0,
        test_suite_ref="tests/test_v7_skills.py",
        exception_policy=["email rỗng/quá ngắn -> từ chối phân tích"],
        stop_conditions=["không có email text -> dừng"],
        known_limits=["CHƯA có connector Vmail — chỉ nhận text chủ cung cấp trực tiếp (nguồn thật BLOCKED)"],
    ),
    dict(
        name="CROSS_SOURCE_EVIDENCE_ANALYSIS",
        goal="Đối chiếu chéo nhiều nguồn (email, tasks.db, consultations, todos, reports); phát hiện mâu thuẫn; đánh giá nguồn theo thẩm quyền/thời điểm/bằng chứng hỗ trợ",
        trigger_patterns=["đối chiếu chéo", "cross check", "đối chiếu nguồn", "mâu thuẫn"],
        inputs={"unified_records": "bản ghi công việc hợp nhất", "sources": "danh sách nguồn đã truy cập"},
        steps=[
            "Chuẩn hoá bản ghi",
            "So từng cặp nguồn",
            "Phát hiện mâu thuẫn §4.2.D",
            "Đánh giá độ tin cậy nguồn",
            "Không phân xử được -> trình bày mâu thuẫn + đề xuất xác minh",
        ],
        tools=["sqlite3", "data/tasks.db", "data/consultations.db", "data/todos.db"],
        acceptance_criteria=[
            "Mọi mâu thuẫn có 2 nguồn trích dẫn",
            "Không mặc định email mới nhất đúng",
            "UNKNOWN khi thiếu dữ liệu",
        ],
        initial_status=SkillStatus.PROPOSED,
        input_schema={"unified_records": "list[object]", "sources": "list[string]"},
        output_schema={"conflicts": "list[object]", "confidence": "object", "unresolved": "list"},
        permissions_required=["read:data/tasks.db", "read:data/consultations.db", "read:data/todos.db"],
        data_sources=["data/tasks.db", "data/consultations.db", "data/todos.db", "reports/"],
        timeout_policy="30s per source",
        error_policy="fail_honest",
        risk_level=1,
        test_suite_ref="tests/test_v7_skills.py",
        exception_policy=["nguồn unavailable -> đánh dấu + tiếp tục nguồn còn lại", "mâu thuẫn không phân xử -> ghi rõ"],
        stop_conditions=["0 nguồn truy cập được -> dừng"],
    ),
    dict(
        name="PROGRESS_RISK_DETECTION",
        goal="Phát hiện quá hạn, nguy cơ chậm, phụ thuộc chưa xong, báo cáo chưa cập nhật, trách nhiệm không rõ, mốc ảnh hưởng việc khác",
        trigger_patterns=["rủi ro tiến độ", "risk detection", "chậm tiến độ", "quá hạn"],
        inputs={"unified_records": "bản ghi hợp nhất có hạn/thuộc tính/trạng thái", "as_of": "ISO date đối chiếu"},
        steps=[
            "Kiểm tra hạn vs as_of",
            "Kiểm tra phụ thuộc",
            "Kiểm tra độ tươi trạng thái",
            "Xếp hạng rủi ro có bằng chứng",
        ],
        tools=["data/tasks.db", "data/todos.db"],
        acceptance_criteria=[
            "Mọi rủi ro có bằng chứng + nguồn",
            "Không suy diễn phần trăm tiến độ",
            "UNKNOWN khi thiếu hạn/ngày",
        ],
        initial_status=SkillStatus.PROPOSED,
        input_schema={"unified_records": "list[object]", "as_of": "ISO date"},
        output_schema={"risks": "list[object: type, evidence, severity]", "unknowns": "list"},
        permissions_required=["read:data/tasks.db", "read:data/todos.db"],
        data_sources=["data/tasks.db", "data/todos.db"],
        timeout_policy="20s",
        error_policy="fail_honest",
        risk_level=1,
        test_suite_ref="tests/test_v7_skills.py",
        exception_policy=["thiếu hạn -> UNKNOWN không phải risk"],
        stop_conditions=["records rỗng -> dừng báo rỗng"],
    ),
    dict(
        name="OWNER_ADVISORY_REPORT",
        goal="Tổng hợp thành báo cáo tư vấn 12 mục §4.2.E; mỗi kết luận truy vết được nguồn; liệt kê nguồn chưa truy cập + giới hạn tin cậy",
        trigger_patterns=["báo cáo tư vấn", "advisory report", "tư vấn tiến độ"],
        inputs={"analysis": "kết quả EMAIL_ANALYSIS", "reconciliation": "kết quả đối chiếu", "risks": "kết quả risk detection"},
        steps=[
            "Tổng hợp 12 mục §4.2.E",
            "Gắn nguồn từng kết luận",
            "Ghi nguồn chưa truy cập",
            "Ghi mức tin cậy + giới hạn",
            "Đề xuất phương án (không tự thực hiện)",
        ],
        tools=["reports/"],
        acceptance_criteria=[
            "Đủ 12 mục",
            "Mỗi kết luận quan trọng có nguồn",
            "Hành động ghi/gửi ngoài KHÔNG tự thực hiện",
        ],
        initial_status=SkillStatus.PROPOSED,
        input_schema={"analysis": "object", "reconciliation": "object", "risks": "object"},
        output_schema={"report_md": "string markdown 12 mục", "traceability": "object"},
        permissions_required=["write:reports/* (chỉ tạo file báo cáo mới, không ghi đè file có sẵn)"],
        data_sources=["kết quả các skill trước"],
        timeout_policy="15s",
        error_policy="fail_honest",
        risk_level=1,
        test_suite_ref="tests/test_v7_skills.py",
        exception_policy=["thiếu input skill trước -> ghi phần đó NOT_VERIFIED"],
        stop_conditions=["không có kết quả phân tích nào -> dừng"],
    ),
    dict(
        name="VERIFIED_WORKFLOW_REUSE",
        goal="Tái sử dụng quy trình đã kiểm chứng: phân loại bài toán -> tìm workflow/skill -> kiểm tra điều kiện áp dụng -> tái sử dụng có điều chỉnh -> đo kết quả",
        trigger_patterns=["tái sử dụng", "reuse workflow", "làm như lần trước"],
        inputs={"new_task": "mô tả bài toán mới", "workflow_id": "id workflow đã lưu (optional)"},
        steps=[
            "Phân loại bài toán",
            "Tìm workflow/skill match",
            "Kiểm tra điều kiện áp dụng §5.5",
            "So khác biệt bài toán mới/cũ",
            "Tái sử dụng + điều chỉnh trong phạm vi",
            "Đánh giá + ghi nhận fit/gap",
        ],
        tools=["skill_registry"],
        acceptance_criteria=[
            "Không tái sử dụng khi điều kiện áp dụng không khớp",
            "Ghi nhận khác biệt dữ liệu/quyền/yêu cầu",
            "Đo lường kết quả tái sử dụng",
        ],
        initial_status=SkillStatus.PROPOSED,
        input_schema={"new_task": "string", "workflow_id": "string optional"},
        output_schema={"reused": "bool", "adjustments": "list", "fit_assessment": "object", "measurements": "object"},
        permissions_required=["read:data/skill_registry.json"],
        data_sources=["data/skill_registry.json"],
        timeout_policy="10s",
        error_policy="fail_honest",
        risk_level=0,
        test_suite_ref="tests/test_v7_skills.py",
        exception_policy=["workflow không match -> no_match, không ép dùng"],
        stop_conditions=["registry trống -> dừng báo trống"],
        known_limits=["Cần workflow VERIFIED tồn tại trước (Cấp 3)"],
    ),
]

created = []
for s in skills:
    rec = reg.register_skill(**s)
    created.append(rec)
    print(f"{rec.skill_id} | {rec.name} | {rec.status.value}")

print("---")
print("Tổng skills:", len(reg.list_skills()))
for s in reg.list_skills():
    print("-", s.name, "|", s.status.value, "| risk", s.risk_level, "|", s.test_suite_ref)
