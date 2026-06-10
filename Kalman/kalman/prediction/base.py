from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from ..ingestion import ProcessedRecord


@dataclass
class PredictionInput:
    history: list[ProcessedRecord] = field(default_factory=list)


@dataclass(frozen=True)
class PredictionResult:
    """Kết quả của một lần dự đoán trước 1 bước.
    value: Giá trị Soil_Moisture dự đoán cho bước kế tiếp; None nếu không có.
    status:
        ok: dự đoán thành công.
        unavailable: model chưa train hoặc thiếu history.
        error: tính toán lỗi; chi tiết nằm trong ``reason``.
    model_kind: Được dự đoán từ model nào.
    reason: Giải thích lý do dự đoán k thành công.
    """

    value: float | None
    status: str
    model_kind: str
    reason: str = ""


class PredictionAdapter(ABC):
    """Abstract base cho mọi model dự đoán trong pipeline ước lượng.

    model_kind        — định danh chữ thường, ví dụ arx
    is_trained        — True khi model đã fit và sẵn sàng dự đoán
    min_history_len   — số record trước đó tối thiểu mà predict() cần
    predict()         — dự đoán trước 1 bước
    load_artifact()   — classmethod; khôi phục adapter đã lưu
    """

    @property
    @abstractmethod
    def model_kind(self) -> str:
        """"""
        # định danh chữ thường, ví dụ "arx"

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """"""
        # True khi model đã fit và sẵn sàng dự đoán, False nếu cần thêm data để train hoặc chưa train

    @property
    @abstractmethod
    def min_history_len(self) -> int:
        """"""
        # số record trước đó tối thiểu mà predict() cần; thường là bậc của model

    @abstractmethod
    def predict(self, inp: PredictionInput) -> PredictionResult:
        """Trả về dự đoán trước 1 bước từ history gần nhất.

        Không được ném lỗi ra. Nếu có lỗi, trả status="error" hoặc
        status="unavailable" để chu kỳ Kalman có thể chạy tiếp mà không
        cần dự đoán.
        """

    @classmethod
    @abstractmethod
    def load_artifact(cls, path: Path) -> "PredictionAdapter":
        """Khôi phục adapter đã lưu từ path.
        """
