r"""Start the local app and open Chrome once it responds. No Docker needed.

Run using .venv\Scripts\python scripts\start_local.py, or the root BAT launcher.
Existing .env settings are preserved. --prepare-only creates a safe local .env.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def prepare_environment() -> bool:
    target = ROOT / ".env"
    if target.exists():
        return False
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    text = text.replace("SECRET_KEY=change-this-secret-key-in-production", "SECRET_KEY=" + secrets.token_urlsafe(48))
    text = text.replace("QDRANT_PATH=\n", "QDRANT_PATH=./data/qdrant\n")
    # Exclusive creation avoids overwriting credentials if another launcher runs.
    try:
        with target.open("x", encoding="utf-8") as stream:
            stream.write(text)
    except FileExistsError:
        return False
    return True


def chrome_executable() -> str | None:
    discovered = shutil.which("chrome") or shutil.which("chrome.exe")
    if discovered:
        return discovered
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if base:
            path = Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            if path.is_file():
                return str(path)
    return None


def open_when_ready(server: subprocess.Popen, url: str, run_id: str) -> None:
    for _ in range(120):
        if server.poll() is not None:
            return
        try:
            with urlopen(url + "/api/health", timeout=1) as response:
                if response.status == 200 and json.load(response).get("instance_id") == run_id:
                    chrome = chrome_executable()
                    if chrome:
                        try:
                            subprocess.Popen([chrome, "--new-tab", url + "/login"])
                        except OSError:
                            print(f"Open Chrome manually: {url}/login", flush=True)
                    else:
                        print(f"Chrome was not found. Open {url}/login in your browser.", flush=True)
                    return
        except (URLError, TimeoutError, OSError, ValueError):
            pass
        time.sleep(0.5)
    print(f"Startup is taking longer than expected. Check the server output: {url}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    os.chdir(ROOT)
    if prepare_environment():
        print("Created .env with a random session secret and local Qdrant storage.")
    os.environ["DEBUG"] = "false"  # Ignore unrelated Windows DEBUG=release.
    try:
        sys.path.insert(0, str(ROOT))
        from config import get_settings
        settings = get_settings()
        import uvicorn  # noqa: F401 - fail before spawning if setup is incomplete
    except ImportError:
        print("Dependencies are missing. Run: .venv\\Scripts\\python -m pip install -r requirements.lock")
        return 1
    if not settings.openai_api_key:
        print("Add OPENAI_API_KEY to .env for document indexing and AI features.")
        print("You can open the app and register without it. Restart after editing .env.")
    if args.prepare_only:
        print("Local configuration is ready. No server or browser was started.")
        return 0
    url = f"http://127.0.0.1:{args.port}"
    print(f"Starting {url}/login. Leave this terminal open; press Ctrl+C to stop.", flush=True)
    run_id = secrets.token_urlsafe(16)
    server_env = os.environ.copy()
    server_env["RESEARCH_RUN_ID"] = run_id
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(args.port)], cwd=ROOT, env=server_env)
    threading.Thread(target=open_when_ready, args=(server, url, run_id), daemon=True).start()
    try:
        return server.wait()
    except KeyboardInterrupt:
        # Ctrl+C is delivered to the child in the same Windows console as well.
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.terminate()
            server.wait(timeout=5)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
