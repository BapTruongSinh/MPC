"""Public output contracts for MPC recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
"""Chứa dữ liệu đầu ra MPC
safe:MPC chạy ổn, kết quả hợp lệ.
pump_off_failsafe:hệ rơi vào chế độ an toàn, bơm 0 giây.
config_error:config sai, ví dụ low/high không hợp lệ.
stale_sample:dữ liệu sensor/Kalman quá cũ.
model_error:lỗi mô hình FAO/MPC khi tính toán.
solver_error:lỗi scipy solver, không tìm được nghiệm.
actuator_error:lỗi khi gửi lệnh xuống thiết bị."""
SafetyStatus = Literal[
    "safe",
    "pump_off_failsafe",
    "config_error",
    "stale_sample",
    "model_error",
    "solver_error",
    "actuator_error",
]


@dataclass(frozen=True)
class Recommendation:
    pump_seconds: float
    step_seconds: int
    predicted_soil_moisture: tuple[float, ...]
    target_band: dict[str, float]
    cost: float
    safety_status: SafetyStatus
    reason: str
    fao56: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "pump_seconds": self.pump_seconds,
            "step_seconds": self.step_seconds,
            "predicted_soil_moisture": list(self.predicted_soil_moisture),
            "target_band": dict(self.target_band),
            "cost": self.cost,
            "safety_status": self.safety_status,
            "reason": self.reason,
        }
        if self.fao56 is not None:
            payload["fao56"] = dict(self.fao56)
        return payload
