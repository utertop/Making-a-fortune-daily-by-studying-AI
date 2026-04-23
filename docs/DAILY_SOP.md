# Daily SOP

This is the shortest daily operating path for v0.1.

## 1. Check Local Readiness

```powershell
scripts\doctor.cmd
```

If API or Web is unreachable, start local services in step 2.

If Next.js command shim or type definitions are missing, run:

```powershell
scripts\install_web_deps.cmd
```

## 2. Start Workspace

```powershell
scripts\start_local.cmd
```

Open:

```text
http://127.0.0.1:3100
```

## 3. Run Daily Radar

Preview only:

```powershell
scripts\daily_flow.cmd
```

Send Feishu push:

```powershell
scripts\daily_flow.cmd --send
```

## 4. Finish Today's Learning Loop

In Today Workspace:

1. Review Top Signals.
2. Mark pushed / selected / ignored.
3. Generate Markdown draft for worthy projects.
4. Fill the draft with Codex or Antigravity.
5. Submit the Markdown document record.
6. Confirm today's progress is complete.

## Safety

Never commit `.env`, webhook URLs, tokens, local databases, caches, or `node_modules`.
