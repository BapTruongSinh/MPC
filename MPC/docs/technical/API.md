# MPC Interface Contracts

MPC exposes Python package contracts for backend integration and tests.

## Recommendation Input

`ControllerState` accepts:

```json
{
  "run_id": 1,
  "timestamp": "2026-05-08T10:00:00Z",
  "kf_x_posterior": 58.2,
  "kf_R": 1.4,
  "raw_soil_moisture": 58.5,
  "temperature": 27.0,
  "humidity": 74.0,
  "light": 300.0,
  "last_pump_seconds": 0.0
}
```

Rules:

- Prefer `kf_x_posterior` while Kalman is trusted.
- If `kf_R > 15` and raw sensor exists, use `raw_soil_moisture`.
- If both posterior and raw are missing, fail closed.
- Stale or future samples fail closed.

## Recommendation Output

`Recommendation.to_dict()` returns:

```json
{
  "pump_seconds": 60.0,
  "step_seconds": 300,
  "predicted_soil_moisture": [58.2, 58.4, 58.8],
  "target_band": {"low": 55.0, "high": 65.0},
  "cost": 12.34,
  "safety_status": "safe",
  "reason": "above_raw_stress",
  "fao56": {
    "initial_dr": 30.0,
    "taw": 51.0,
    "raw": 25.5,
    "ks": 0.82,
    "et0_step": 0.05,
    "etc_adj": 0.04,
    "irrigation_depth_mm": 4.8,
    "predicted_dr": [25.0, 20.0, 18.0],
    "sensor_calibration_mode": "target_band_to_raw"
  }
}
```

Allowed `safety_status` values:

- `safe`
- `pump_off_failsafe`
- `config_error`
- `stale_sample`
- `model_error`
- `solver_error`
- `actuator_error`

## Config

`ControllerConfig` is the runtime source of truth. `default_config_schema()`
exports controller defaults and UI field groups for clients that need to render
settings forms.

The backend maps database profile fields into `ControllerConfig`.

## Solver

The solver uses `scipy.optimize.minimize` over a future pump sequence:

```text
u = [u0, u1, ..., uN-1]
```

Each `u_k` is bounded by `pump.min_seconds <= u_k <= pump.max_seconds`. The
solver returns only `u0` by receding horizon.

The runtime objective is FAO-56 water-balance control:

```text
sensor soil_moisture %
-> FAO target-band calibration maps current % to Dr/RAW/TAW
-> scipy tries future pump seconds u_k
-> FAO rolls out Dr_next = Dr + ETc_step - I(u_k)
-> cost is computed from physical stress, wetness, water, switching, and caps
```

Per step:

```text
ETc_step = Ks * Kc * ET0_hour * step_seconds / 3600
I(u_k) = irrigation_depth_mm = eta * Q / A * u_k
Dr_next = clamp(Dr_current + ETc_step - I(u_k), 0, TAW)
sensor_hat_k = calibrated_sensor_percent_from_depletion_mm(Dr_next)
```

Cost terms:

```text
stress_error = max(0, Dr_next - RAW)
overwater_error = max(0, Dr_raw_next * -1)
water_term = (u_k / pump_max_seconds)^2
switch_term = ((u_k - u_k-1) / pump_max_seconds)^2
```

Cost grouping:

```text
J_tracking = stress_total + overwater_total + terminal_total
J_control = switching_total
J_resource = water_total + daily_cap_total
J = J_tracking + J_control + J_resource
```

`predicted_soil_moisture` is the FAO rollout converted back to sensor percent
for dashboard display. `fao56.predicted_dr` is the physical depletion trace.

## Closed Loop

`run_closed_loop()` combines solver output with actuator safety:

- unsafe recommendation -> pump command is forced to `0s`
- actuator disabled/misconfigured -> no HTTP command is sent
- HTTP actuator failure -> fail-closed actuator result
- bearer token value is read from env and never returned in output
