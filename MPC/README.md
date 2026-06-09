# MPC

Standalone MPC/AMPC controller package for the Green-House backend.

## Overview

`MPC/` exposes Python modules that the Django backend imports directly. It does
not provide a command-line runtime anymore.

Runtime flow:

```text
Green-House backend
  -> mpc.core.ControllerState
  -> mpc.solver.ScipyMpcSolver(...).recommend(...)
  -> recommendation / optional actuator command
```

## Tech Stack

| Layer | Technology | Notes |
| --- | --- | --- |
| Controller core | Python package | Imported by backend/tests |
| State source | Kalman posterior / raw sensor fallback | `kf_R > 15` falls back to raw sensor |
| Solver | `scipy.optimize.minimize` | Optimizes future pump sequence and executes the first command |
| Plant model | FAO-56 water balance | Rolls out `Dr_next = Dr + ETc_step - I(u_k)` |
| Tests | pytest | Unit and safety tests |

## Project Structure

```text
MPC/
  mpc/
    actuator/
    control/
    core/
    solver/
  tests/
  docs/
```

## Usage

Use the package from Python:

```python
from mpc.core.config import ControllerConfig
from mpc.core.state import ControllerState
from mpc.solver import ScipyMpcSolver

config = ControllerConfig()
state = ControllerState.from_mapping({...})
recommendation = ScipyMpcSolver(config).recommend(
    state=state,
)
```

For the full app, run the Django backend in `Green-House/backend`; the backend
loads this package directly.

## Tests

```powershell
python -m pytest MPC/tests -q
python -m compileall -q MPC/mpc
```
