"""Validated in-memory Kalman run configuration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from ..filter import KalmanConfig


class ConfigFrozenError(RuntimeError):
    """Raised by persistence services when a started run is edited."""


@dataclass(frozen=True)
class RunConfig:
    name: str = "unnamed_run"
    dataset_source: str = ""
    x0: float = 0.0
    P0: float = 1.0
    Q: float = 0.05
    R0: float = 1.0
    R_min: float = 0.05
    R_max: float = 15.0
    forgetting_factor_b: float = 0.95

    def __post_init__(self) -> None:
        self.to_kalman_config()

    def to_kalman_config(self) -> KalmanConfig:
        return KalmanConfig(
            x0=self.x0,
            P0=self.P0,
            Q=self.Q,
            R0=self.R0,
            R_min=self.R_min,
            R_max=self.R_max,
            forgetting_factor_b=self.forgetting_factor_b,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "RunConfig":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON for RunConfig: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("RunConfig JSON must be an object")
        try:
            return cls(**payload)
        except TypeError as exc:
            raise ValueError(f"RunConfig JSON has unexpected fields: {exc}") from exc

    @classmethod
    def from_experiment_config(cls, db_row: object) -> "RunConfig":
        run = getattr(db_row, "run", None)
        name = getattr(run, "name", "unnamed_run") if run is not None else "unnamed_run"
        dataset_source = (
            getattr(run, "dataset_source", "") or ""
            if run is not None
            else ""
        )
        return cls(
            name=name,
            dataset_source=dataset_source,
            x0=db_row.x0,  # type: ignore[union-attr]
            P0=db_row.P0,  # type: ignore[union-attr]
            Q=db_row.Q,  # type: ignore[union-attr]
            R0=db_row.R0,  # type: ignore[union-attr]
            R_min=db_row.R_min,  # type: ignore[union-attr]
            R_max=db_row.R_max,  # type: ignore[union-attr]
            forgetting_factor_b=db_row.forgetting_factor_b,  # type: ignore[union-attr]
        )
