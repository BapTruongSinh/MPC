---
title: "Superseded hybrid ARX forecast + FAO physical MPC objective"
required_skills:
  - backend
  - quality
  - planning
status: superseded
superseded_by: "015-restore-fao-water-balance-solver"
---

# #014 - Superseded Hybrid ARX Forecast + FAO Physical MPC Objective

This task was completed during exploration, then intentionally rolled back.

The hybrid direction was:

```text
pump sequence
-> ARX plant forecast predicts sensor soil_moisture %
-> FAO maps forecast % to Dr/RAW/TAW
-> cost chooses pump sequence
```

It was superseded because the project owner chose the explicit FAO-56 water
balance as the runtime MPC model:

```text
Dr_next = Dr_current + ETc_step - I(u_k)
```

The current implementation is tracked by task #015.
