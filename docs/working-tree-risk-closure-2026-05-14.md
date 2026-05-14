# Working Tree Risk Closure 2026-05-14

## Goal

Reduce the risk from the mixed local working tree by preserving a recovery snapshot and moving verified slices into reviewable GitHub branches.

## Recovery Snapshot

- Snapshot directory: `C:\Users\10693\.codex\snapshots\legal-case-system\20260514-202039`
- Tracked diff: `tracked.patch`
- Untracked files: `untracked-files.zip`
- Untracked zip entries: `264`

## Branches Created Or Updated

| Branch | Purpose | Status |
| --- | --- | --- |
| `codex/chore-docs-tooling-and-deploy` | Docs, tooling, deploy baseline, health gate repair | Pushed |
| `codex/backend-a3-ai-files-integrations` | Backend modules/integrations consolidation through AI/files/storage | Pushed |
| `codex/refactor-web-frontend-structure` | Web `app/features/entities/shared/pages` migration | Pushed |
| `codex/refactor-mini-program-structure` | Mini-program `features/entities/shared` migration | Pushed |

## Validation Evidence

- `codex/chore-docs-tooling-and-deploy`
  - `powershell -ExecutionPolicy Bypass -File scripts\check-docs-integrity.ps1`: PASS
  - `powershell -ExecutionPolicy Bypass -File scripts\check-status-doc-update.ps1`: PASS
  - `python scripts\check_mojibake.py`: PASS
- `codex/backend-a3-ai-files-integrations`
  - `python -m pytest tests -q`: `216 passed, 5 warnings`
  - router/schema/auth repository boundary checks: PASS
- `codex/refactor-web-frontend-structure`
  - `npm run lint`: PASS
  - `npm run test`: `58 passed`
  - `npm run build`: PASS
- `codex/refactor-mini-program-structure`
  - `python scripts\mini_program_static_audit.py`: `17/17 passed`
  - Old `mini-program/common` import search: no code import hits; only `pages/common/*` page paths remain.

## Remaining Local-Only Risk

The source checkout at `D:\code\law\legal-case-system` intentionally still contains the full mixed working tree. It should be treated as a staging source, not a review branch.

Local-only paths that should not be pushed as product code:

- `.runtime/`
- `backend/.runtime/`
- `tmp/`
- `.claude/settings.local.json`
- `.codebuddy/`
- `backend/test_results.txt`
- generated mini-program `unpackage/` output

## Recommended Next Order

1. Use the pushed branches above for review or PR creation.
2. Do not create a PR from `codex/ai-agent-rag-review`; it remains the mixed source branch.
3. Resolve the dirty `codex/backend-a1-router-aggregation` worktree separately, because it contains uncommitted intermediate auth/router changes that overlap with the later backend branch chain.
4. After all review branches are accepted or discarded, replace the mixed source checkout with a clean branch rather than continuing new work there.
