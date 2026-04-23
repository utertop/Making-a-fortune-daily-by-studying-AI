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

Open:

```text
http://127.0.0.1:3100
```

## Today Workspace API

The web workspace reads and updates local task state through the backend:

```text
GET  http://127.0.0.1:8000/tasks/today?limit=10
POST http://127.0.0.1:8000/tasks/{task_id}/status
```

Supported task statuses:

```text
pending, pushed, selected, documented, archived, ignored
```

Opening the workspace creates local `learning_task` rows from the current Top Signals if they do not already exist.

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



## Security Rules

Before committing, read docs/SECURITY_RULES.md. Do not commit .env, tokens, webhook URLs, local databases, caches, logs, .venv/, or node_modules/.

