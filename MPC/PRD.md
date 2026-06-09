# Product Requirements Document - MPC / AMPC Controller

> Source of truth cho `MPC/`. TÃ i liá»‡u nÃ y Ä‘Æ°á»£c táº¡o tá»« onboarding MPC ngÃ y 2026-05-08 vÃ  káº¿ hoáº¡ch v2/v3 Ä‘Ã£ Ä‘Æ°á»£c user duyá»‡t.

---

**Version**: 1.0
**Status**: Draft
**Last updated by human**: 2026-05-08
**Product owner**: Project owner

---

## 1. Executive Summary


---

## 2. Problem Statement

### 2.1 Current Situation

`Kalman/` Ä‘Ã£ cÃ³ live-only pipeline: ingest sensor, ARX prior, Adaptive Kalman posterior, MySQL trace, dashboard online. Tuy nhiÃªn repo chÆ°a cÃ³ controller thá»±c sá»± Ä‘á»ƒ biáº¿n state Ä‘á»™ áº©m Ä‘áº¥t thÃ nh lá»‡nh bÆ¡m.

### 2.2 The Problem

Äiá»u khiá»ƒn tÆ°á»›i thá»§ cÃ´ng hoáº·c threshold-based pháº£n á»©ng cháº­m, dá»… tÆ°á»›i quÃ¡ má»©c, vÃ  khÃ´ng táº­n dá»¥ng Ä‘Æ°á»£c dá»± bÃ¡o Ä‘á»™ng há»c. Cáº§n má»™t controller cÃ³ thá»ƒ nhÃ¬n trÆ°á»›c trong horizon, cÃ¢n báº±ng giá»¯a giá»¯ Ä‘á»™ áº©m trong band vÃ  giáº£m nÆ°á»›c/switching.

### 2.3 Why Now

Estimator live-only Ä‘Ã£ á»•n Ä‘á»‹nh, ARX artifact Ä‘Ã£ cÃ³ input `Drip`, vÃ  user Ä‘Ã£ chá»‘t scope controller chá»‰ Ä‘iá»u khiá»ƒn bÆ¡m nÆ°á»›c. ÄÃ¢y lÃ  thá»i Ä‘iá»ƒm phÃ¹ há»£p Ä‘á»ƒ tÃ¡ch controller thÃ nh project riÃªng Ä‘á»ƒ phÃ¡t triá»ƒn v2 MPC rá»“i nÃ¢ng lÃªn v3 AMPC.

---

## 3. Goals & Success Metrics

### 3.1 Goals

- DÃ¹ng ARX artifact hiá»‡n cÃ³ lÃ m plant model ban Ä‘áº§u vÃ  map `pump_seconds / 300` sang `Drip`.
- ÄÃ¡nh giÃ¡ controller báº±ng band violation, tá»•ng thá»i gian bÆ¡m, switching count, vÃ  objective cost.
- V3 thÃªm RLS adaptation vÃ  closed-loop pilot an toÃ n qua HTTP actuator adapter.

### 3.2 Success Metrics

| Metric | Baseline | Target | How Measured |
|--------|----------|--------|--------------|
| Solver determinism | N/A | CÃ¹ng input cho cÃ¹ng output | Unit tests |
| Safety fail-closed | N/A | 100% lá»—i stale/model/API tráº£ pump off | Safety tests |

---

## 4. User Personas

### Persona: Project Owner / Research Implementer

- **Role**: NgÆ°á»i xÃ¢y dá»±ng vÃ  báº£o vá»‡ project smart greenhouse.
- **Goals**: CÃ³ controller MPC/AMPC rÃµ rÃ ng, test Ä‘Æ°á»£c, giáº£i thÃ­ch Ä‘Æ°á»£c báº±ng mÃ´ hÃ¬nh vÃ  metric.
- **Pain points**: Code controller láº«n vÃ o estimator sáº½ khÃ³ review; controller thiáº¿u fail-safe sáº½ nguy hiá»ƒm khi lÃªn pháº§n cá»©ng.
- **Technical level**: Developer/research.
- **Usage frequency**: ThÆ°á»ng xuyÃªn trong giai Ä‘oáº¡n implementation vÃ  demo.

### Persona: Greenhouse Operator

- **Role**: NgÆ°á»i váº­n hÃ nh nhÃ  kÃ­nh nhá»/demo.
- **Goals**: Nháº­n Ä‘á» xuáº¥t hoáº·c lá»‡nh bÆ¡m giÃºp giá»¯ Ä‘á»™ áº©m Ä‘áº¥t trong vÃ¹ng an toÃ n.
- **Pain points**: Threshold/manual control pháº£n á»©ng cháº­m vÃ  cÃ³ thá»ƒ lÃ£ng phÃ­ nÆ°á»›c.
- **Technical level**: Non-technical to moderate.
- **Usage frequency**: Khi cháº¡y demo hoáº·c pilot.

---

## 5. Functional Requirements

### 5.1 Project Scaffold

- **FR-001**: Project pháº£i cÃ³ folder `MPC/` riÃªng á»Ÿ repo root vá»›i README, PRD, TODO, `.tasks/`, docs technical/user/content/plan.
- **FR-002**: Project pháº£i lÆ°u Q&A onboarding MPC Ä‘á»ƒ cÃ¡c quyáº¿t Ä‘á»‹nh Ä‘Ã£ chá»‘t khÃ´ng bá»‹ há»i láº¡i.
- **FR-003**: Backlog MPC pháº£i cÃ³ task tháº­t cho v2/v3, khÃ´ng Ä‘á»ƒ placeholder template.


- **FR-010**: MPC pháº£i dÃ¹ng step `300s`, horizon `12`, target band máº·c Ä‘á»‹nh `55-65%`.
- **FR-011**: MPC pháº£i nháº­n state Æ°u tiÃªn `kf_x_posterior`, fallback `raw_soil_moisture`.
- **FR-012**: MPC pháº£i biá»ƒu diá»…n control lÃ  `pump_seconds` trong `[0, 300]` má»—i step.
- **FR-013**: Plant model v2 pháº£i reuse `../ARX/arx_model.json` vÃ  map `pump_seconds / 300` vÃ o ARX input `Drip`.
- **FR-014**: Disturbance `Temperature/Humidity/Light` trong v2 dÃ¹ng measured-hold forecast.
- **FR-015**: Solver dÃ¹ng `scipy.optimize.minimize` Ä‘á»ƒ tá»‘i Æ°u chuá»—i lá»‡nh bÆ¡m trong horizon; khÃ´ng yÃªu cáº§u CVXPY.
- **FR-016**: Recommendation output pháº£i cÃ³ `pump_seconds`, `step_seconds`, `predicted_soil_moisture`, `target_band`, `cost`, `safety_status`, `reason`.

### 5.3 V3 AMPC

- **FR-020**: AMPC pháº£i cáº­p nháº­t há»‡ sá»‘ ARX báº±ng RLS dá»±a trÃªn prediction error/Kalman residual gáº§n Ä‘Ã¢y.
- **FR-022**: Adaptation pháº£i cÃ³ guard Ä‘á»ƒ khÃ´ng lÃ m máº¥t fail-safe khi residual thiáº¿u, stale, hoáº·c outlier.

### 5.4 Closed-Loop Pilot

- **FR-030**: V3 closed-loop pilot pháº£i gá»­i actuator command báº±ng HTTP POST vá»›i Bearer token tá»« env/config.
- **FR-031**: Command payload pháº£i gá»“m `command_id`, `timestamp`, `run_id`, `pump_seconds`, `step_seconds`, `mode`, `reason`, `safety_status`.
- **FR-032**: Náº¿u thiáº¿u URL/token, sample stale quÃ¡ 10 phÃºt, state thiáº¿u, solver lá»—i, model lá»—i, hoáº·c actuator API lá»—i, controller pháº£i fail closed: pump off + alert/log.
- **FR-033**: Auto execute chá»‰ Ä‘Æ°á»£c cháº¡y khi config explicit há»£p lá»‡; test pháº£i dÃ¹ng fake actuator, khÃ´ng gá»i pháº§n cá»©ng tháº­t.

---

## 6. Non-Functional Requirements

### Performance

- Solve v2 recommendation cho horizon 12 pháº£i Ä‘á»§ nhanh cho chu ká»³ 5 phÃºt; target local p95 dÆ°á»›i 1 giÃ¢y.

### Security

- KhÃ´ng commit secret.
- Bearer token chá»‰ láº¥y tá»« env/config runtime.
- Actuator command pháº£i validate bounds trÆ°á»›c khi gá»­i.

### Reliability

- Fail-safe máº·c Ä‘á»‹nh lÃ  pump off.
- Backend/package integration pháº£i tráº£ lá»—i rÃµ rÃ ng khi artifact/input/config khÃ´ng há»£p lá»‡.

### Maintainability

- V2 pháº£i giá»¯ package Ä‘á»™c láº­p vá»›i Django.
- API/interface pháº£i Ä‘á»§ rÃµ Ä‘á»ƒ sau nÃ y tÃ­ch há»£p backend mÃ  khÃ´ng rewrite solver.

---

## 7. Out of Scope

- KhÃ´ng implement Hybrid MPC hoáº·c Hierarchical MPC.
- KhÃ´ng control `Mist` hoáº·c `Fan`.
- KhÃ´ng ghi DB trong v2.
- KhÃ´ng thÃªm Django endpoint á»Ÿ phase scaffold.
- KhÃ´ng Ä‘iá»u khiá»ƒn pháº§n cá»©ng tháº­t trÆ°á»›c khi task closed-loop pilot cÃ³ fake tests vÃ  fail-safe.
- KhÃ´ng train láº¡i ARX trong MPC v2.

---

## 8. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | Grid resolution cho `pump_seconds` nÃªn lÃ  bao nhiÃªu giÃ¢y? | Project owner | Answered by ADR-004: default `30s` |
| 2 | Cost weights cá»¥ thá»ƒ cho band/water/switching/daily cap lÃ  bao nhiÃªu? | Project owner | Answered by ADR-004: band `10.0`, terminal band `20.0`, water `0.2`, switching `0.5`, daily cap excess `2.0` |
| 3 | Soft daily cap máº·c Ä‘á»‹nh lÃ  bao nhiÃªu giÃ¢y/ngÃ y? | Project owner | Answered by ADR-004: `1800s/day` soft cap |
| 4 | Actuator HTTP endpoint vÃ  payload final cá»§a thiáº¿t bá»‹ tháº­t lÃ  gÃ¬? | Project owner | Open trÆ°á»›c v3 pilot |
| 5 | CÃ³ flow rate bÆ¡m tháº­t Ä‘á»ƒ Ä‘á»•i seconds sang ml/L khÃ´ng? | Project owner | Deferred |

---

## 9. Revision History

| Date | Author | Change Description |
|------|--------|--------------------|
| 2026-05-08 | Project owner / Codex | Initial MPC/AMPC project draft from approved plan and onboarding Q&A |
