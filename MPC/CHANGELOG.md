# Changelog

## [Unreleased]

### Added

- Plain FAO-56 MPC runtime with scipy pump-sequence optimization.
- Scipy optimizer solves the future pump sequence while keeping the public solver API compatible.
- MPC is used as a Python package imported by the backend.
- V3 HTTP actuator pilot with `ActuatorCommand`, Bearer auth from env, and fake HTTP actuator tests.
- Config schema export for website-facing defaults/field groups.

### Fixed

- Removed the previous ARX/RLS MPC package path and kept one active FAO-56 water-balance objective.
- Replaced grid/beam solver internals with `scipy.optimize.minimize`.
- Objective cost normalize water/switching báº±ng `pump.max_seconds` vÃ  daily cap báº±ng `soft_daily_pump_cap_seconds`, Ä‘Ãºng theo biÃªn Ä‘iá»u khiá»ƒn bÆ¡m.
- Recommendation output uses the public contract top-level instead of a nested envelope.
- `run_closed_loop()` validate actuator config trÆ°á»›c khi dÃ¹ng injected actuator client, nÃªn fake/test client khÃ´ng bypass Ä‘Æ°á»£c guard explicit config.
