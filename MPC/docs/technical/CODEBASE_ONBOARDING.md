# MPC Codebase Onboarding

`MPC/` is the controller package used by Green-House backend.

## Important Modules

- `mpc.core.config`: validated controller config.
- `mpc.core.state`: latest controller state and Kalman raw fallback.
- `mpc.control.fao56`: FAO-56 water balance and sensor calibration.
- `mpc.solver.cost`: FAO rollout and cost.
- `mpc.solver.scipy_solver`: recommendation optimizer.

## Runtime Integration

Green-House calls:

```python
ScipyMpcSolver(config).recommend(...)
```

MPC does not load or train ARX models. Kalman can still use its own ARX
prediction adapter before Green-House builds `ControllerState`, but the MPC
package itself is plain FAO water-balance MPC.

## Checks

```powershell
python -m pytest MPC\tests -q
python -m compileall -q MPC\mpc
```
