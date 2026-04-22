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
http://127.0.0.1:3000
```
