from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# định nghĩa dữ liệu thô lấy vào từ bảng sensordata
@dataclass(frozen=True)
class RawRecord:

    timestamp: datetime
    soil_moisture: float | None
    temperature: float | None
    humidity: float | None
    light: float | None
    drip: float | None
    fan: float | None
    mist: float | None
    row_index: int
