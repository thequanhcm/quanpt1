# Xử lý alarm mất đồng bộ

Khi site báo alarm mất đồng bộ, thực hiện quy trình: kiểm tra nguồn điện,
kiểm tra link quang, kiểm tra clock source. Nếu 30 phút không hồi phục thì
escalation lên cấp trên.

# SLA xử lý alarm

Alarm nghiêm trọng (critical) phải xử lý xong trong 4 giờ theo SLA.
Alarm thường (major) trong 8 giờ. Ghi nhận thời điểm bắt đầu vào ticket.