from __future__ import annotations

from dataclasses import dataclass

from .loader import RawRecord
from .validator import ValidationResult

_FIELDS = ("soil_moisture", "temperature", "humidity", "light", "drip", "mist", "fan")


@dataclass(frozen=True)
class ProcessedRecord:

    raw: RawRecord
    validation: ValidationResult
    preprocess_status: str

    soil_moisture: float | None
    temperature: float | None
    humidity: float | None
    light: float | None
    drip: float | None
    mist: float | None
    fan: float | None


def _make_processed(
    record: RawRecord,
    validation: ValidationResult,
    status: str,
    effective: dict[str, float | None],
) -> ProcessedRecord:
    return ProcessedRecord(
        raw=record,
        validation=validation,
        preprocess_status=status,
        soil_moisture=effective.get("soil_moisture"),
        temperature=effective.get("temperature"),
        humidity=effective.get("humidity"),
        light=effective.get("light"),
        drip=effective.get("drip"),
        mist=effective.get("mist"),
        fan=effective.get("fan"),
    )


def preprocess_single(
    record: RawRecord,
    validation: ValidationResult,
) -> ProcessedRecord:
    if validation.is_valid:
        effective = {field: getattr(record, field) for field in _FIELDS}
        return _make_processed(record, validation, "valid", effective)
    return _make_processed(
        record,
        validation,
        "skipped",
        {field: None for field in _FIELDS},
    )
