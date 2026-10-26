import os
import argparse
import logging
from pathlib import Path
from ocr_engine import OCREngine
from label_parser import LabelParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
log = logging.getLogger('ocr_main')

def process_image(image_path: str, use_gpu: bool = False):
    engine = OCREngine(use_gpu=use_gpu)
    parser = LabelParser()
    
    log.info(f"Processing image: {image_path}")
    if not os.path.exists(image_path):
        log.error(f"File not found: {image_path}")
        return
        
    text = engine.extract_text(image_path)
    if not text:
        log.warning("No text extracted from image.")
        return
        
    log.info("Extracted Text:\n" + "-"*40 + f"\n{text}\n" + "-"*40)
    
    parsed_info = parser.parse(text)
    
    log.info("Parsed Information:")
    for key, val in parsed_info.items():
        if key == 'raw_text': continue
        if val:
            log.info(f"  {key}: {val}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Standalone Telecom OCR Module")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("--gpu", action="store_true", help="Enable GPU for EasyOCR")
    
    args = parser.parse_args()
    process_image(args.image_path, args.gpu)
