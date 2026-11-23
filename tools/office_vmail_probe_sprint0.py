# -*- coding: utf-8 -*-
"""Sprint 0 probe — kiểm chứng KHẢ NĂNG SOAP cho Vmail Connector (READ-ONLY).

Card TASK-VMAIL-S1 tiền điều kiện. Chỉ gọi các request ĐỌC của Zimbra SOAP:
- GetFolderRequest (list_folders)
- GetInfoRequest (get_account_profile)
- SearchRequest types="conversation" (get_thread)
KHÔNG mark read, KHÔNG xóa, KHÔNG gửi. Timeout tổng 90s (bài học imaplib hang).
"""
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, r'E:/BRAIN/tools')
sys.path.insert(0, r'E:/BRAIN/user, pass, token')

import mail_reader as mr

out_lines = []
try:
    token = mr._auth()
    out_lines.append("AUTH: OK (authToken nhận được, KHÔNG in giá trị)")

    # 1. GetFolderRequest — list_folders khả thi?
    try:
        out = mr._soap(
            f'<GetFolderRequest xmlns="{mr.MAIL_NS}"><folder path="/"/></GetFolderRequest>',
            token)
        root = ET.fromstring(out)
        folders = [f.get("name") for f in root.iter(f"{{{mr.MAIL_NS}}}folder")]
        out_lines.append(f"GETFOLDER: OK — {len(folders)} folder: {folders[:12]}")
    except Exception as e:
        out_lines.append(f"GETFOLDER: FAIL — {type(e).__name__}: {e}")

    # 2. GetInfoRequest — get_account_profile khả thi?
    try:
        out = mr._soap('<GetInfoRequest xmlns="urn:zimbraAccount" sections="ident"/>', token)
        root = ET.fromstring(out)
        name_el = root.find(f'.//{{urn:zimbraAccount}}displayName')
        email_el = root.find(f'.//{{urn:zimbraMail}}attrs/{{urn:zimbraMail}}_mail')
        display = name_el.text if name_el is not None else "(n/a)"
        out_lines.append(f"GETINFO: OK — displayName={display}")
    except Exception as e:
        out_lines.append(f"GETINFO: FAIL — {type(e).__name__}: {e}")

    # 3. SearchRequest types="conversation" — get_thread khả thi?
    try:
        body = (f'<SearchRequest xmlns="{mr.MAIL_NS}" types="conversation" limit="3" '
                f'sortBy="dateDesc"><query>in:inbox</query></SearchRequest>')
        out = mr._soap(body, token)
        root = ET.fromstring(out)
        convs = [(c.get("id"), mr._clean((c.find(f"{{{mr.MAIL_NS}}}su").text if c.find(f"{{{mr.MAIL_NS}}}su") is not None else "")))
                 for c in root.iter(f"{{{mr.MAIL_NS}}}c")]
        out_lines.append(f"CONV-SEARCH: OK — {len(convs)} conversation (top id/subject): {convs[:3]}")
    except Exception as e:
        out_lines.append(f"CONV-SEARCH: FAIL — {type(e).__name__}: {e}")

    # 4. Thread theo subject (fallback khi conv-id không dùng được) — SearchRequest
    try:
        items = mr._search(token, 'in:inbox subject:"tiến độ"', 5)
        out_lines.append(f"SUBJECT-SEARCH: OK — {len(items)} hit cho 'subject:tiến độ'")
    except Exception as e:
        out_lines.append(f"SUBJECT-SEARCH: FAIL — {type(e).__name__}: {e}")

except Exception as e:
    out_lines.append(f"FATAL: {type(e).__name__}: {e}")

for ln in out_lines:
    print(ln)
