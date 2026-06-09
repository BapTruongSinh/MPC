# MPC Database Notes

MPC does not own database models. Green-House provides the current state and
configuration before calling the solver.

Runtime data is scoped by `greenhouse_id`:

- `greenhouse_control_profiles` stores one controller configuration per greenhouse.
- `api_estimationcycle` stores Kalman/live-window state for each greenhouse.
- `api_ampcrecommendation` stores MPC recommendations for each greenhouse.

Legacy experiment run/config/evaluation tables are not part of the runtime
pipeline.
