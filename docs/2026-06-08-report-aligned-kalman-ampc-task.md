# Report-Aligned Kalman And AMPC Task

Umbrella note for the 2026-06-08 implementation request.

Tracked source-of-truth tasks:

- `Kalman/.tasks/001-report-iae-r-update.md`
- `MPC/.tasks/013-report-rls-scipy-ampc-solver.md`

Scope:

- Kalman `R_k` must follow the report IAE formula.
- AMPC must update ARX parameters with RLS instead of moving-average bias correction.
- MPC must optimize the future pump sequence with `scipy.optimize`, while preserving the current model/control structure.
- Dependencies may use `numpy` and `scipy`; do not add `pandas` or `sklearn`.

Status on 2026-06-08:

- Kalman task: completed.
- MPC task: completed for RLS/scipy runtime scope.
- Verified: `python -m pytest Kalman\tests -q`, `python -m pytest MPC\tests -q`, compileall for Kalman/MPC/backend, `manage.py check`, backend requirements install, and frontend build.
- Known backend test blocker: `manage.py test api` imports stale multi-greenhouse tests that reference removed `Greenhouse`/`Device` models and old `run_auto_recommendation(user, greenhouse_id)` signature.
