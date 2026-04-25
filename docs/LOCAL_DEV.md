# Local Development

v0.1 starts local-first.

## Backend

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Frontend

PowerShell may block `npm.ps1`; use `npm.cmd`.

```powershell
cd apps/web
npm.cmd install
npm.cmd run dev
```

Project-local install shortcut:

```powershell
scripts\install_web_deps.cmd
```

Open:

```text
http://127.0.0.1:3100
```

## One-command Local Startup

Start backend and frontend in two PowerShell windows:

```powershell
.\scripts\start_local.ps1
```

If PowerShell execution policy blocks `.ps1` scripts, use:

```powershell
scripts\start_local.cmd
```

The script starts:

```text
API: http://127.0.0.1:8000
Web: http://127.0.0.1:3100
Scheduler: enabled
```

The local scheduler sends Feishu pushes at:

```text
08:00 morning push
14:00 afternoon push
21:30 soft deadline
23:00 hard deadline
```

Use this only if you want API + Web without the local scheduler:

```powershell
scripts\start_local.cmd -NoScheduler
```

## Windows Task Scheduler

If you want pushes to run even when you did not manually open the local Web page, register Windows Scheduled Tasks:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\register_windows_tasks.ps1
```

This registers four daily tasks under `\AI Signal Radar\`:

```text
Morning Push    08:00
Afternoon Push  14:00
Soft Deadline   21:30
Hard Deadline   23:00
```

Preview the registration commands without changing the system:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\register_windows_tasks.ps1 -Preview
```

Remove those Scheduled Tasks:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\unregister_windows_tasks.ps1
```

After registration, `scripts\start_local.cmd` will show:

```text
Scheduler: managed by Windows Task Scheduler
```

That means local Web/API startup will no longer launch the loop scheduler by default, which avoids duplicate pushes.

## Windows Startup Catch-up

If you want a one-time catch-up check whenever you log in, register the Startup entry:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\register_startup_catchup.ps1
```

This creates a Startup script that runs:

```text
scripts\run_login_catchup.cmd
```

That catch-up flow checks whether any of today's scheduled jobs were missed and replays them in scheduled order.

Preview without changing the system:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\register_startup_catchup.ps1 -Preview
```

Remove the Startup entry:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\unregister_startup_catchup.ps1
```

To allow access from another device on the same LAN:

```powershell
scripts\start_local.cmd --lan
```

LAN mode binds API and Web to `0.0.0.0` and prints the detected LAN URL when possible. Use it only on a trusted network.
When the Web page is opened through a LAN IP, client-side task actions automatically call the same host on API port `8000`.

## Daily Flow

Run collection, GitHub scoring, Today Workspace task preparation, and Feishu preview:

```powershell
.\.venv\Scripts\python.exe scripts\daily_flow.py
```

Windows shortcut:

```powershell
scripts\daily_flow.cmd
```

Send the Feishu message for real:

```powershell
.\.venv\Scripts\python.exe scripts\daily_flow.py --send
```

Useful options:

```powershell
.\.venv\Scripts\python.exe scripts\daily_flow.py --skip-rss
.\.venv\Scripts\python.exe scripts\daily_flow.py --skip-github
.\.venv\Scripts\python.exe scripts\daily_flow.py --skip-push
.\.venv\Scripts\python.exe scripts\daily_flow.py --limit 5
```

## Local Doctor

Check local readiness:

```powershell
scripts\doctor.cmd
```

The doctor checks the local database, knowledge-base folders, Feishu webhook presence, API/Web reachability, and common Web dependency problems.

If it reports missing Next.js command shim or type definitions, run:

```powershell
scripts\install_web_deps.cmd
```

## Today Workspace API

The web workspace reads and updates local task state through the backend:

```text
GET  http://127.0.0.1:8000/tasks/today?limit=10
POST http://127.0.0.1:8000/tasks/{task_id}/status
POST http://127.0.0.1:8000/tasks/{task_id}/draft
POST http://127.0.0.1:8000/tasks/{task_id}/document
```

Supported task statuses:

```text
pending, pushed, selected, documented, archived, ignored
```

Opening the workspace creates local `learning_task` rows from the current Top Signals if they do not already exist.

Generating a draft writes a Markdown file under `knowledge-base/daily/YYYY/MM/YYYY-MM-DD/`, records it as a draft `knowledge_document`, and moves the task into `selected`.

Submitting a Markdown document creates or updates a `knowledge_document` row, stores the document path on the task, and marks that task as `documented`.

## Feishu Push

Detailed setup guide: `docs/FEISHU_WEBHOOK.md`.

Create a local `.env` from `.env.example`, then set:

```text
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx
```

Preview today's task message without sending:

```powershell
.venv\Scripts\python scripts\push_today.py --limit 5
```

Send to Feishu:

```powershell
.venv\Scripts\python scripts\push_today.py --send --limit 10
```

The script does not send anything unless `--send` is provided.

Preview one local scheduled push without sending:

```powershell
.venv\Scripts\python scripts\local_scheduler.py --run-now morning_push --preview
.venv\Scripts\python scripts\local_scheduler.py --run-now soft_deadline --preview
```



## Security Rules

Before committing, read docs/SECURITY_RULES.md. Do not commit .env, tokens, webhook URLs, local databases, caches, logs, .venv/, or node_modules/.

