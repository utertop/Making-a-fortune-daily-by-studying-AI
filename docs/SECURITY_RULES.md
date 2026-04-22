# Security Rules

This project is local-first, but it may use external services such as GitHub, Feishu, and future LLM providers. Secrets must never be committed.

## Never Commit

Do not commit any of the following:

- `.env`
- real Feishu webhook URLs
- GitHub tokens
- OpenAI / Anthropic / Gemini API keys
- Supabase service role keys
- OAuth tokens
- private keys, certificates, `.pem`, `.p12`, `.pfx`
- local SQLite databases, for example `data/local.db`
- logs that may contain request headers or secrets
- `.venv/`
- `.pip-cache/`
- `.npm-cache/`
- `node_modules/`

## Safe to Commit

These are safe and expected to be committed:

- `.env.example`
- docs with placeholder secrets only
- source code
- schema files
- scripts
- Markdown knowledge documents without real secrets

## Placeholder Format

Use placeholders like:

```text
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
GITHUB_TOKEN=
OPENAI_API_KEY=
```

## Before Every Commit

Run:

```powershell
git -c safe.directory=D:/Automatic/github_ai_learn status --short
```

Check that no secret files or local generated files are staged.

If unsure, inspect staged diff:

```powershell
git -c safe.directory=D:/Automatic/github_ai_learn diff --cached
```

## If a Secret Is Accidentally Committed

1. Rotate or revoke the exposed secret immediately.
2. Remove it from the repository.
3. Treat the secret as compromised even if the repo is private.

## Project Rule

All installs, caches, databases, generated logs, and secrets must stay inside this project directory when possible, and sensitive files must stay ignored by Git.
