import re
from typing import Dict, Any, List

class LabelParser:
    def __init__(self):
        # Các mẫu Regex đặc trưng viễn thông (Cập nhật đa dạng hơn)
        self.patterns = {
            'rack_name': r'\b[A-Z0-9]+_R[0-9]+_G[0-9]+\b', # VD: PDL1_R21_G02
            'device_code': r'\bPDL[0-9A-Z]{5,15}\b',       # VD: PDL9102DWP31
            'cable_odf': r'\bPDL[0-9]+MOF[0-9A-Z]+ODF[0-9A-Z]+(?:[/\s]*[0-9,\.]+)?\b', # VD: PDL9202MOF06ODF14A/ 09,10
            'port_slot': r'\b(?:SL|Slot)\s*[0-9]+(?:/[0-9A-Za-z\.]+)?\b',   # VD: SL1/P.IN, SL5/3, Slot 3/2
            'shelf': r'\bShelf\s*[0-9]+\b',                # VD: Shelf 6
            'dxc_node': r'\bDXC[0-9]+\b',                  # VD: DXC4
            'customer': r'\b(?:KH|Khách hàng|Cty|CMC)\s+[A-Za-z0-9\s]+\b', # VD: KH Techcombank, Khách hàng AWS
            'direction': r'\b(?:Fr|To|From)\s*:\s*([A-Za-z0-9_/\s\.,\(\)]+)' # VD: Fr: PDL9202DWB51
        }
        
    def _norm_text(self, text: str) -> str:
        # Thay thế các ký tự xuống dòng bằng khoảng trắng
        text = text.replace('\n', ' ')
        return ' '.join(text.split())

    def parse(self, ocr_text: str) -> Dict[str, Any]:
        result = {
            'raw_text': ocr_text,
            'racks': [],
            'devices': [],
            'cables_odf': [],
            'ports': [],
            'shelves': [],
            'dxc_nodes': [],
            'customers': [],
            'directions': [],
            'other_keywords': []
        }
        
        norm_txt = self._norm_text(ocr_text)
        
        # Bóc tách bằng Regex
        result['racks'] = list(set(re.findall(self.patterns['rack_name'], norm_txt, re.IGNORECASE)))
        result['devices'] = list(set(re.findall(self.patterns['device_code'], norm_txt, re.IGNORECASE)))
        result['cables_odf'] = list(set(re.findall(self.patterns['cable_odf'], norm_txt, re.IGNORECASE)))
        result['ports'] = list(set(re.findall(self.patterns['port_slot'], norm_txt, re.IGNORECASE)))
        result['shelves'] = list(set(re.findall(self.patterns['shelf'], norm_txt, re.IGNORECASE)))
        result['dxc_nodes'] = list(set(re.findall(self.patterns['dxc_node'], norm_txt, re.IGNORECASE)))
        result['customers'] = [c.strip() for c in set(re.findall(self.patterns['customer'], norm_txt, re.IGNORECASE))]
        result['directions'] = [d.strip() for d in set(re.findall(self.patterns['direction'], norm_txt, re.IGNORECASE))]
        
        # Tìm thêm một số keyword thông dụng
        for keyword in ['AWS', 'MAIN', 'Viettel', 'Bank', 'HNI', 'P.HN']:
            if re.search(r'\b' + re.escape(keyword) + r'\b', norm_txt, re.IGNORECASE):
                result['other_keywords'].append(keyword)
                
        return result
