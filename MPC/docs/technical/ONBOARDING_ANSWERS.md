# MPC Onboarding Answers

| Question | Answer |
| --- | --- |
| What is MPC? | Python package for greenhouse pump recommendation. |
| Public interface | Python imports used by backend/tests. |
| Runtime owner | Green-House backend. |
| ARX source | Trained `ARX/arx_model.json` artifact. |
| Does MPC train ARX? | No. |
| Solver | `scipy.optimize.minimize` over future pump seconds. |
| Control state | FAO-56 `Dr/RAW/TAW`. |
| Dashboard forecast unit | Sensor percent. |
| Safety behavior | Fail closed with `pump_seconds=0` on stale/config/model/solver/actuator errors. |
