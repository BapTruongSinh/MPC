# MPC Architecture

`MPC/` is a Python package imported by the Green-House backend.

## Runtime Flow

```text
Kalman posterior/raw sensor
  -> ControllerState
  -> ScipyMpcSolver.recommend(...)
  -> Recommendation
  -> optional run_closed_loop actuator wrapper
```

## Package Layout

```text
MPC/
  mpc/
    actuator/
      base.py
      http.py
    control/
      closed_loop.py
      fao56.py
    core/
      config.py
      schema.py
      state.py
      types.py
    solver/
      cost.py
      scipy_solver.py
  tests/
```

## Boundaries

- `mpc.core`: config, state, schema, output contracts.
- `mpc.control.fao56`: FAO-56 formulas and sensor target-band calibration.
- `mpc.solver.cost`: FAO rollout and objective.
- `mpc.solver.scipy_solver`: optimizer and fail-closed recommendation wrapper.
- `mpc.control.closed_loop`: optional actuator command orchestration.
- `mpc.actuator`: HTTP actuator adapter and output contracts.

## Design Rules

- Backend calls Python modules directly; no subprocess boundary.
- Solver optimizes in FAO depletion units `Dr/RAW/TAW`.
- Dashboard-facing predictions remain sensor percent.
- Unsafe input, stale samples, model errors, solver errors, and actuator errors
  fail closed with pump off.
