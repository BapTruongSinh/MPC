---
id: "013"
title: "Align AMPC with report RLS adaptation and scipy optimizer"
status: "completed"
area: "backend"
agent: "@builder"
priority: "high"
created_at: "2026-06-08"
due_date: null
started_at: "2026-06-08"
completed_at: "2026-06-08"
prd_refs: []
blocks: []
blocked_by:
  - "Kalman-001"
required_skills:
  - planning
  - backend
  - quality
  - docs
---

## Description

Sua `MPC/` de khop bao cao:

1. AMPC khong con dung moving-average bias correction lam co che thich nghi chinh. Thay vao do cap nhat he so ARX bang Recursive Least Squares (RLS):

```text
e_k = y_k - phi_k^T theta_{k-1}
K_k = P_{k-1} phi_k / (lambda + phi_k^T P_{k-1} phi_k)
theta_k = theta_{k-1} + K_k e_k
P_k = (1/lambda) * (P_{k-1} - K_k phi_k^T P_{k-1})
```

2. Solver MPC khong con dung grid shooting lam solver chinh. Thay bang `scipy.optimize.minimize`, trong do chuoi lenh bom tuong lai la bien toi uu:

```text
u = [u0, u1, ..., uN-1]
0 <= u_k <= max_pump_seconds
```

3. Giu nguyen cach xay dung cau truc mo hinh/luong hien co: ARX van co `ARXPlantModel`, MPC van predict horizon -> tinh cost -> chon chuoi dieu khien -> chi thuc thi `u0`. Thu vien chi ho tro phep tinh ben trong, khong bien model thanh black-box.

## Acceptance Criteria

- [x] Loai bo runtime dependency vao `BiasCorrectedPlantModel` trong AMPC path; RLS la co che adaptive chinh.
- [x] Them module RLS cap nhat `theta` ARX tu residual va regression row `phi` ma `ARXPlantModel` dang dung.
- [x] `ARXPlantModel` giu cau truc hien co, co API an toan de lay prediction row va tao model voi theta da cap nhat.
- [x] Backend `Green-House/backend/api/ampc.py` dung RLS state tu cac `EstimationCycle` gan nhat khi `adaptive_enabled=True`.
- [x] Solver recommendation dung `scipy.optimize.minimize` de toi uu chuoi `pump_seconds`, khong con enumerate grid la co che chinh.
- [x] Bounds pump duoc ap dung bang scipy bounds va ket qua `u0` duoc clamp/validate.
- [x] Cost van ton trong FAO-56 Dr/RAW/TAW calibration hien tai, khong quay lai so sanh truc tiep sensor percent voi low/high.
- [x] Them `numpy`/`scipy` vao dependency package can thiet; khong them pandas/sklearn.
- [x] Unit tests bao phu RLS theta update, scipy solver dry/wet behavior, pump bounds, va compatibility public imports.
- [x] Backend integration check pass voi `Green-House`.
- [x] Logic gate pass: RLS va scipy solver doi chieu duoc voi cong thuc bao cao/MPC receding horizon.
- [x] Nghiep vu gate pass: duoi nguong kho AMPC co kha nang de xuat bom, an toan thi pump 0.
- [x] Security gate pass: khong them URL/token/secret, khong persist du lieu vuot field length, fail-closed khi solver loi.
- [x] Test chay thuc te pass: `python -m pytest MPC\tests -q`, `python -m compileall -q MPC\mpc`, va `cd Green-House\backend; python manage.py check`.

## Technical Notes

- Bao cao dong 702-706 yeu cau Adaptive MPC cap nhat tham so ARX bang RLS.
- Bao cao dong 695-701 mo ta MPC tinh chuoi dieu khien tuong lai va chi thuc thi lenh dau tien theo receding horizon.
- Runtime uses `ScipyMpcSolver`; removed old grid/terminal runner compatibility.
- Khong them `sklearn` vi runtime doc nay khong train model hoc may; RLS va solver can `numpy` + `scipy`.

## History

| Date | Agent / Human | Event |
|------|--------------|-------|
| 2026-06-08 | human | Chon A: thay han bias AMPC bang RLS va thay han grid solver bang scipy.optimize. |
| 2026-06-08 | Codex | Task created and started. |
| 2026-06-08 | Codex | Implemented RLS adaptation, scipy solver, backend integration, docs, and verified MPC/Kalman/backend/frontend gates. Backend `manage.py test api` remains blocked by stale tests importing removed `Greenhouse`/`Device` models. |
