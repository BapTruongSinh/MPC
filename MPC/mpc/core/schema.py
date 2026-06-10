from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mpc.control.fao56 import FAO56_SOIL_PRESETS
from mpc.core.config import ControllerConfig

FieldSpec = tuple[str, str, str] | tuple[str, str, str, dict[str, Any]]

USER_INPUT_FIELDS: tuple[FieldSpec, ...] = (
    ("target_band.low", "number", "Lower soil moisture bound for the crop."),
    ("target_band.high", "number", "Upper soil moisture bound for the crop."),
    ("pump.max_seconds", "number", "Maximum pump seconds in one control step."),
    ("fao56.crop_kc", "number", "Crop coefficient used by FAO-56 ETc adjustment."),
    (
        "fao56.soil_type",
        "enum",
        "Soil preset name for FAO-56 theta defaults.",
        {"options": tuple(sorted(FAO56_SOIL_PRESETS))},
    ),
    ("fao56.root_depth_m", "number", "Effective crop root depth in meters."),
    (
        "fao56.depletion_fraction_p",
        "number",
        "Fraction of total available water that is readily available.",
    ),
    (
        "fao56.et0_hour_mm",
        "number",
        "Fallback hourly FAO ET0 in millimeters when no weather ET0 is supplied.",
    ),
    (
        "fao56.pump_efficiency",
        "number",
        "Pump efficiency multiplier for delivered irrigation depth.",
    ),
    ("fao56.pump_flow_lps", "number", "Pump flow rate in liters per second."),
    (
        "fao56.irrigation_area_m2",
        "number",
        "Irrigated surface area in square meters.",
    ),
    ("actuator.enabled", "boolean", "Allow sending commands to the HTTP actuator."),
    (
        "actuator.url",
        "string|null",
        "HTTP actuator endpoint, configured outside code.",
        {"secret": False},
    ),
    (
        "actuator.bearer_token_env",
        "string|null",
        "Environment variable name that stores the Bearer token.",
        {"secret": False},
    ),
)

SYSTEM_DEFAULT_FIELDS: tuple[FieldSpec, ...] = (
    ("step_seconds", "integer", "Control step duration in seconds."),
    ("horizon_steps", "integer", "Number of forecast steps in the horizon."),
    ("pump.min_seconds", "number", "Lower bound for pump command."),
    ("cost.band_violation", "number", "Weight for target-band error."),
    ("cost.water_use", "number", "Weight for water use."),
    ("cost.switching", "number", "Weight for changing pump command."),
    (
        "cost.terminal_band_violation",
        "number",
        "Weight for final horizon state outside the band.",
    ),
    ("fao56.theta_fc", "number", "Volumetric water content at field capacity."),
    ("fao56.theta_wp", "number", "Volumetric water content at wilting point."),
)


def controller_config_to_dict(config: ControllerConfig) -> dict[str, Any]:
    """Return a JSON-serializable controller config payload."""

    return asdict(config)


def default_config_schema() -> dict[str, Any]:
    """Return defaults and field grouping for UI/API clients."""

    return {
        "schema_version": 1,
        "controller_defaults": controller_config_to_dict(ControllerConfig()),
        "field_groups": {
            "user_inputs": [_field_from_spec(spec) for spec in USER_INPUT_FIELDS],
            "system_defaults": [
                _field_from_spec(spec) for spec in SYSTEM_DEFAULT_FIELDS
            ],
        },
    }


def _field_from_spec(spec: FieldSpec) -> dict[str, Any]:
    name, value_type, description, *rest = spec
    kwargs = rest[0] if rest else {}
    return _field(name, value_type, description, **kwargs)


def _field(
    name: str,
    value_type: str,
    description: str,
    *,
    runtime_field: bool = True,
    secret: bool = False,
    options: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    field = {
        "name": name,
        "type": value_type,
        "description": description,
        "runtime_field": runtime_field,
        "secret": secret,
    }
    if options is not None:
        field["options"] = list(options)
    return field
