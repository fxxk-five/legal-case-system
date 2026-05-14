# Health Repair Execution 2026-05-14

## Goal

Repair the hard failures found by the project health check while avoiding unrelated refactors in the current large working tree.

## Scope

- Backend test collection: make `pytest -q` collect only `backend/tests`.
- Documentation gate: keep every Markdown document under `docs` and `plans` listed in `docs/documentation-map.md`.
- Documentation encoding: keep Markdown files compatible with the repository UTF-8 BOM gate.
- Service size warning: track the `AuthLoginService` threshold separately with the backend module batch.

## Execution Plan

1. Add `backend/pytest.ini` with `testpaths = tests` so `backend/test_results.txt` is not collected as a test artifact.
2. Add this execution note to `docs/documentation-map.md` so the repair itself is tracked.
3. Keep changed Markdown files encoded as UTF-8 with BOM to satisfy `scripts/check-docs-integrity.ps1`.
4. Rerun the backend, frontend, documentation, boundary, and static checks used in the health review.

## Expected Verification

- `cd backend; .\venv\Scripts\python.exe -m pytest -q`
- `cd web-frontend; npm run lint`
- `cd web-frontend; npm run test`
- `cd web-frontend; npm run build`
- `powershell -ExecutionPolicy Bypass -File scripts\check-docs-integrity.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts\check-status-doc-update.ps1`
- `cd backend; .\venv\Scripts\python.exe ..\scripts\check-router-boundaries.py`
- `cd backend; .\venv\Scripts\python.exe ..\scripts\check-schema-boundaries.py`
- `cd backend; .\venv\Scripts\python.exe ..\scripts\check-auth-repository-boundaries.py`
- `cd backend; .\venv\Scripts\python.exe ..\scripts\check-service-size-threshold.py`
- `python scripts\mini_program_static_audit.py`
