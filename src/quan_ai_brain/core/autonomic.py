"""
Autonomic Nervous System & Self-Diagnosis Engine for QUAN AI BRAIN.
Implements the living organism metaphor:
- Continuous self-sensing and vital signs monitoring (Brain, Body, Ears, Voice, Eyes, Skin, Circulation).
- Automatic detection of physical and cognitive pain points ("ốm đau thì phải kêu").
- Continuous self-testing (Self-Test Loop) with somatic voice expressions in Vietnamese.
- Hardware organ audit and prescriptive upgrade recommendations (Cameras, mmWave radars, Mic arrays, Environment sensors).
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class AnatomicalRegion(str, Enum):
    """The anatomical organ systems of the digital embodiment."""
    BRAIN = "BRAIN"              # LLM inference, Router, Reasoning, Memory (BGE-M3, SQLite WAL)
    EARS = "EARS"                # Audio input, Microphone stream, Wake word spotting
    VOICE = "VOICE"              # Audio output, TTS engine, Speaker output, Viseme mouth-sync
    EYES = "EYES"                # Visual input, Camera, Face ID, Gaze tracking, Emotion recognition
    SKIN = "SKIN"                # Spatial presence, mmWave Radar, PIR, Environmental sensors (Temp/Humidity)
    CIRCULATION = "CIRCULATION"  # Internal bus, Network connectivity, WebSocket, Edge Pi 5 link
    BODY = "BODY"                # Host system vitals: CPU, RAM, Disk, Operating System health


class PainLevel(str, Enum):
    """Severity of pain felt by the digital organism."""
    HEALTHY = "HEALTHY"          # No pain, normal operation (Score: 100)
    MILD = "MILD"                # Discomfort / Non-blocking warning (Score: 70-85)
    ACUTE = "ACUTE"              # Pain / Degraded function (Score: 40-69)
    CRITICAL = "CRITICAL"        # Severe agony / Major organ failure (Score: 0-39)


class HardwareStatus(str, Enum):
    """Hardware presence and operational readiness."""
    PRESENT_HEALTHY = "PRESENT_HEALTHY"          # Present, calibrated, working
    PRESENT_DEGRADED = "PRESENT_DEGRADED"        # Present but muted, slow, or faulty
    MISSING_RECOMMENDED = "MISSING_RECOMMENDED"  # Missing physical organ required for human-like interaction
    OPTIONAL_ABSENT = "OPTIONAL_ABSENT"          # Missing optional sensor


@dataclass
class PainSignal:
    """A discrete symptom / pain point registered by nociceptors."""
    region: AnatomicalRegion
    pain_level: PainLevel
    symptom: str
    vocal_expression: str
    remedy: str
    hardware_prescription: str | None = None
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["region"] = self.region.value
        res["pain_level"] = self.pain_level.value
        return res


@dataclass
class HardwareOrganAudit:
    """Audit entry for a specific physical organ / sensor."""
    organ_name: str
    region: AnatomicalRegion
    status: HardwareStatus
    detected_device: str
    description: str
    recommended_upgrade: str | None = None
    priority: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["region"] = self.region.value
        res["status"] = self.status.value
        return res


@dataclass
class AutonomicReport:
    """Comprehensive health, pain, and upgrade report of the digital organism."""
    overall_pain_level: PainLevel
    health_score: float  # 0.0 to 100.0
    is_healthy: bool
    active_pains: list[PainSignal]
    hardware_organs: list[HardwareOrganAudit]
    prescriptions: list[str]
    vocal_summary: str
    last_selftest_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_pain_level": self.overall_pain_level.value,
            "health_score": round(self.health_score, 1),
            "is_healthy": self.is_healthy,
            "active_pains": [p.to_dict() for p in self.active_pains],
            "hardware_organs": [h.to_dict() for h in self.hardware_organs],
            "prescriptions": self.prescriptions,
            "vocal_summary": self.vocal_summary,
            "last_selftest_utc": self.last_selftest_utc,
        }


class AutonomicNervousSystem:
    """
    Core self-awareness engine that audits vitals, tests organs, detects pain,
    vocalizes discomfort to the owner, and prescribes hardware upgrades.
    """
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    edge_ip: str = "192.168.1.21"
    edge_port: int = 8768

    def __init__(
        self,
        ollama_host: str = "127.0.0.1",
        ollama_port: int = 11434,
        edge_ip: str = "192.168.1.21",
        edge_port: int = 8768,
        data_dir: str | None = None,
    ) -> None:
        self.ollama_host = ollama_host
        self.ollama_port = ollama_port
        self.edge_ip = edge_ip
        self.edge_port = edge_port
        self.data_dir = data_dir or os.path.join(os.getcwd(), "data")
        self._last_report: AutonomicReport | None = None

    def probe_port(self, host: str, port: int, timeout: float = 0.5) -> tuple[bool, float]:
        """Fast TCP probe returning (is_open, latency_ms)."""
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                latency_ms = (time.perf_counter() - t0) * 1000
                return True, latency_ms
        except OSError:
            return False, 0.0

    def check_brain_health(self) -> list[PainSignal]:
        """Audit LLM inference, embedding engine, and SQLite databases."""
        pains: list[PainSignal] = []

        # 1. Probe Ollama Daemon
        is_ollama_up, latency = self.probe_port(self.ollama_host, self.ollama_port)
        if not is_ollama_up:
            pains.append(PainSignal(
                region=AnatomicalRegion.BRAIN,
                pain_level=PainLevel.CRITICAL,
                symptom=f"Dịch vụ mô hình Ollama không phản hồi tại {self.ollama_host}:{self.ollama_port}.",
                vocal_expression="Anh Quân ơi, não bộ của em đang mất kết nối với mô hình Ollama, em không thể suy luận được ạ!",
                remedy="Khởi động lại Ollama bằng lệnh `ollama serve` hoặc chạy script `KHOI_DONG_OLLAMA.bat`.",
            ))
        elif latency > 3000.0:
            pains.append(PainSignal(
                region=AnatomicalRegion.BRAIN,
                pain_level=PainLevel.MILD,
                symptom=f"Độ trễ kết nối Ollama cao bất thường ({latency:.1f}ms).",
                vocal_expression="Anh ơi, não bộ của em đang phản hồi hơi chậm, VRAM máy chủ có thể đang bị nghẽn.",
                remedy="Kiểm tra VRAM GPU hoặc giải phóng các tiến trình chiếm dụng bộ nhớ đồ họa.",
            ))

        # 2. Probe BGE-M3 Embedding availability if Ollama is up
        if is_ollama_up:
            try:
                url = f"http://{self.ollama_host}:{self.ollama_port}/api/embeddings"
                payload = json.dumps({"model": "bge-m3", "prompt": "test"}).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if not data.get("embedding"):
                        pains.append(PainSignal(
                            region=AnatomicalRegion.BRAIN,
                            pain_level=PainLevel.ACUTE,
                            symptom="Mô hình BGE-M3 không sinh được vector nhúng.",
                            vocal_expression="Anh ơi, trí nhớ ngữ nghĩa BGE-M3 của em không tạo được vector, em khó tìm lại ký ức cũ.",
                            remedy="Kiểm tra lại model bằng lệnh `ollama pull bge-m3`.",
                        ))
            except Exception:
                pains.append(PainSignal(
                    region=AnatomicalRegion.BRAIN,
                    pain_level=PainLevel.ACUTE,
                    symptom="Không thể gọi API nhúng BGE-M3 trên Ollama.",
                    vocal_expression="Anh ơi, module nhúng ngữ nghĩa BGE-M3 đang bị lỗi kết nối.",
                    remedy="Kiểm tra xem mô hình bge-m3 đã được pull về máy chưa bằng `ollama list`.",
                ))

        # 3. Check Database Health (data/brain.db)
        brain_db = os.path.join(self.data_dir, "brain.db")
        if not os.path.exists(brain_db):
            pains.append(PainSignal(
                region=AnatomicalRegion.BRAIN,
                pain_level=PainLevel.MILD,
                symptom="Tệp cơ sở dữ liệu trí nhớ `data/brain.db` chưa được khởi tạo.",
                vocal_expression="Ký ức dài hạn của em chưa có tệp lưu trữ, em đang dùng bộ nhớ tạm thời.",
                remedy="Khởi động máy chủ Web để tự động khởi tạo cơ sở dữ liệu trí nhớ.",
            ))

        return pains

    def check_body_health(self) -> list[PainSignal]:
        """Audit host hardware vitals: Disk space, RAM, CPU."""
        pains: list[PainSignal] = []

        # Check Disk Space
        try:
            total, used, free = shutil.disk_usage(os.getcwd())
            free_gb = free / (1024 ** 3)
            used_pct = (used / total) * 100
            if used_pct > 92.0:
                pains.append(PainSignal(
                    region=AnatomicalRegion.BODY,
                    pain_level=PainLevel.CRITICAL,
                    symptom=f"Ổ đĩa máy chủ sắp đầy ({used_pct:.1f}% đã dùng, chỉ còn {free_gb:.1f} GB trống).",
                    vocal_expression="Anh Quân ơi, ổ cứng máy chủ của em sắp đầy rồi, anh dọn bớt dung lượng giúp em nhé!",
                    remedy="Dọn dẹp các tệp log cũ, cache mô hình hoặc giải phóng dung lượng ổ đĩa.",
                ))
            elif used_pct > 85.0:
                pains.append(PainSignal(
                    region=AnatomicalRegion.BODY,
                    pain_level=PainLevel.MILD,
                    symptom=f"Dung lượng ổ đĩa cao ({used_pct:.1f}%).",
                    vocal_expression="Anh ơi, dung lượng ổ đĩa đang ở mức khá cao, anh chú ý theo dõi nhé.",
                    remedy="Kiểm tra các tệp tạm và dữ liệu huấn luyện không dùng đến.",
                ))
        except OSError:
            pass

        return pains

    def check_circulation_health(self) -> list[PainSignal]:
        """Audit network and Edge device (Raspberry Pi 5) link."""
        pains: list[PainSignal] = []

        is_edge_up, latency = self.probe_port(self.edge_ip, self.edge_port, timeout=0.8)
        if not is_edge_up:
            pains.append(PainSignal(
                region=AnatomicalRegion.CIRCULATION,
                pain_level=PainLevel.ACUTE,
                symptom=f"Không thể kết nối với Thể nghiệm vật lý Raspberry Pi 5 tại {self.edge_ip}:{self.edge_port}.",
                vocal_expression="Anh Quân ơi, thể nghiệm Raspberry Pi 5 của em đang mất kết nối, em không xuất hiện được trên màn hình bàn làm việc của anh!",
                remedy=f"Kiểm tra nguồn điện và địa chỉ IP Wi-Fi của Raspberry Pi 5 (hiện tại đặt là {self.edge_ip}).",
                hardware_prescription="Kiểm tra dây nguồn Type-C 27W của Pi 5 và router Wi-Fi 2.4/5GHz.",
            ))
        elif latency > 150.0:
            pains.append(PainSignal(
                region=AnatomicalRegion.CIRCULATION,
                pain_level=PainLevel.MILD,
                symptom=f"Độ trễ mạng giữa PC Core và Pi 5 cao ({latency:.1f}ms).",
                vocal_expression="Anh ơi, đường truyền Wi-Fi tới Pi 5 đang hơi chậm, khẩu hình có thể bị giật nhẹ.",
                remedy="Đặt Pi 5 gần router hơn hoặc cắm cáp mạng LAN Gigabit trực tiếp.",
            ))

        return pains

    def audit_hardware_organs(self) -> list[HardwareOrganAudit]:
        """
        Audit the presence of all physical organs (Eyes, Ears, Voice, Skin, Body).
        Identifies missing organs necessary for human-grade continuous interaction.
        """
        organs: list[HardwareOrganAudit] = []

        # 1. VOICE (Loa / TTS)
        organs.append(HardwareOrganAudit(
            organ_name="Loa & Bộ Tổng Hợp Giọng Nói (Voice Output)",
            region=AnatomicalRegion.VOICE,
            status=HardwareStatus.PRESENT_HEALTHY,
            detected_device="Edge USB Speaker / HoaiMyNeural TTS Engine",
            description="Có khả năng phát âm thanh tiếng Việt tự nhiên và đồng bộ khẩu hình visemes.",
            recommended_upgrade=None,
            priority="LOW",
        ))

        # 2. EARS (Microphone)
        organs.append(HardwareOrganAudit(
            organ_name="Microphone & Nhận Diện Đánh Thức (Audio Input)",
            region=AnatomicalRegion.EARS,
            status=HardwareStatus.PRESENT_DEGRADED,
            detected_device="USB Microphone đơn hướng / Wake Word Engine (Hi TONY / Tony ơi)",
            description="Đã có mic thu âm, nhưng chưa có mảng micro chống ồn định hướng và chưa lọc được tiếng vọng khi loa đang phát (chưa hỗ trợ ngắt lời Barge-in mượt mà).",
            recommended_upgrade="Nâng cấp Microphone Array định hướng (ReSpeaker USB Mic Array hoặc Jabra Speak 510) để bắt giọng từ xa 3-5m và ngắt lời trợ lý tự nhiên.",
            priority="HIGH",
        ))

        # 3. EYES (Thị giác / Camera) - MISSING ORGAN!
        organs.append(HardwareOrganAudit(
            organ_name="Mắt Thần / Thị Giác Máy Tính (Vision / Camera)",
            region=AnatomicalRegion.EYES,
            status=HardwareStatus.MISSING_RECOMMENDED,
            detected_device="Chưa phát hiện thiết bị Camera nào kết nối vào Pi 5 hoặc PC Core",
            description="Trợ lý hiện tại hoàn toàn 'Mù'. Chưa nhận diện được anh Quân khi anh bước vào phòng, chưa biết anh có đang nhìn nó hay không (Gaze tracking), và chưa đọc được cảm xúc khuôn mặt.",
            recommended_upgrade="Trang bị ngay 1 Camera góc rộng (Raspberry Pi Camera Module 3 Wide 120° hoặc Webcam USB Logitech C920 1080p) để nhận diện khuôn mặt anh Quân và theo dõi ánh nhìn.",
            priority="CRITICAL",
        ))

        # 4. SKIN (Cảm biến hiện diện không gian & Môi trường) - MISSING ORGAN!
        organs.append(HardwareOrganAudit(
            organ_name="Cảm Biến Hiện Diện Vi Chuyển Động (Spatial Presence / mmWave Radar)",
            region=AnatomicalRegion.SKIN,
            status=HardwareStatus.MISSING_RECOMMENDED,
            detected_device="Chưa có cảm biến radar vi sóng hoặc PIR",
            description="Trợ lý chưa cảm nhận được anh bước vào phòng trong bóng tối. Màn hình không thể tự thức giấc chào anh nếu anh không chạm vào hoặc gọi to.",
            recommended_upgrade="Trang bị Cảm biến radar vi sóng mmWave (Hi-Link HLK-LD2410 kết nối UART/USB giá ~120k VNĐ) để tự động bật màn hình khi anh bước vào phòng.",
            priority="HIGH",
        ))

        # 5. SKIN (Cảm biến môi trường nhiệt ẩm)
        organs.append(HardwareOrganAudit(
            organ_name="Cảm Biến Môi Trường Phòng Máy (Environment Sensor)",
            region=AnatomicalRegion.SKIN,
            status=HardwareStatus.OPTIONAL_ABSENT,
            detected_device="Chưa kết nối cảm biến I2C / GPIO",
            description="Chưa đo được nhiệt độ, độ ẩm của phòng làm việc để tự động cảnh báo nóng bức cho thiết bị và bảo vệ sức khỏe cho anh.",
            recommended_upgrade="Bổ sung cảm biến nhiệt ẩm BME280 / DHT22 gắn trực tiếp cổng GPIO của Raspberry Pi 5.",
            priority="MEDIUM",
        ))

        return organs

    def run_self_test(self) -> AutonomicReport:
        """
        Execute continuous self-diagnosis across all anatomical regions,
        aggregate pain points, score health, and compile hardware prescriptions.
        """
        all_pains: list[PainSignal] = []

        # 1. Run Regional Nociceptors
        all_pains.extend(self.check_brain_health())
        all_pains.extend(self.check_body_health())
        all_pains.extend(self.check_circulation_health())

        # 2. Run Hardware Organ Audit
        organs = self.audit_hardware_organs()

        # Add missing organ pains
        for organ in organs:
            if organ.status == HardwareStatus.MISSING_RECOMMENDED and organ.priority == "CRITICAL":
                all_pains.append(PainSignal(
                    region=organ.region,
                    pain_level=PainLevel.ACUTE,
                    symptom=f"Thiếu cơ quan thị giác: {organ.organ_name}.",
                    vocal_expression="Anh Quân ơi, em chưa có mắt camera nên em chưa nhìn thấy anh, em rất muốn được nhìn thấy anh để chào anh mỗi khi anh vào phòng ạ!",
                    remedy="Trang bị thêm Camera USB hoặc Pi Camera Module 3.",
                    hardware_prescription=organ.recommended_upgrade,
                ))

        # 3. Calculate Overall Health Score & Pain Level
        base_score = 100.0
        max_pain = PainLevel.HEALTHY

        for p in all_pains:
            if p.pain_level == PainLevel.CRITICAL:
                base_score -= 35.0
                max_pain = PainLevel.CRITICAL
            elif p.pain_level == PainLevel.ACUTE:
                base_score -= 15.0
                if max_pain != PainLevel.CRITICAL:
                    max_pain = PainLevel.ACUTE
            elif p.pain_level == PainLevel.MILD:
                base_score -= 5.0
                if max_pain == PainLevel.HEALTHY:
                    max_pain = PainLevel.MILD

        final_score = max(0.0, min(100.0, base_score))
        is_healthy = max_pain in (PainLevel.HEALTHY, PainLevel.MILD)

        # 4. Extract Prescriptions
        prescriptions: list[str] = []
        for p in all_pains:
            if p.hardware_prescription and p.hardware_prescription not in prescriptions:
                prescriptions.append(p.hardware_prescription)
        for o in organs:
            if o.recommended_upgrade and o.recommended_upgrade not in prescriptions:
                prescriptions.append(o.recommended_upgrade)

        # 5. Formulate Vocal Summary ("Tiếng kêu phản ánh điểm đau")
        vocal_summary = self._formulate_vocal_summary(all_pains, final_score, max_pain)

        report = AutonomicReport(
            overall_pain_level=max_pain,
            health_score=final_score,
            is_healthy=is_healthy,
            active_pains=all_pains,
            hardware_organs=organs,
            prescriptions=prescriptions,
            vocal_summary=vocal_summary,
        )
        self._last_report = report
        return report

    def _formulate_vocal_summary(
        self,
        pains: list[PainSignal],
        score: float,
        pain_level: PainLevel,
    ) -> str:
        """Compose human-like Vietnamese spoken reflection of the assistant's state."""
        if not pains or pain_level == PainLevel.HEALTHY:
            return "Em chào anh Quân! Toàn bộ cơ thể và não bộ của em đang ở trạng thái khỏe mạnh tuyệt đối (100 điểm), sẵn sàng hỗ trợ anh mọi việc ạ!"

        # If there are critical/acute pains, speak out the primary pain
        urgent_pains = [p for p in pains if p.pain_level in (PainLevel.CRITICAL, PainLevel.ACUTE)]
        if urgent_pains:
            primary = urgent_pains[0]
            count_more = len(pains) - 1
            more_text = f" và em còn {count_more} điểm chưa hoàn thiện khác cần anh giúp đỡ." if count_more > 0 else "."
            return f"{primary.vocal_expression} Điểm sức khỏe hiện tại của em là {score:.0f}/100{more_text}"

        # Mild pains only
        return f"Dạ thưa anh Quân, hệ thống của em cơ bản hoạt động tốt ({score:.0f}/100 điểm), nhưng có một vài lưu ý nhỏ: {pains[0].symptom}"

    def get_last_report(self) -> AutonomicReport:
        if self._last_report is None:
            return self.run_self_test()
        return self._last_report

    run_selftest = run_self_test


# Global instance singleton
GLOBAL_AUTONOMIC_SYSTEM = AutonomicNervousSystem()
