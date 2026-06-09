# MPC Validation

Run from repo root:

```powershell
python -m pytest MPC\tests -q
python -m compileall -q MPC\mpc
```

For backend integration:

```powershell
cd Green-House\backend
.\.venv\Scripts\python.exe manage.py test api -v 1 --noinput
```

Validation focus:

- FAO-56 target-band calibration maps sensor low/high to `RAW/Dr`.
- Scipy solver recommends pump when `Dr > RAW`.
- Fail-closed behavior returns `pump_seconds=0` on stale/config/model errors.
- Backend imports package modules directly.
