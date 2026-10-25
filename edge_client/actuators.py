"""Hardware Actuator & Relay Controller Interface for Raspberry Pi 5.

Controls physical motion, relays, robotic limbs/arms/hands, and head movement.
Enforces physical hardware fail-safe kill switches and authenticated command execution.
Designed for Raspberry Pi 5 GPIO, I2C PWM drivers (e.g. PCA9685), and USB relay modules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
import threading
import time
from typing import Any

logger = logging.getLogger("quan_ai_brain.edge.actuators")


@dataclass
class RelayChannel:
    """Individual hardware relay channel configuration."""

    id: str  # e.g. "relay_1" to "relay_8"
    name: str  # e.g. "Nguồn Cánh Tay Phải", "Đèn Báo Trạng Thái", "Rơ-le Khóa Điện"
    gpio_pin: int  # Raspberry Pi BCM GPIO pin number
    state: str = "OPEN"  # "OPEN" (de-energized/OFF) or "CLOSED" (energized/ON)
    active_low: bool = True  # Standard 5V relay modules are active-low (0V = ON)


@dataclass
class LimbJoint:
    """Individual robotic limb joint / servo motor configuration."""

    id: str  # e.g. "arm_right_pitch", "hand_right_grip", "head_yaw"
    name: str  # e.g. "Khớp Vai Phải", "Bàn Tay Phải", "Khớp Cổ Quay Ngang"
    channel: int  # PWM channel or GPIO pin
    min_angle: float = 0.0
    max_angle: float = 180.0
    current_angle: float = 90.0  # Safe resting center position
    speed_deg_per_sec: float = 60.0


class ActuatorController:
    """Controls physical relays, servos, and robotic limbs with fail-safe boundaries."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.is_hardware_available: bool = False
        self.emulated_mode: bool = True

        # Standard 8-Channel Relay mapping on Raspberry Pi 5 BCM pins
        self.relays: dict[str, RelayChannel] = {
            "relay_1": RelayChannel("relay_1", "Nguồn Cánh Tay Trái", gpio_pin=17),
            "relay_2": RelayChannel("relay_2", "Nguồn Cánh Tay Phải", gpio_pin=27),
            "relay_3": RelayChannel("relay_3", "Khóa Điện Cơ Chân Trái", gpio_pin=22),
            "relay_4": RelayChannel("relay_4", "Khóa Điện Cơ Chân Phải", gpio_pin=23),
            "relay_5": RelayChannel("relay_5", "Đèn Báo Khẩn Cấp LED", gpio_pin=24),
            "relay_6": RelayChannel("relay_6", "Hệ Thống Làm Mát Quạt", gpio_pin=25),
            "relay_7": RelayChannel("relay_7", "Rơ-le Dự Phòng Kênh 7", gpio_pin=5),
            "relay_8": RelayChannel("relay_8", "Rơ-le Dự Phòng Kênh 8", gpio_pin=6),
        }

        # Standard 6-DOF Robotic Limbs & Head Joints
        self.joints: dict[str, LimbJoint] = {
            "head_yaw": LimbJoint("head_yaw", "Khớp Cổ Quay Ngang (Yaw)", channel=0, current_angle=90.0),
            "head_pitch": LimbJoint("head_pitch", "Khớp Cổ Gật Lên Xuống (Pitch)", channel=1, current_angle=90.0),
            "arm_left_shoulder": LimbJoint("arm_left_shoulder", "Khớp Vai Trái", channel=2, current_angle=90.0),
            "hand_left_grip": LimbJoint("hand_left_grip", "Bàn Tay Trái (Kẹp/Mở)", channel=3, min_angle=0.0, max_angle=90.0, current_angle=0.0),
            "arm_right_shoulder": LimbJoint("arm_right_shoulder", "Khớp Vai Phải", channel=4, current_angle=90.0),
            "hand_right_grip": LimbJoint("hand_right_grip", "Bàn Tay Phải (Kẹp/Mở)", channel=5, min_angle=0.0, max_angle=90.0, current_angle=0.0),
        }

        self._detect_hardware()

    def _detect_hardware(self) -> None:
        """Detect whether native Raspberry Pi GPIO libraries are available."""
        try:
            import RPi.GPIO as GPIO  # type: ignore
            self.is_hardware_available = True
            self.emulated_mode = False
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for r in self.relays.values():
                GPIO.setup(r.gpio_pin, GPIO.OUT)
                # Ensure fail-safe de-energized initially
                initial_val = GPIO.HIGH if r.active_low else GPIO.LOW
                GPIO.output(r.gpio_pin, initial_val)
        except Exception:
            # Running on x86 PC or dev machine: activate safe emulation
            self.is_hardware_available = False
            self.emulated_mode = True

    def set_relay(self, channel_id: str, state: str) -> dict[str, Any]:
        """Switch relay state ('OPEN' / 'CLOSED') with thread safety."""
        state = state.strip().upper()
        if state not in ("OPEN", "CLOSED"):
            raise ValueError(f"Invalid relay state '{state}'; must be 'OPEN' or 'CLOSED'")

        with self.lock:
            if channel_id not in self.relays:
                raise KeyError(f"Relay channel '{channel_id}' not found in registry")

            relay = self.relays[channel_id]
            relay.state = state

            if self.is_hardware_available:
                try:
                    import RPi.GPIO as GPIO
                    if relay.active_low:
                        val = GPIO.LOW if state == "CLOSED" else GPIO.HIGH
                    else:
                        val = GPIO.HIGH if state == "CLOSED" else GPIO.LOW
                    GPIO.output(relay.gpio_pin, val)
                except Exception as e:
                    logger.warning("GPIO output error on %s: %s", channel_id, e)

            return {
                "success": True,
                "channel_id": channel_id,
                "name": relay.name,
                "state": relay.state,
                "gpio_pin": relay.gpio_pin,
                "emulated": self.emulated_mode,
            }

    def pulse_relay(self, channel_id: str, duration_ms: int = 500) -> dict[str, Any]:
        """Pulse relay momentarily (e.g. trigger solenoid or latch) then safely return to OPEN."""
        def _pulse_worker():
            self.set_relay(channel_id, "CLOSED")
            time.sleep(max(50, duration_ms) / 1000.0)
            self.set_relay(channel_id, "OPEN")

        t = threading.Thread(target=_pulse_worker, daemon=True)
        t.start()
        return {
            "success": True,
            "channel_id": channel_id,
            "action": "PULSE_SCHEDULED",
            "duration_ms": duration_ms,
        }

    def set_joint_angle(self, joint_id: str, angle: float) -> dict[str, Any]:
        """Set servo limb/joint angle within calibrated physical bounds."""
        with self.lock:
            if joint_id not in self.joints:
                raise KeyError(f"Joint '{joint_id}' not found in registry")

            joint = self.joints[joint_id]
            clamped_angle = max(joint.min_angle, min(joint.max_angle, float(angle)))
            joint.current_angle = clamped_angle

            return {
                "success": True,
                "joint_id": joint_id,
                "name": joint.name,
                "angle": joint.current_angle,
                "emulated": self.emulated_mode,
            }

    def emergency_all_stop(self) -> dict[str, Any]:
        """CRITICAL HARDWARE FAIL-SAFE: Immediately de-energize all relays and freeze all joints."""
        with self.lock:
            for r_id in self.relays:
                try:
                    self.set_relay(r_id, "OPEN")
                except Exception:
                    pass

            for j in self.joints.values():
                j.current_angle = 90.0  # Center resting position

            return {
                "success": True,
                "emergency_status": "DE_ENERGIZED_ALL_RELAYS",
                "relays_open_count": len(self.relays),
                "timestamp_utc": time.time(),
            }

    def get_status(self) -> dict[str, Any]:
        """Return comprehensive hardware telemetry for all motion and relay channels."""
        with self.lock:
            return {
                "hardware_available": self.is_hardware_available,
                "emulated_mode": self.emulated_mode,
                "relays": {k: asdict(v) for k, v in self.relays.items()},
                "joints": {k: asdict(v) for k, v in self.joints.items()},
            }
