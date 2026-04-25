from pathlib import Path
import json
import os
import sys
import urllib.error
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.db import database_status, init_database


def check_path(path, description, required=True):
    exists = Path(path).exists()
    return {
        "name": description,
        "ok": exists if required else True,
        "status": "ok" if exists else ("missing" if required else "not_found"),
        "path": str(path),
    }


def check_url(url, description):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return {
                "name": description,
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "url": url,
            }
    except (urllib.error.URLError, TimeoutError) as error:
        return {
            "name": description,
            "ok": False,
            "status": "unreachable",
            "url": url,
            "error": str(error),
        }


def env_has_value(name):
    value = os.environ.get(name, "")
    if not value:
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8-sig").splitlines():
                if line.startswith(f"{name}="):
                    value = line.split("=", 1)[1].strip()
                    break
    return bool(value)


def main():
    init_database()
    checks = [
        check_path(REPO_ROOT / ".venv" / "Scripts" / "python.exe", "project python venv"),
        check_path(REPO_ROOT / ".env", "local .env", required=False),
        check_path(REPO_ROOT / "data" / "local.db", "local sqlite database", required=False),
        check_path(REPO_ROOT / "knowledge-base", "knowledge base directory"),
        check_path(REPO_ROOT / "knowledge-base" / "daily", "daily notes directory"),
        check_path(REPO_ROOT / "knowledge-base" / "projects", "project notes directory"),
        check_path(REPO_ROOT / "knowledge-base" / "templates" / "project-note.md", "project note template"),
        check_path(REPO_ROOT / "apps" / "web" / "node_modules" / ".bin" / "next.cmd", "Next.js command shim"),
        check_path(REPO_ROOT / "apps" / "web" / "node_modules" / "next" / "index.d.ts", "Next.js type definitions"),
        check_path(
            REPO_ROOT / "apps" / "web" / "node_modules" / "@next" / "swc-wasm-nodejs" / "wasm.js",
            "Next.js wasm SWC fallback",
        ),
        check_url("http://127.0.0.1:8000/health", "API health"),
        check_url("http://127.0.0.1:3100", "Web workspace"),
    ]
    checks.append(
        {
            "name": "Feishu webhook configured",
            "ok": env_has_value("FEISHU_WEBHOOK_URL"),
            "status": "configured" if env_has_value("FEISHU_WEBHOOK_URL") else "missing",
        }
    )

    ok_count = sum(1 for check in checks if check["ok"])
    required_check_names = {
        "project python venv",
        "knowledge base directory",
        "daily notes directory",
        "project notes directory",
        "project note template",
        "Next.js command shim",
        "Next.js type definitions",
        "Next.js wasm SWC fallback",
    }
    required_checks_ok = all(
        check["ok"] for check in checks if check["name"] in required_check_names
    )
    result = {
        "ok": required_checks_ok,
        "ok_count": ok_count,
        "total": len(checks),
        "database": database_status(),
        "checks": checks,
        "notes": [
            "API/Web checks are expected to be unreachable until scripts/start_local.ps1 or scripts/start_local.cmd is running.",
            "If Web dependency checks fail, run scripts/install_web_deps.cmd.",
        ],
    }
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
