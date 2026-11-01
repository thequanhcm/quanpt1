import os
import threading
import logging
from typing import List, Optional
import numpy as np

try:
    from PIL import Image, ImageOps, ImageFilter
    import cv2
except ImportError:
    Image = None
    cv2 = None

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    easyocr = None
    HAS_EASYOCR = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    pytesseract = None
    HAS_TESSERACT = False

log = logging.getLogger('ocr_engine')

class OCREngine:
    def __init__(self, langs: List[str] = None, use_gpu: bool = False):
        if langs is None:
            langs = ['en', 'vi']
        self.langs = langs
        self.use_gpu = use_gpu
        self._easyocr_reader = None
        self.ocr_lock = threading.Lock()
        
    def _get_easyocr_reader(self):
        if not HAS_EASYOCR:
            return None
        with self.ocr_lock:
            if self._easyocr_reader is None:
                log.info(f"Loading EasyOCR with langs: {self.langs}")
                self._easyocr_reader = easyocr.Reader(self.langs, gpu=self.use_gpu)
            return self._easyocr_reader

    def preprocess_image(self, image_path: str):
        if Image is None or cv2 is None:
            log.warning("Pillow or OpenCV not installed.")
            return None
            
        try:
            # Dùng OpenCV đọc ảnh và tăng cường chất lượng
            img_cv = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if img_cv is None:
                return None
            
            # Khử nhiễu
            img_cv = cv2.fastNlMeansDenoising(img_cv, None, 10, 7, 21)
            
            # Cân bằng Histogram cục bộ (CLAHE) để làm rõ chữ trên tem dán
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            img_cv = clahe.apply(img_cv)
            
            # Resize lên nếu ảnh quá nhỏ
            h, w = img_cv.shape
            if max(w, h) < 1200:
                scale = 1200 / max(w, h)
                img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
                
            # Chuyển về PIL Image cho Tesseract
            img_pil = Image.fromarray(img_cv)
            return img_pil, img_cv
        except Exception as e:
            log.exception(f"Preprocessing error: {e}")
            return None, None

    def extract_text(self, image_path: str) -> str:
        texts = []
        img_pil, img_cv = self.preprocess_image(image_path)
        
        # 1. EasyOCR
        if HAS_EASYOCR:
            try:
                reader = self._get_easyocr_reader()
                # Dùng ảnh chưa qua biến đổi OpenCV vì EasyOCR có cơ chế học sâu xử lý tốt
                raw_texts = reader.readtext(str(image_path), detail=0, paragraph=True)
                if raw_texts:
                    texts.extend(raw_texts)
            except Exception as e:
                log.error(f"EasyOCR error: {e}")

        # 2. Tesseract (Fallback / Supplement)
        if HAS_TESSERACT and img_pil is not None:
            try:
                # Cấu hình OCR engine mode (OEM) 3 (Mặc định) và Page segmentation mode (PSM) 11 (Sparse text)
                config = '--oem 3 --psm 11'
                txt = pytesseract.image_to_string(img_pil, lang='+'.join(self.langs), config=config)
                if txt.strip():
                    texts.append(txt.strip())
            except Exception as e:
                log.error(f"Tesseract error: {e}")
                
        return '\n'.join([t for t in texts if t]).strip()
