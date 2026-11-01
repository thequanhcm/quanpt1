"""Configuration model for QUAN AI BRAIN — Raspberry Pi 5 Edge Client.

Designed for edge deployment on Raspberry Pi 5 with touch kiosk display.
Zero core credentials or databases stored on edge device.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
from typing import Any


@dataclass
class EdgeConfig:
    """Settings for Raspberry Pi 5 Edge Kiosk interface."""

    device_id: str = "EDGE-PI5-DESK-01"
    device_label: str = "Bàn Làm Việc Quanpt1"
    core_host: str = "127.0.0.1"
    core_port: int = 8766
    kiosk_host: str = "127.0.0.1"
    kiosk_port: int = 8768
    shared_secret: str = "EDGE_EPHEMERAL_DEV_SECRET_DO_NOT_USE_IN_PROD"
    poll_interval_sec: float = 1.0
    heartbeat_timeout_sec: float = 4.0
    reconnect_delay_sec: float = 2.0
    kiosk_mode: bool = True
    face_only_mode: bool = True  # Strictly display digital face/avatar; hide texts & panels
    display_orientation: str = "landscape"  # "landscape" or "portrait"
    screen_width: int = 1280
    screen_height: int = 720
    wake_word: str = "TONY ơi"
    follow_up_window_sec: float = 15.0
    core_version: str = "0.2.0"
    edge_client_version: str = "0.2.0"
    avatar_version: str = "digital_human_model_a_v1"
    persona_version: str = "1.0.0"
    assistant_name: str = "TONY PHAM"
    config_schema_version: str = "1.0"
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def core_base_url(self) -> str:
        return f"http://{self.core_host}:{self.core_port}"

    @property
    def kiosk_url(self) -> str:
        return f"http://{self.kiosk_host}:{self.kiosk_port}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EdgeConfig:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @classmethod
    def load_from_file(cls, path: Path | str) -> EdgeConfig:
        fpath = Path(path)
        if not fpath.exists():
            return cls()
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = json.load(f)
            return cls.from_dict(content)
        except Exception:
            return cls()

    def save_to_file(self, path: Path | str) -> None:
        fpath = Path(path)
        fpath.parent.mkdir(parents=True, exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
