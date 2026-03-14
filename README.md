# Legal Case System

Single-law-firm pilot with multi-tenant-ready architecture.

## Stack Plan

- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- Web: Vue 3 + Vite + Element Plus
- Mini Program: uni-app
- Infrastructure: Docker + Redis + Nginx

## Repository Structure

- `backend/`: FastAPI backend service
- `web-frontend/`: Vue 3 web application
- `mini-program/`: uni-app / WeChat Mini Program
- `docs/`: planning, setup, deployment, API notes
- `scripts/`: local helper scripts

## Day 1 Deliverables

- Project skeleton created
- Git repository initialized
- `.gitignore` added
- `.editorconfig` added
- Environment check script added
- Setup docs added

## Local Prerequisites

Install and verify these before Day 2:

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis
- Docker
- Git
- VS Code

## Quick Start

Run the local environment check on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-env.ps1
```

Then:

1. Create a remote repository on GitHub or Gitee.
2. Add the remote locally.
3. Push the current branch.

## Related Docs

- `docs/day-01-checklist.md`
- `docs/project-setup.md`
