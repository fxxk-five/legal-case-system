# Repository Branch Split Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the current mixed working tree into reviewable branch-sized batches without losing the verified green local baseline.

**Architecture:** Work from the current mixed tree as the source of truth, but execute each low-risk batch in an isolated git worktree created from the clean `HEAD`. Start with the most independently verifiable domain, confirm it in isolation, then continue with the next branch-sized batch.

**Tech Stack:** Git worktrees, PowerShell, FastAPI backend, Vue/Vite web frontend, UniApp mini-program, repository validation scripts.

---

## Batch Map

### Branch A: `codex/refactor-backend-module-boundaries`

- Batch A1: API entry and router aggregation
  - `backend/app/api/api_v1.py`
  - `backend/app/main.py`
  - `backend/app/api/routes_*.py` deletions
  - `backend/app/modules/*/router.py`
- Batch A2: auth / invites / tenants / users consolidation
  - `backend/app/modules/auth/**`
  - `backend/app/modules/invites/**`
  - `backend/app/modules/tenants/**`
  - `backend/app/modules/users/**`
  - `backend/app/dependencies/auth.py` deletion
  - `backend/app/services/{auth,invite,sms,mini_program}.py` deletions
- Batch A3: ai / files / integrations consolidation
  - `backend/app/modules/ai/**`
  - `backend/app/modules/files/**`
  - `backend/app/integrations/{llm,sms,storage,wechat}/**`
- Batch A4: models / schema cleanup / migrations / tests
  - `backend/app/models/**`
  - `backend/app/schemas/**`
  - `backend/alembic/versions/**`
  - `backend/tests/**`

### Branch B: `codex/refactor-web-frontend-structure`

- Batch B1: shared + features foundation
  - `web-frontend/src/shared/**`
  - `web-frontend/src/features/**`
  - `web-frontend/src/lib/**` deletions
  - `web-frontend/src/stores/{ai,auth,notifications}.js` deletions
- Batch B2: app shell + auth/system pages
  - `web-frontend/src/app/**`
  - `web-frontend/src/main.js`
  - `web-frontend/src/pages/auth/**`
  - `web-frontend/src/pages/system/**`
  - `web-frontend/src/router/index.js`
  - `web-frontend/src/stores/index.js`
- Batch B3: workspace + AI pages
  - `web-frontend/src/pages/**`
  - `web-frontend/src/components/ai/**`
  - `web-frontend/src/views/**` deletions

### Branch C: `codex/refactor-mini-program-structure`

- Batch C1: shared API / session foundation
  - `mini-program/common/**` deletions
  - `mini-program/shared/**`
  - `mini-program/features/auth/**`
  - `mini-program/features/workspace/**`
  - `mini-program/components/{CaseRemarkInput.vue,ClientTabBar.vue,WorkspaceTabBar.vue}`
- Batch C2: login and permission flow
  - `mini-program/pages/login/index.vue`
  - `mini-program/pages/common/force-reset-password.vue`
  - `mini-program/pages/common/my.vue`
- Batch C3: client case and upload flow
  - `mini-program/pages/client/**`
  - `mini-program/features/cases/**`
  - `mini-program/entities/**`
  - `mini-program/components/{LongTaskStatusCard.vue,PageStatusBanner.vue,UploadFailureNotice.vue}`

### Branch D: `codex/chore-docs-tooling-and-deploy`

- Batch D1: documentation truth + cleanup
  - `docs/current-project-status.md`
  - `docs/final-acceptance-checklist.md`
  - `docs/documentation-map.md`
  - `docs/README.md`
  - `docs/release-execution-workorder.md`
  - `plans/project-overall-blueprint.md`
  - deleted legacy docs and plans
- Batch D2: tooling / guard scripts / CI / contracts
  - `scripts/check-*.py`
  - `scripts/check-*.ps1`
  - `scripts/smoke_login_matrix.py`
  - `scripts/sync-status-code-map.py`
  - `.github/**`
  - `contracts/**`
- Batch D3: deploy baseline
  - `deploy/backend.env.tencent.*.example`
  - `docker-compose.prod.yml`
  - `docs/production-deployment.md`
  - `README.md`

## Verification Commands

- Backend full baseline: `python -m pytest backend/tests -q`
- Backend route boundary: `python scripts/check-router-boundaries.py`
- Web lint/test/build:
  - `npm --prefix web-frontend run lint`
  - `npm --prefix web-frontend run test`
  - `npm --prefix web-frontend run build`
- Mini-program baseline:
  - `python scripts/mini_program_static_audit.py`
  - `python scripts/smoke_login_matrix.py`
- Docs/tooling baseline:
  - `powershell -ExecutionPolicy Bypass -File scripts/check-docs-integrity.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`

## Execution Order

- [ ] Step 1: Prepare the plan file and confirm the current green baseline references
- [ ] Step 2: Create an isolated worktree for Branch D and replay docs/tooling changes there first
- [ ] Step 3: Run docs/tooling verification in the isolated worktree
- [ ] Step 4: Use the same replay pattern for Branch A, then Branch B, then Branch C
- [ ] Step 5: Only after isolated verification, decide whether to stage/commit each branch batch

## Why Branch D First

- It is the lowest-risk branch-sized batch.
- It has independent validation.
- It gives the repository a permanent execution record before touching the harder code branches.
- It avoids forcing interactive staging on the current mixed working tree.
