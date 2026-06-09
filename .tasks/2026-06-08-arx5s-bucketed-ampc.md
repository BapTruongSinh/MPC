---
title: "ARX 5s + bucketed AMPC runtime integration"
required_skills:
  - backend
  - frontend
  - database
  - quality
status: completed
---

# ARX 5s + Bucketed AMPC Runtime Integration

## Muc tieu

Tich hop lai runtime sau khi ESP32 gui raw telemetry moi 5 giay va ARX moi duoc export tai
`ARX/ARX_DO_BY_SELF/result/arx_5s_model.json`.

Khong sua logic trong `ESP32/` va khong sua code/artifact trong `ARX/`. Runtime Green-House,
Kalman va MPC phai doc duoc format ARX moi, luu dung telemetry ESP32 vao DB, va AMPC phai gom
raw `SensorData` thanh mau dai dien theo `step_seconds` truoc khi chay du bao.

## Checklist

- [x] Doc rule `.claude`, ESP32 telemetry payload va ARX 5s artifact/code.
- [x] Cap nhat ARX loader trong Kalman va MPC de doc format artifact moi: `spec`, `theta`,
      `scale`, `clip_scaled`, derived features va z-score/inverse scale.
- [x] Cap nhat backend ingest de luu day du snapshot telemetry ESP32 can thiet cho bucket
      `Drip/Mist/Fan` ma khong sua ESP32.
- [x] Them co che bucket tam thoi tu `SensorData` raw trong DB theo `step_seconds`; tao
      `EstimationCycle` dai dien, khong tao bang bucket moi.
- [x] Cap nhat AMPC scheduler/runtime de moi vong dung config hien tai, tao cac bucket gan nhat
      theo `step_seconds * horizon_steps`, va chay recommendation tren mau dai dien.
- [x] Dong bo FE/BE auto settings cho `step_seconds` va `horizon_steps`.
- [x] Cap nhat test cho ARX artifact moi, bucket aggregation, auto-settings contract.
- [x] Chay verification: Kalman tests, MPC tests, Django api tests/check, FE smoke/build neu kha thi.

## Expected Behavior

- Default `step_seconds=300`, `horizon_steps=12` nghia la du bao 60 phut, moi buoc 5 phut.
- Neu `step_seconds=120`, `horizon_steps=10`, AMPC se lay 20 phut du lieu raw gan nhat,
  chia thanh 10 cua so 2 phut, tinh average cho moi cua so, tao/cap nhat `EstimationCycle`
  dai dien, roi MPC du bao 10 buoc tuong lai.
- `SensorData` van luu raw 5 giay/lần trong DB; khong tao bang bucket moi.
- ARX runtime chi doc artifact `.json` da train, khong train lai.

## Quality Gates

- Logic: khong tron raw 5s voi control step neu chua average.
- Nghiep vu: user doi `step_seconds/horizon_steps` tren FE thi BE luu vao profile va AMPC
  doi bucket/horizon tuong ung.
- Security: payload ESP32 va config user van validate finite/bounds.
- Test thuc te: cac test Python/FE phu hop phai pass truoc khi bao cao hoan thanh.
