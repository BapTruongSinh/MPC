---
title: "Restore FAO water-balance MPC solver"
required_skills:
  - backend
  - frontend
  - quality
status: completed
---

# #015 - Restore FAO Water-Balance MPC Solver

## Goal

Rollback the MPC objective away from ARX forecast and use the FAO-56 water
balance directly:

```text
ETc_step = Ks * Kc * ET0_hour * step_seconds / 3600
I(u_k) = irrigation_depth_mm = eta * Q / A * u_k
Dr_next = clamp(Dr_current + ETc_step - I(u_k), 0, TAW)
```

`scipy.optimize` still optimizes the future pump sequence, but every candidate
sequence is evaluated by rolling out `Dr` with FAO. `predicted_soil_moisture`
is the rolled-out `Dr` converted back to calibrated sensor percent for the
dashboard.

## Checklist

- [x] Replace hybrid ARX+FAO scoring with `score_fao56_trajectory`.
- [x] Remove `plant_model.forecast()` from `ScipyMpcSolver`.
- [x] Remove AMPC runtime loading/adapting `ARXPlantModel`.
- [x] Remove closed-loop API dependency on `history` and `plant_model`.
- [x] Keep FAO physical config/audit fields required by `ETc_step` and `I(u_k)`.
- [x] Update frontend forecast card that previously showed RLS AMPC.
- [x] Update backend/MPC/frontend tests for FAO water-balance runtime.

## ARX Status

`MPC/mpc/plant` and `MPC/mpc/adaptive` were removed after this rollback. ARX
remains a Kalman-side prediction concern only; the MPC package does not load
ARX artifacts or run RLS updates.

## Verification

- [x] `python -m pytest MPC\tests\test_scipy_solver.py MPC\tests\test_actuator_closed_loop.py MPC\tests\test_fao56.py -q`
- [x] `python -m compileall -q MPC\mpc Green-House\backend\api`
- [x] `cd Green-House\backend; .\.venv\Scripts\python.exe manage.py test api -v 1 --noinput`
- [x] `cd Green-House\backend; .\.venv\Scripts\python.exe manage.py check`
- [x] `cd Green-House\backend; .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- [x] `python -m pytest MPC\tests -q`
- [x] `python -m pytest Kalman\tests MPC\tests -q`
- [x] `cd Green-House\frontend; npm test -- --runInBand`
- [x] `cd Green-House\frontend; npm run build`
