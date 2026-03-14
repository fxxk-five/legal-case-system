# Project Setup

## Repository Layout

- `backend/`: FastAPI service
- `web-frontend/`: Vue 3 + Vite web app
- `mini-program/`: uni-app WeChat mini program
- `docs/`: planning, setup, deployment, API notes
- `scripts/`: local helper scripts

## Day 1 Outcome

By the end of Day 1, the repository should provide:

- a clean Git repository
- a stable top-level directory structure
- ignore rules for local and generated files
- basic editor consistency rules
- a local environment check script

## Before Day 2

1. Run `powershell -ExecutionPolicy Bypass -File .\scripts\check-env.ps1`
2. Create a remote repository on GitHub or Gitee
3. Add the remote:
   - `git remote add origin <your-repo-url>`
4. Push the current branch:
   - `git push -u origin main`

## Notes

- Day 2 should start only after the local toolchain is confirmed.
- Keep secrets out of Git from the beginning. Use `.env` files later.
