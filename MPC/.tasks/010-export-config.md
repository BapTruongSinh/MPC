---
id: "010"
title: "Export MPC config"
status: "done"
area: "backend"
agent: "@builder"
required_skills: ["backend", "quality", "docs"]
priority: "normal"
created_at: "2026-05-09"
completed_at: "2026-05-09"
---

## Description

Export controller defaults and field groups for UI/API clients. Runtime calls
MPC through backend integration or direct Python imports.

## Acceptance Criteria

- [x] Module-level config metadata is available from `mpc.core.schema`.
- [x] Metadata includes controller defaults and field groups.
- [x] Runtime does not depend on terminal commands.

## Completion Gates

- [x] Logic: config metadata remains importable.
- [x] Business: backend can build `ControllerConfig` from DB profile fields.
- [x] Security: no secret values are emitted.
- [x] Test: package tests cover config behavior.
