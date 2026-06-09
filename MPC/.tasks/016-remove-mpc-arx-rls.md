---
title: "Remove MPC-side ARX/RLS and keep plain FAO MPC"
required_skills:
  - backend
  - frontend
  - quality
status: completed
---

# #016 - Remove MPC-Side ARX/RLS And Keep Plain FAO MPC

## Goal

Don dua `MPC/` ve MPC thuong, chi dung FAO-56 water balance va
`scipy.optimize.minimize` de toi uu chuoi lenh bom:

```text
ETc_step = Ks * Kc * ET0_hour * step_seconds / 3600
I(u_k) = irrigation_depth_mm = eta * Q / A * u_k
Dr_next = clamp(Dr_current + ETc_step - I(u_k), 0, TAW)
```

MPC khong con so huu model ARX, khong load ARX artifact, va khong cap nhat RLS.
Kalman van co the dung ARX rieng cua Kalman truoc khi backend tao
`ControllerState`.

## Checklist

- [x] Xoa `mpc.plant` va `mpc.adaptive` khoi source package.
- [x] Xoa `PlantRecord`, `DisturbanceForecast`, `to_plant_record`, va `to_duty`
  la cac contract phuc vu ARX history cu.
- [x] Xoa tests ARX/RLS thuoc MPC.
- [x] Xoa `AdaptiveConfig` va schema adaptive khoi `ControllerConfig`.
- [x] Xoa package metadata `mpc.plant`/`mpc.adaptive` trong `pyproject.toml`.
- [x] Xoa backend fields/API `adaptive_*` va `rls_*` cua MPC recommendation.
- [x] Them migration backend de drop cac cot legacy adaptive/RLS.
- [x] Xoa frontend types/UI/smoke-test fields adaptive/RLS.
- [x] Cap nhat docs current-state sang plain FAO MPC.

## Boundaries

- Khong sua `ARX/`.
- Khong sua `ESP32/`.
- Khong doc/sua `Server/`.
- Khong xoa Kalman ARX adapter vi no thuoc Kalman prediction path, khong thuoc
  MPC package.

## Verification

- [x] `python -m compileall -q MPC\mpc Green-House\backend\api`
- [x] `python -m pytest MPC\tests -q`
- [x] `python -m pytest Kalman\tests MPC\tests -q`
- [x] `cd Green-House\backend; .\.venv\Scripts\python.exe manage.py test api -v 1 --noinput`
- [x] `cd Green-House\backend; .\.venv\Scripts\python.exe manage.py check`
- [x] `cd Green-House\backend; .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- [x] `cd Green-House\frontend; npm test -- --runInBand`
- [x] `cd Green-House\frontend; npm run build`

## Notes

- Cac migration cu van co the chua ten cot `adaptive_*`/`rls_*` vi do la lich
  su schema. Runtime models/serializers/API hien tai khong con expose cac field
  nay.
- Cac task cu #002/#013/#014 duoc giu nhu lich su, nhung trang thai hien tai
  duoc xac dinh boi task #015 va #016.
