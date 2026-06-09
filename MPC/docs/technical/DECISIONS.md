# MPC Decisions

## ADR-001: Root-Level Python Package

MPC lives under root `MPC/` as a Python package imported by Green-House backend.
The old standalone terminal runner was removed to keep one runtime path.

## ADR-002: No ARX/RLS Inside MPC

MPC does not load ARX artifacts, train ARX, or update ARX coefficients. Kalman
may use its own ARX prediction adapter before Green-House builds
`ControllerState`, but the MPC package is a plain FAO-56 controller.

## ADR-003: FAO-56 Control State

The solver controls physical depletion terms:

- `TAW`
- `RAW`
- `Dr`

Sensor percent is calibrated from user target band:

- `target_high -> Dr = 0`
- `target_low -> Dr = RAW`

Dashboard predictions remain sensor percent.

## ADR-004: Scipy Optimizer

The solver uses `scipy.optimize.minimize` over the future pump sequence and
returns only the first command by receding horizon.

## ADR-005: Removed ARX/RLS Package Modules

`mpc.plant` and `mpc.adaptive` were removed to keep one active MPC model path.
Runtime prediction is the FAO-56 water-balance rollout in the solver objective.

## ADR-006: FAO Water-Balance MPC Objective

The MPC objective rolls the future state with FAO-56 depletion balance:

```text
ETc_step = Ks * Kc * ET0_hour * step_seconds / 3600
I(u_k) = eta * Q / A * u_k
Dr_next = clamp(Dr_current + ETc_step - I(u_k), 0, TAW)
```

The optimizer still chooses a future pump sequence and executes only the first
command by receding horizon:

```text
u = [u0, u1, ..., uN-1]
```

`predicted_soil_moisture` is produced by converting the rolled-out `Dr` trace
back to calibrated sensor percent for the dashboard.
