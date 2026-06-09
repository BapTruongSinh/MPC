# MPC Database Notes


## Future Integration

Náº¿u sau nÃ y tÃ­ch há»£p vá»›i `Kalman/`, nguá»“n dá»¯ liá»‡u chÃ­nh sáº½ lÃ :

- `PipelineCycle.kf_x_posterior` lÃ m state chÃ­nh.
- `PipelineCycle.raw_soil_moisture` lÃ m fallback.
- `PipelineCycle.temperature`, `humidity`, `light` lÃ m measured disturbance.
- `ExperimentRun` lÃ m run identity.

KhÃ´ng thÃªm báº£ng má»›i cho MPC trong scaffold nÃ y. Náº¿u cáº§n lÆ°u recommendation/history, táº¡o task database riÃªng vÃ  cáº­p nháº­t ADR trÆ°á»›c.

