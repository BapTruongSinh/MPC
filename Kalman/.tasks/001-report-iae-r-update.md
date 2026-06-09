---
id: "001"
title: "Align Adaptive Kalman R update with report IAE formula"
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
blocked_by: []
required_skills:
  - planning
  - backend
  - quality
---

## Description

Sua Adaptive Kalman trong `Kalman/kalman/filter/cycle.py` de cong thuc cap nhat nhieu do luong `R_k` dung voi bao cao PBL:

```text
innovation = z_k - H_k x_hat(k|k-1)
R_candidate = innovation^2 - H_k P(k|k-1) H_k^T
R_k = (1 - d_k) R_{k-1} + d_k * R_candidate
d_k = (1 - b) / (1 - b^(k+1)), 0 < b < 1
```

Voi he hien tai la 1D va `H = 1`, cong thuc runtime la:

```text
R_candidate = innovation^2 - P_prior
R_k = clip((1 - d_k) * R_{k-1} + d_k * R_candidate, R_min, R_max)
```

Giu nguyen cau truc `AdaptiveKalmanCycle.step()`, `KalmanConfig`, `KalmanState`, `CycleResult`; chi thay cong thuc tinh ben trong. Dung `numpy` cho phep tinh vo huong/vector neu can, khong them pandas/sklearn.

## Acceptance Criteria

- [x] `R_k` duoc cap nhat bang cong thuc IAE trong bao cao, co tru `P_prior` voi he 1D `H=1`.
- [x] He so thich nghi `d_k = (1 - b) / (1 - b^(k+1))` duoc tinh ro rang tu tham so quen, khong dung EMA `alpha` cu lam cong thuc chinh.
- [x] `R_k` van duoc gioi han trong `[R_min, R_max]` de tranh am/khong on dinh.
- [x] Predict/update Kalman co ban van giu dung: `P_prior = P_post + Q`, `K = P_prior / (P_prior + R)`, `x_post = x_prior + K * innovation`, `P_post = (1 - K) * P_prior`.
- [x] Unit test bao phu case `R_candidate = innovation^2 - P_prior`, clamp min/max, va missing measurement giu `R` nguyen.
- [x] Logic gate pass: cong thuc code doi chieu duoc voi bao cao.
- [x] Nghiep vu gate pass: output Kalman van la tin hieu lam muot cho AMPC, khong doi API Django/backend.
- [x] Security gate pass: khong them input khong validate, khong hardcode secret/path.
- [x] Test chay thuc te pass: `python -m pytest Kalman\tests -q` va `python -m compileall -q Kalman\kalman`.

## Technical Notes

- Bao cao dong 670-690 mo ta IAE uoc luong `R_k`.
- Code hien tai dang dung `R = alpha * R_prev + (1 - alpha) * innovation^2`; day la gan dung innovation EMA nhung chua dung IAE vi thieu thanh phan `H P H^T`.
- Co the giu field `alpha` de backward-compatible, nhung nghia moi nen la forgetting factor `b` hoac them alias ro rang trong docstring/test.
- Khong doi schema DB va khong doi response API.

## History

| Date | Agent / Human | Event |
|------|--------------|-------|
| 2026-06-08 | human | Yeu cau sua Kalman dung IAE theo bao cao. |
| 2026-06-08 | Codex | Task created and started. |
| 2026-06-08 | Codex | Implemented IAE R update and verified `python -m pytest Kalman\tests -q` plus `python -m compileall -q Kalman\kalman`. |
