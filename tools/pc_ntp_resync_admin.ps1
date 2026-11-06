# ============================================================
# QUAN AI BRAIN — Đồng bộ giờ PC về chuẩn NTP (Duyệt chat 06/11)
# Nguồn sai: PC chậm ~2.5s (sync lần cuối 03/11). Pi5 đang đúng chuẩn.
# ============================================================
Write-Host "== 1. Force resync NTP ==" -ForegroundColor Cyan
w32tm /resync /force
Write-Host "`n== 2. Kiểm tra kết quả ==" -ForegroundColor Cyan
w32tm /query /status
Write-Host "`n== 3. So sánh với giờ chuẩn NTP (python query) ==" -ForegroundColor Cyan
python -c "
import socket, struct, time
from datetime import datetime, timezone
def ntp(h):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
    t0 = time.time(); s.sendto(b'\x1b' + 47*b'\0', (h, 123)); data,_ = s.recvfrom(48); t3 = time.time(); s.close()
    srv = struct.unpack('!I', data[40:44])[0] - 2208988800 + struct.unpack('!I', data[44:48])[0]/2**32
    return (srv + (t3-t0)/2) - time.time()
off = ntp('pool.ntp.org')
print(f'Sai lech PC vs NTP sau resync: {off*1000:+.0f} ms')
print('KET QUA:', 'DONG BO CHUAN (<100ms)' if abs(off) < 0.1 else 'van lech — chay lai lenh 1')
"
Write-Host "`n== HOAN TAT — nhan Enter de dong ==" -ForegroundColor Green
Read-Host
