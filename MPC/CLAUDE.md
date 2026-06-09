# MPC - Claude Instructions

> Stack: Python package · FAO-56 water-balance MPC · optional HTTP actuator pilot
> Last updated: 2026-06-09

## Project Context

`MPC/` la project controller tach rieng khoi `Kalman/`. Trang thai hien tai la MPC thuong: solver dung FAO-56 water balance va `scipy.optimize.minimize` de toi uu chuoi thoi gian bom. MPC khong load ARX artifact va khong chay RLS; ARX neu co chi thuoc luong Kalman truoc khi backend tao `ControllerState`.

**Tech stack summary**: No frontend in v2 Â· Python package imported by backend Â· no DB ownership in v2 Â· optional HTTP actuator pilot in v3

---

## Critical Rules

1. `MPC/` lÃ  project root cho controller. KhÃ´ng viáº¿t code MPC vÃ o `Green-House/backend` trá»« khi cÃ³ task integration rÃµ.
2. `ARX/` lÃ  context/artifact source. KhÃ´ng sá»­a training/data generator cá»§a `ARX/` náº¿u task chá»‰ lÃ  MPC.
3. `Kalman/` lÃ  upstream estimator/runtime. MPC Ä‘Æ°á»£c Ä‘á»c output live/Kalman posterior, khÃ´ng phÃ¡ live-only invariant hiá»‡n táº¡i.
4. `MPC/PRD.md` lÃ  source of truth cho controller v2/v3. Chá»‰ sá»­a khi user yÃªu cáº§u hoáº·c khi Ä‘ang cháº¡y onboarding/task planning cho MPC.
5. `MPC/TODO.md` vÃ  `MPC/.tasks/` lÃ  backlog source of truth cho MPC. LÃ m xong task nÃ o pháº£i tick task Ä‘Ã³ vÃ  cáº­p nháº­t file task tÆ°Æ¡ng á»©ng.
6. TrÆ°á»›c má»—i task pháº£i Ä‘á»c `.claude/.claude/rules/`, `.claude/.claude/review/REVIEW.md`, `MPC/docs/technical/CODEBASE_ONBOARDING.md`, `MPC/TODO.md`, vÃ  task file liÃªn quan.
7. Má»—i task pháº£i cÃ³ `required_skills` trong task file vÃ  pháº£i dÃ¹ng Ä‘Ãºng skill local/system tÆ°Æ¡ng á»©ng trÆ°á»›c khi thá»±c hiá»‡n.
8. Má»—i task chá»‰ Ä‘Æ°á»£c hoÃ n táº¥t khi qua Ä‘á»§ 4 gate: Logic, Nghiá»‡p vá»¥, Security, Test cháº¡y thá»±c táº¿.
9. KhÃ´ng hardcode secret, actuator URL, Bearer token, hoáº·c thÃ´ng sá»‘ pháº§n cá»©ng nháº¡y cáº£m. DÃ¹ng config/env khi implement.
10. V2 khÃ´ng Ä‘iá»u khiá»ƒn pháº§n cá»©ng. V3 closed-loop pháº£i fail closed: lá»—i sensor/model/API/stale sample thÃ¬ pump off + alert/log.
11. Chá»‰ cáº­p nháº­t `MPC/docs/technical/CODEBASE_ONBOARDING.md` sau khi user review vÃ  xÃ¡c nháº­n flow/code Ä‘Ã£ á»•n.
12. Sau má»—i prompt/task, cáº­p nháº­t `.claude/.claude/review/REVIEW.md`.
13. TÃ i liá»‡u markdown trong `MPC/` dÃ¹ng tiáº¿ng Viá»‡t cÃ³ dáº¥u, giá»¯ nguyÃªn thuáº­t ngá»¯ ká»¹ thuáº­t cáº§n thiáº¿t.

---

## Required Skills And Gates

| Area | Required skills |
|------|-----------------|
| planning | `planning`, `docs` |
| backend | `backend`, `quality`; thÃªm `backend-security-coder` náº¿u cÃ³ actuator/auth/safety |
| qa | `quality` |
| docs | `docs`, `quality` |
| setup | `planning`, `docs` |

Má»i task pháº£i cÃ³ checklist `## Completion Gates` trong `.tasks/NNN-*.md`:

- Logic: luá»“ng xá»­ lÃ½ khÃ´ng mÃ¢u thuáº«n vÃ  khÃ´ng táº¡o side effect sai.
- Nghiá»‡p vá»¥: bÃ¡m Ä‘Ãºng PRD/Q&A/ADR cá»§a MPC.
- Security: khÃ´ng lá»™ secret, validate input/config, fail-safe Ä‘Ãºng vá»›i actuator.
- Test cháº¡y thá»±c táº¿: cÃ³ command/check cá»¥ thá»ƒ Ä‘Ã£ cháº¡y hoáº·c ghi rÃµ vÃ¬ sao chÆ°a Ã¡p dá»¥ng.

---

## Environment & Commands

Current package status: task #016 removed the MPC-side ARX/RLS modules. Use `ScipyMpcSolver`; it rolls out `Dr_next = Dr + ETc_step - I(u_k)` through FAO-56 and executes only the first optimized pump command.

Current solver note: solver uses scipy bounds with fail-closed validation. Run MPC through backend integration or direct Python imports in tests.


- **Run tests**: `python -m pytest MPC/tests -q`
- **Compile package**: `python -m compileall -q MPC/mpc`

---

## Key Documentation

@MPC/PRD.md
@MPC/TODO.md
@MPC/docs/technical/ONBOARDING_ANSWERS.md
@MPC/docs/technical/ARCHITECTURE.md
@MPC/docs/technical/DECISIONS.md
@MPC/docs/technical/CONFIG.md
@MPC/docs/technical/API.md
@MPC/docs/technical/DATABASE.md
@MPC/docs/technical/VALIDATION.md
@MPC/docs/technical/CODEBASE_ONBOARDING.md
@MPC/docs/plan/2026-05-08-mpc-v2-ampc-v3.md
@Green-House/docs/technical/CODEBASE_ONBOARDING.md
@Green-House/docs/technical/AMPC_MODELING_HANDOFF.md
