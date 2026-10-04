# RoboAssistant Company OS & Development Guidelines

## Project Execution & Local Server
- The unified multi-tenant backend API and frontend web application are served via `api_server.py`.
- **Start Command**: `python3 api_server.py 8080`
- **Local URL**: `http://localhost:8080`
- **Health Check**: `http://localhost:8080/health`
- **Web UI**: `http://localhost:8080/` (serves `web/index.html`)

## Mandatory Git Workflow
- **Commit & Push Policy**: After **every** development task, bug fix, feature addition, or configuration update:
  1. Test and verify code functionality locally on `http://localhost:8080`.
  2. Stage modified and newly created files (`git add <files>`).
  3. Commit with a concise and descriptive message following Conventional Commits format (`git commit -m "<type>: <description>"`).
  4. Push the commit to the remote repository immediately (`git push origin main`).
