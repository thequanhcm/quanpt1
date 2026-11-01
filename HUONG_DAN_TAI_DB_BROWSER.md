# 📥 HƯỚNG DẪN TẢI & CÀI ĐẶT DB BROWSER FOR SQLITE

## 🎯 Bước 1: Tải về

### Link tải chính thức:
**https://github.com/sqlitebrowser/sqlitebrowser/releases**

### Lựa chọn cho máy anh (Windows 10 64-bit):

✅ **DB Browser for SQLite - Standard installer for 64-bit Windows**

**Link trực tiếp:**
```
https://github.com/sqlitebrowser/sqlitebrowser/releases/download/v3.13.1/DB.Browser.for.SQLite.3.13.1-win64.exe
```

**Hoặc:**
1. Mở trình duyệt (Chrome/Edge)
2. Truy cập: https://github.com/sqlitebrowser/sqlitebrowser/releases
3. Tìm phiên bản mới nhất (ví dụ: v3.13.1)
4. Click vào **"DB Browser for SQLite - Standard installer for 64-bit Windows"**
5. File sẽ tự động tải về: `DB.Browser.for.SQLite.3.13.1-win64.exe`

---

## 🚀 Bước 2: Cài đặt

1. **Double-click** file vừa tải về
2. **Next** → **I Agree** (chấp nhận license)
3. **Chọn thư mục cài đặt** (mặc định: `C:\Program Files\DB Browser for SQLite`)
4. **Next** → **Install**
5. **Finish** (khởi động ngay)

**Lưu ý:**
- ✅ Không cần Administrator nếu cài vào thư mục user
- ✅ Tự động tạo shortcut trên Desktop
- ✅ ~30 MB dung lượng

---

## 💡 Bước 3: Sử dụng với brain.db

### Mở database:
1. **Mở DB Browser for SQLite**
2. **File** → **Open Database** (hoặc Ctrl+O)
3. **Browse** → Chọn: `E:\AI\QUAN AI BRAIN\data\brain.db`
4. **Open**

### Xem/trí nhớ:
1. **Click tab "Browse Data"**
2. **Chọn table:** `semantic_memory`
3. **Xem tất cả trí nhớ** đã lưu
4. **Tìm kiếm:** Ctrl+F → nhập từ khóa (ví dụ: "phương lan")

### Thêm trí nhớ mới:
1. **Click tab "Edit Data"**
2. **Chọn table:** `semantic_memory`
3. **Click "New Record"**
4. **Điền thông tin:**
   - `id`: UUID (tự tạo hoặc để NULL)
   - `statement`: "Nội dung trí nhớ"
   - `source_ref`: "manual"
   - `approved_by`: "owner"
   - `regression_passed`: 1
5. **Click "Write Changes"** (icon đĩa mềm)

### Chạy SQL query:
1. **Click tab "Execute SQL"**
2. **Nhập query:**
   ```sql
   SELECT * FROM semantic_memory 
   WHERE statement LIKE '%phương lan%';
   ```
3. **Click "Execute"** (F5)

---

## 🎨 Giao diện DB Browser for SQLite

```
┌─────────────────────────────────────────────────────┐
│  DB Browser for SQLite                              │
├─────────────────────────────────────────────────────┤
│  [Database: brain.db]                               │
│                                                     │
│  ┌──────────────┬────────────────────────────────┐ │
│  │ Database     │ Tables:                        │ │
│  │ Structure    │  • semantic_memory (1841)      │ │
│  │ Browse Data  │  • episodes (2180)             │ │
│  │ Edit Data    │  • candidate_knowledge (3454)  │ │
│  │ Execute SQL  │  • ...                         │ │
│  └──────────────┴────────────────────────────────┘ │
│                                                     │
│  Records:                                           │
│  ┌───────────────────────────────────────────────┐ │
│  │ ID | Statement | Source | Approved | Date    │ │
│  ├───────────────────────────────────────────────┤ │
│  │ ...| Vợ anh...| manual | owner    | 2026-... │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  [Write Changes] [Revert] [New Record] [Delete]    │
└─────────────────────────────────────────────────────┘
```

---

## 🆚 So sánh với DBeaver

| Tính năng | DB Browser | DBeaver |
|-----------|------------|---------|
| **Đơn giản** | ✅ Rất dễ | ⚠️ Phức tạp hơn |
| **Nhẹ** | ✅ ~30 MB | ⚠️ ~100 MB |
| **Chuyên SQLite** | ✅ Tối ưu | ✅ Tốt |
| **Giao diện** | ✅ Đơn giản | ⚠️ Nhiều tính năng |
| **Khuyến nghị** | **✅ Cho anh** | Đã có sẵn |

**Lựa chọn:**
- **DB Browser:** Nếu muốn đơn giản, nhanh, dễ dùng
- **DBeaver:** Nếu đã quen, có nhiều database khác

---

## 📱 Alternative: Portable Version

Nếu không muốn cài đặt:

**Tải:** DB Browser for SQLite - .zip (no installer) for 64-bit Windows

**Cách dùng:**
1. Tải file `.zip`
2. Giải nén vào thư mục (ví dụ: `E:\Tools\DB Browser`)
3. Double-click `DBBrowserForSQLite.exe` để chạy
4. **Không cần cài đặt** - chạy ngay

---

## ✅ Kiểm tra sau cài đặt

Sau khi cài đặt, mở DB Browser và:

1. **File** → **Open Database**
2. Chọn: `E:\AI\QUAN AI BRAIN\data\brain.db`
3. **Browse Data** tab → Chọn `semantic_memory`
4. Tìm kiếm "phương lan" → **Phải thấy 1 record**

**Nếu thấy:** ✅ Thành công!

---

## 🆘 Xử lý sự cố

### Không tải được?
- **Thay link:** https://sqlitebrowser.org/dl/
- **Chọn:** Windows 64-bit installer
- **Click:** Download button

### Không mở được brain.db?
- **Check:** File không bị lock (Right-click → Properties → Unblock)
- **Check:** Không mở bằng file khác (close VS Code, Python)

### Lỗi "database is locked"?
- **Close** tất cả ứng dụng đang dùng brain.db
- **Restart** DB Browser

---

## 🎯 Quick Start

**Sau khi cài đặt:**

```
1. Mở DB Browser for SQLite
2. Open: E:\AI\QUAN AI BRAIN\data\brain.db
3. Tab "Browse Data" → Table: semantic_memory
4. Tìm "phương lan" → Thấy record ✅
5. Tab "Execute SQL":
   SELECT * FROM semantic_memory 
   WHERE statement LIKE '%vợ%';
6. Xem kết quả → Thành công! 🎉
```

---

## 📞 Hỗ trợ

**Nếu gặp vấn đề:**
1. **Screenshot** lỗi
2. **Gửi** cho em
3. **Em** sẽ hướng dẫn chi tiết

**Hoặc dùng script Python thay thế:**
```bash
python tools/add_personal_memory.py "Nội dung" --tags tag1,tag2
python tools/add_personal_memory.py --search "từ khóa"
```

---

**Chúc anh thành công!** 🚀

Nếu cần hỗ trợ thêm, anh cứ nhắn em! 😊