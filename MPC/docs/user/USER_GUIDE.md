# MPC User Guide

`MPC/` is a Python package used by the Green-House backend. There is no
standalone terminal runner.

## Run Through Backend

Start the backend from `Green-House/backend`:

```powershell
python manage.py runserver
```

The backend calls MPC directly:

```text
api/ampc.py
  -> ControllerState.from_mapping(...)
  -> ScipyMpcSolver(config).recommend(...)
```

## Direct Python Usage

For unit tests or debugging, import the package directly:

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

## Validation

Run from repo root:

```powershell
python -m pytest MPC\tests -q
python -m compileall -q MPC\mpc
```
