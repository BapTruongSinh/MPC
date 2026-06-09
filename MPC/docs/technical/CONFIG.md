# MPC Config

`ControllerConfig` is the runtime config used by the solver and backend
integration.

## Main Defaults

```json
{
  "step_seconds": 300,
  "horizon_steps": 12,
  "target_band": {"low": 55.0, "high": 65.0},
  "pump": {"min_seconds": 0.0, "max_seconds": 300.0},
  "cost": {
    "band_violation": 10.0,
    "terminal_band_violation": 20.0,
    "water_use": 0.2,
    "switching": 0.5
  },
  "safety": {
    "state_min": 0.0,
    "state_max": 100.0,
    "stale_after_seconds": 600,
    "fail_closed_pump_seconds": 0.0
  }
}
```

## FAO-56 Defaults

```json
{
  "crop_kc": 1.0,
  "soil_type": "loam",
  "theta_fc": 0.32,
  "theta_wp": 0.15,
  "root_depth_m": 0.3,
  "depletion_fraction_p": 0.5,
  "et0_hour_mm": 0.6,
  "pump_efficiency": 0.8,
  "pump_flow_lps": 0.001,
  "irrigation_area_m2": 0.25
}
```

`et0_hour_mm` is a fallback value. Green-House can override it from weather ET0.

## Validation

- `0 <= target_band.low < target_band.high <= 100`
- `pump.min_seconds >= 0`
- `pump.max_seconds > pump.min_seconds`
- `step_seconds > 0`
- `horizon_steps >= 1`
- `fail_closed_pump_seconds == 0`
- `0 < depletion_fraction_p < 1`
- `0 <= theta_wp < theta_fc <= 0.8`

## Backend Mapping

Green-House stores user settings in database profiles, then builds
`ControllerConfig` before calling MPC. MPC itself does not own database models.

## Schema Export

`default_config_schema()` returns controller defaults and field groups for UI/API
clients that need to render settings forms.
