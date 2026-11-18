"""Tests — speech_utils: bộ công cụ xử lý chữ quanh giọng nói cho CHERRY.

Nguồn: port từ vivi-agent (app/voice.py, app/lead_in.py) 18/11/2026.
Kiểm tra hành vi đặc tả bởi ADR vivi (0054/0058/0071/0074) + fail-open.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quan_ai_brain.cognition.speech_utils import (  # noqa: E402
    SentenceSplitter,
    clean_for_speech,
    is_lead_in,
    match_wake,
    split_first_sentence,
    strip_lead_in,
    words_equal,
)


# ============================================================
# 1. words_equal — so từ, không quan trọng dấu câu / hoa thường
# ============================================================

class TestWordsEqual:
    def test_same_with_punctuation(self):
        assert words_equal("Xin chào, Cherry!", "xin chào cherry") is True

    def test_word_changed(self):
        assert words_equal("mở cửa sổ 50%", "mở cửa sổ 60%") is False

    def test_word_order_changed(self):
        assert words_equal("mở cửa sổ", "sổ mở cửa") is False

    def test_empty(self):
        assert words_equal("", "") is True

    def test_diacritics_kept(self):
        # "sử" khác "su" — dấu thanh phải được giữ khi so
        assert words_equal("sử", "su") is False


# ============================================================
# 2. match_wake — "Cherry ơi", "Hey Cherry", cách STT ghi sai
# ============================================================

class TestMatchWake:
    def test_wake_oi(self):
        ok, cmd = match_wake("Cherry ơi mở cửa sổ ghế lái 50%")
        assert ok is True
        assert cmd == "mở cửa sổ ghế lái 50%"

    def test_wake_with_lead_e(self):
        ok, cmd = match_wake("ê Cherry ơi mở nhạc")
        assert ok is True
        assert cmd == "mở nhạc"

    def test_wake_no_diacritics(self):
        ok, cmd = match_wake("cherry oi bat dieu hoa")
        assert ok is True
        assert cmd == "bat dieu hoa"

    def test_stt_misspell_2word(self):
        # STT ghi "Cherry" thành "che ri" (2 âm rời)
        ok, cmd = match_wake("che ri ơi bật đèn")
        assert ok is True
        assert cmd == "bật đèn"

    def_stt_misspell_one = None  # placeholder để tránh lỗi class-scoped

    def test_stt_misspell_one_word(self):
        # STT ghi "cherri" dính liền
        ok, _ = match_wake("cherri ơi bật quạt")
        assert ok is True

    def test_wake_hey_without_oi(self):
        ok, cmd = match_wake("Hey Cherry mở cốp")
        assert ok is True
        assert cmd == "mở cốp"

    def test_wake_hey_stt_hai(self):
        # STT ghi "hey" thành "hai" (ADR-0074)
        ok, _ = match_wake("hai Cherry cho mình biết giờ")
        assert ok is True

    def test_name_in_middle_not_wake(self):
        # Nhắc tên giữa câu KHÔNG bật
        ok, _ = match_wake("hôm nay Cherry có gì vui không")
        assert ok is False

    def test_empty(self):
        assert match_wake("") == (False, "")

    def test_command_keeps_numbers(self):
        # Giữ nguyên "50%", "22,5", dấu câu sau wake
        ok, cmd = match_wake("Cherry ơi, chỉnh 22,5 độ!")
        assert ok is True
        assert cmd == "chỉnh 22,5 độ!"


# ============================================================
# 3. clean_for_speech — làm sạch chữ trước TTS
# ============================================================

class TestCleanForSpeech:
    def test_strips_markdown_bold(self):
        assert clean_for_speech("**Quan trọng**: pin 78%") == "Quan trọng: pin 78%"

    def test_strips_link_keep_text(self):
        assert clean_for_speech("xem [tài liệu](http://x.com/y) nhé") == "xem tài liệu nhé"

    def test_strips_image(self):
        assert clean_for_speech("ảnh ![a](x.png) ở đây") == "ảnh ở đây"

    def test_strips_citation(self):
        assert clean_for_speech("pin 78% [1,2] hết") == "pin 78% hết"

    def test_strips_url(self):
        assert clean_for_speech("mở http://192.168.1.21:8768 kiosk") == "mở kiosk"

    def test_strips_src_line(self):
        s = clean_for_speech("pin 78%\nNguồn: sổ tay VF9")
        assert "Nguồn" not in s

    def test_cut_at_sentence_boundary(self):
        long_text = ". ".join(f"Câu thứ {i} khá dài" for i in range(1, 200)) + "."
        out = clean_for_speech(long_text, max_chars=200)
        assert len(out) <= 210
        assert out.endswith((".", "!", "?")) or len(out) <= 200

    def test_empty(self):
        assert clean_for_speech("") == ""


# ============================================================
# 4. SentenceSplitter — cắt câu streaming
# ============================================================

class TestSentenceSplitter:
    def test_split_simple(self):
        sp = SentenceSplitter()
        out = []
        out += sp.feed("Xin chào. Hôm nay")
        out += sp.feed(" trời đẹp. ")
        out.append(sp.flush())
        joined = " ".join(x for x in out if x.strip())
        assert "Xin chào." in joined
        assert "Hôm nay trời đẹp." in joined

    def test_not_cut_decimal(self):
        # "22,5" không được cắt giữa chừng (dấu phẩy thập phân) — phải nằm nguyên trong
        # câu phát ra hoặc buffer flush
        sp = SentenceSplitter()
        out = sp.feed("Chỉnh 22,5 độ.")
        out.append(sp.flush())
        assert any("22,5" in s for s in out)

    def test_not_cut_short_num(self):
        # "3.5" không cắt giữa số — nằm nguyên trong câu phát ra hoặc buffer flush
        sp = SentenceSplitter()
        out = sp.feed("Điều chỉnh 3.5 bar.")
        out.append(sp.flush())
        assert any("3.5" in s for s in out)

    def test_short_fragment_carried(self):
        # "1." quá ngắn phải ghép với câu sau, không đọc riêng
        sp = SentenceSplitter()
        out = sp.feed("1. ")
        out += sp.feed("Chỉnh điều hòa. ")
        # "1. Chỉnh điều hòa." phải thành 1 câu (hoặc nằm trong buffer đến flush)
        all_text = " ".join(out) + " " + sp.flush()
        assert "1." in all_text

    def test_flush_empty(self):
        sp = SentenceSplitter()
        sp.feed("Câu đầy đủ. ")
        # "Câu đầy đủ." đã phát qua feed (kết thúc bằng ". "); flush trả rỗng
        assert sp.flush() == ""

    def test_soft_cut_long_sentence(self):
        # Câu dài không dấu chấm → cắt ở dấu phẩy sau soft_chars
        sp = SentenceSplitter(soft_chars=30)
        long_sent = "a" * 40 + ", " + "b" * 40 + ", " + "c" * 40
        out = sp.feed(long_sent)
        assert len(out) >= 1

    def test_incremental_feed(self):
        sp = SentenceSplitter()
        # Feed từng ký tự — tổng văn bản cuối vẫn đủ
        collected = []
        for ch in "Một hai ba. Bốn năm sáu.":
            collected += sp.feed(ch)
        collected.append(sp.flush())
        assert "Một hai ba." in " ".join(collected)


# ============================================================
# 5. is_lead_in + strip_lead_in — lọc câu dẫn (ADR-0071)
# ============================================================

class TestLeadIn:
    def test_lead_in_vn(self):
        assert is_lead_in("Mình cần tra cứu thông tin.") is True

    def test_lead_in_wait(self):
        assert is_lead_in("Bạn chờ mình một chút.") is True

    def test_lead_in_en(self):
        assert is_lead_in("I'll look that up for you.") is True

    def test_not_lead_in_long(self):
        # >90 ký tự là câu trả lời thật, không phải câu dẫn
        long = "Mình cần tra cứu thông tin này từ tài liệu sổ tay xe để trả lời chính xác nhất cho bạn."
        assert is_lead_in(long) is False

    def test_not_lead_in_with_number(self):
        # Có số liệu → là nội dung thật
        assert is_lead_in("Mình tra thấy pin 78%.") is False

    def test_not_lead_in_result(self):
        assert is_lead_in("Mình tra thấy thông tin đó rồi.") is False

    def test_strip_lead_in(self):
        out = strip_lead_in("Mình cần tra sổ tay trước. Pin xe là 78%.")
        assert out.startswith("Pin")

    def test_strip_keeps_if_empty(self):
        # Bỏ hết thì giữ nguyên bản gốc
        src = "Mình cần tra."
        assert strip_lead_in(src) == src

    def test_strip_two_sentences(self):
        out = strip_lead_in("Mình sẽ tra cứu. Bạn chờ mình chút. Đáp án là 78%.")
        assert out.startswith("Đáp án")

    def test_strip_no_lead(self):
        src = "Pin xe là 78%."
        assert strip_lead_in(src) == src
