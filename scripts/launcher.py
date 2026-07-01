#!/usr/bin/env python3
"""One-click launcher: optional ComfyUI + Monster AI."""
from __future__ import annotations

import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_node_api_proc: subprocess.Popen | None = None


def _load_settings():
    sys.path.insert(0, str(ROOT))
    from monster_ai.config import load_settings

    return load_settings()


def _comfyui_online(url: str) -> bool:
    try:
        import httpx

        r = httpx.get(f"{url.rstrip('/')}/system_stats", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _resolve_comfyui_path(configured: str) -> Path | None:
    if configured in ("", "disabled", "off", "none"):
        return None
    if configured and configured != "auto":
        p = Path(configured)
        if (p / "run_nvidia_gpu.bat").exists():
            return p
        portable = p / "ComfyUI_windows_portable_nvidia" / "ComfyUI_windows_portable"
        if (portable / "run_nvidia_gpu.bat").exists():
            return portable
        return p if p.exists() else None
    sys.path.insert(0, str(ROOT / "scripts"))
    from detect_comfyui import find_comfyui

    return find_comfyui()


def _start_comfyui_windows(comfy_path: Path, *, headless: bool = True) -> None:
    if headless:
        sys.path.insert(0, str(ROOT / "scripts"))
        from comfyui_headless import comfyui_display_name, start_comfyui_headless

        log = ROOT / "data" / "logs" / "comfyui.log"
        start_comfyui_headless(comfy_path, log)
        print(f"Started {comfyui_display_name(comfy_path)} — log: {log}")
        return

    bat = comfy_path / "run_nvidia_gpu.bat"
    if not bat.exists():
        raise FileNotFoundError(f"run_nvidia_gpu.bat not found in {comfy_path}")
    subprocess.Popen(
        'start "ComfyUI" cmd /k run_nvidia_gpu.bat',
        cwd=str(comfy_path),
        shell=True,
    )
    print("Launched ComfyUI in console window (headless disabled)")


def _start_comfyui_unix(comfy_path: Path) -> None:
    main_py = comfy_path / "main.py"
    if not main_py.exists():
        main_py = comfy_path / "ComfyUI" / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(f"No ComfyUI main.py in {comfy_path}")
    log = ROOT / "data" / "logs" / "comfyui.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        subprocess.Popen(
            [sys.executable, str(main_py), "--listen", "127.0.0.1", "--port", "8188"],
            cwd=str(main_py.parent),
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def _wait_comfyui(url: str, timeout: int) -> bool:
    print(f"Waiting for ComfyUI at {url} (timeout {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _comfyui_online(url):
            print("ComfyUI is online.")
            return True
        time.sleep(2)
    return False


def _needs_comfyui(settings) -> bool:
    if not settings.launcher.comfyui_enabled:
        return False
    return settings.modules.image.enabled or settings.modules.video.enabled


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _node_api_cmd() -> list[str] | None:
    """Start tsx directly — avoids pnpm.ps1 PowerShell execution-policy failures."""
    if sys.platform == "win32":
        tsx_bin = ROOT / "node_modules" / ".bin" / "tsx.cmd"
        if tsx_bin.is_file():
            return [str(tsx_bin), "server/_core/index.ts"]
    tsx_cli = ROOT / "node_modules" / "tsx" / "dist" / "cli.mjs"
    if tsx_cli.is_file() and _which("node"):
        return ["node", str(tsx_cli), "server/_core/index.ts"]
    pnpm = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
    if _which(pnpm):
        return [pnpm, "exec", "tsx", "server/_core/index.ts"]
    return None


def _react_build_paths() -> tuple[Path, Path]:
    return ROOT / "dist" / "public" / "index.html", ROOT / "client"


def _react_build_stale() -> bool:
    index, client_dir = _react_build_paths()
    if not index.is_file():
        return True
    build_mtime = index.stat().st_mtime
    for pattern in ("**/*.tsx", "**/*.ts", "**/*.css"):
        for src in client_dir.glob(pattern):
            if src.stat().st_mtime > build_mtime:
                return True
    return False


def _run_vite_build() -> bool:
    index, _ = _react_build_paths()
    pnpm = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
    if not _which(pnpm):
        print("WARNING: pnpm not found — React UI build skipped; using legacy static UI.")
        return False
    if not (ROOT / "node_modules").is_dir():
        print("Installing frontend dependencies for React UI...")
        r = subprocess.run([pnpm, "install"], cwd=str(ROOT), shell=False)
        if r.returncode != 0:
            print("WARNING: pnpm install failed — using legacy static UI.")
            return False
    print("Building React Web UI (may take a minute)...")
    r = subprocess.run(
        [pnpm, "exec", "vite", "build"],
        cwd=str(ROOT),
        shell=False,
    )
    if r.returncode != 0:
        print("WARNING: vite build failed — using legacy static UI.")
        return False
    return index.is_file()


def _ensure_react_build() -> bool:
    index, _ = _react_build_paths()
    if index.is_file() and not _react_build_stale():
        return True
    if index.is_file():
        print("React UI source changed — rebuilding dist/public...")
    return _run_vite_build()


def _probe_react_ui_served(host: str, port: int) -> bool:
    if not _port_open(host, port):
        return False
    try:
        import httpx

        r = httpx.get(f"http://{host}:{port}/", timeout=3, follow_redirects=True)
        if r.status_code != 200:
            return False
        body = r.text
        if 'id="root"' in body and "/assets/" in body:
            return True
        if "style.css" in body and "monsterlock-badge" in body:
            return False
        return 'id="root"' in body
    except Exception:
        return False


def _stop_node_api() -> None:
    global _node_api_proc
    proc = _node_api_proc
    _node_api_proc = None
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _probe_node_api(port: int) -> bool:
    if not _port_open("127.0.0.1", port):
        return False
    probe = f"http://127.0.0.1:{port}/api/trpc/auth.me"
    try:
        import httpx

        r = httpx.get(
            probe,
            params={
                "batch": "1",
                "input": json.dumps({"0": {"json": None}}),
            },
            timeout=3,
        )
        return r.status_code == 200 and bool(r.text.strip())
    except Exception:
        return False


def _probe_node_api_with_retries(port: int, *, attempts: int = 4, delay: float = 1.0) -> bool:
    for attempt in range(attempts):
        if _probe_node_api(port):
            return True
        if attempt + 1 < attempts:
            time.sleep(delay)
    return False


def _discover_node_api_port(preferred: int, span: int = 10) -> int | None:
    """Find an already-running Monster tRPC API (e.g. leftover pnpm dev on :3001)."""
    for port in range(preferred, preferred + span):
        if _probe_node_api_with_retries(port, attempts=2, delay=0.5):
            return port
    return None


def _wait_node_api(port: int, timeout: int = 45) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _probe_node_api(port):
            return True
        time.sleep(1)
    return False


def _pid_is_windows_service(pid: int) -> bool:
    if sys.platform != "win32":
        return False
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "Services" in r.stdout or "Service" in r.stdout
    except Exception:
        return False


def _port_held_by_windows_service(port: int) -> bool:
    for pid in _pids_on_port(port):
        if _pid_is_windows_service(pid):
            return True
    return False


def _print_service_port_hint(port: int) -> None:
    if _port_held_by_windows_service(port):
        print(
            f"Port {port} is held by Windows Service MonsterAIService "
            "(legacy HTML UI)."
        )
        print(
            "Right-click scripts\\stop-service.bat -> Run as administrator, "
            "then run run.bat again."
        )


def _pids_on_port(port: int) -> list[int]:
    pids: list[int] = []
    try:
        r = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
        needle = f":{port}"
        for line in r.stdout.splitlines():
            if "LISTENING" not in line or needle not in line:
                continue
            parts = line.split()
            if not parts:
                continue
            pid = parts[-1]
            if pid.isdigit():
                pids.append(int(pid))
    except Exception:
        return []
    return list(dict.fromkeys(pids))


def _free_port(port: int, *, attempts: int = 3) -> bool:
    for _ in range(attempts):
        freed = False
        for pid in _pids_on_port(port):
            if pid <= 0:
                continue
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/F"],
                        capture_output=True,
                        check=False,
                    )
                else:
                    subprocess.run(
                        ["kill", "-9", str(pid)], capture_output=True, check=False
                    )
                freed = True
            except Exception:
                continue
        if freed:
            time.sleep(2.0)
        if not _port_open("127.0.0.1", port):
            return True
    return not _port_open("127.0.0.1", port)


def _start_node_api(port: int) -> int:
    global _node_api_proc
    if not (ROOT / "node_modules").is_dir():
        print("Installing Node dependencies...")
        pnpm = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        installer = pnpm if _which(pnpm) else npm if _which(npm) else None
        if not installer:
            print("ERROR: Node.js not found. Install Node.js 20+ and run npm install.")
            return 0
        r = subprocess.run([installer, "install"], cwd=str(ROOT), shell=False)
        if r.returncode != 0:
            print(f"ERROR: {installer} install failed.")
            return 0
    node_cmd = _node_api_cmd()
    if not node_cmd:
        print("ERROR: tsx not found. Run npm install in the project root.")
        return 0

    discovered = _discover_node_api_port(port)
    if discovered is not None:
        os.environ["NODE_API_URL"] = f"http://127.0.0.1:{discovered}"
        if discovered == port:
            print(f"Node tRPC API already running on :{port} — reusing it.")
        else:
            print(
                f"Node tRPC API already running on :{discovered} — reusing it "
                f"(configured port :{port} was busy)."
            )
        return discovered

    if _port_open("127.0.0.1", port):
        print(
            f"Port {port} is in use but not responding as Monster tRPC API. "
            "Trying to free the port..."
        )
        if not _free_port(port):
            print(
                f"ERROR: Port {port} is already in use. "
                "Close other Monster AI / pnpm dev windows and run run.bat again."
            )
            print("Or run: scripts\\stop-dev.bat")
            return 0
        print(f"Port {port} freed.")

    log = ROOT / "data" / "logs" / "node-api.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["API_ONLY"] = "1"
    env["NODE_ENV"] = "development"
    env["NODE_API_URL"] = f"http://127.0.0.1:{port}"

    with log.open("a", encoding="utf-8") as log_file:
        _node_api_proc = subprocess.Popen(
            node_cmd,
            cwd=str(ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    atexit.register(_stop_node_api)

    print(f"Starting Node tRPC API on :{port} (log: {log})")
    if not _wait_node_api(port):
        print("ERROR: Node tRPC API did not become ready in time. See data/logs/node-api.log")
        _stop_node_api()
        return 0
    print("Node tRPC API is ready.")
    os.environ["NODE_API_URL"] = f"http://127.0.0.1:{port}"
    return port


def _probe_monster_ai_web(host: str, port: int) -> bool:
    if not _port_open(host, port):
        return False
    probe = f"http://{host}:{port}/health"
    try:
        import httpx

        r = httpx.get(probe, timeout=3)
        if r.status_code != 200:
            return False
        data = r.json()
        return data.get("status") == "ok"
    except Exception:
        return False


def _prepare_monster_ai_web(host: str, port: int, *, want_react: bool) -> str:
    """Return 'reuse', 'start', or 'fail'."""
    if _probe_monster_ai_web(host, port):
        if want_react and (ROOT / "dist" / "public" / "index.html").is_file():
            if not _probe_react_ui_served(host, port):
                print(
                    f"Port {port} is running legacy HTML UI. "
                    "Restarting to serve React Web UI from dist/public..."
                )
                if not _free_port(port):
                    print(
                        f"ERROR: Could not restart Python on :{port}."
                    )
                    _print_service_port_hint(port)
                    print("Or run scripts\\stop-dev.bat, then run run.bat again.")
                    return "fail"
                return "start"
        return "reuse"
    if _port_open(host, port):
        print(
            f"Port {port} is in use but not responding as Monster AI. "
            "Trying to free the port..."
        )
        if not _free_port(port):
            print(
                f"ERROR: Port {port} is already in use. "
                "Close other Monster AI windows and run run.bat again."
            )
            _print_service_port_hint(port)
            print("Or run: scripts\\stop-dev.bat")
            return "fail"
        print(f"Port {port} freed.")
    return "start"


def _preflight_monster_ai() -> bool:
    """Fail fast before ComfyUI wait if the app cannot import."""
    try:
        sys.path.insert(0, str(ROOT))
        from monster_ai.app import create_app
        from monster_ai.config import load_settings

        create_app(load_settings())
        return True
    except Exception as exc:
        print(f"ERROR: Monster AI failed to load: {exc}")
        print("Fix the error above, then run run.bat again.")
        return False


def main() -> int:
    os.chdir(ROOT)
    if not _preflight_monster_ai():
        return 1

    settings = _load_settings()
    launcher = settings.launcher
    log_dir = ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    comfy_path = _resolve_comfyui_path(launcher.comfyui_path)
    launcher_info: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "comfyui_path": str(comfy_path) if comfy_path else None,
        "comfyui_url": launcher.comfyui_url,
        "auto_start": launcher.auto_start_comfyui,
    }
    comfy_ready = True

    if _needs_comfyui(settings) and launcher.wait_for_comfyui:
        if not _comfyui_online(launcher.comfyui_url):
            if launcher.auto_start_comfyui:
                if not comfy_path:
                    print("WARNING: ComfyUI not found. Set launcher.comfyui_path in config.yaml")
                    print("Monster AI will start, but image/video need ComfyUI.")
                    launcher_info["warning"] = "comfyui_not_found"
                    comfy_ready = False
                else:
                    headless = launcher.comfyui_headless
                    print(f"Auto-starting ComfyUI (headless={headless})")
                    if sys.platform == "win32":
                        _start_comfyui_windows(comfy_path, headless=headless)
                    else:
                        _start_comfyui_unix(comfy_path)
                    if not _wait_comfyui(
                        launcher.comfyui_url, launcher.startup_timeout_seconds
                    ):
                        launcher_info["warning"] = "comfyui_timeout"
                        comfy_ready = False
                        if launcher.block_on_comfyui_timeout:
                            print("ERROR: ComfyUI did not become ready in time.")
                            (log_dir / "launcher.json").write_text(
                                json.dumps({**launcher_info, "error": "comfyui_timeout"}, indent=2),
                                encoding="utf-8",
                            )
                            return 1
                        print(
                            "WARNING: ComfyUI not ready yet — starting Monster AI anyway. "
                            "Wait for the ComfyUI window, then retry generation."
                        )
            else:
                print("ComfyUI offline. Enable launcher.auto_start_comfyui or start headless manually")
                comfy_ready = False
        else:
            print("ComfyUI already running.")

    launcher_info["comfyui_ready"] = comfy_ready

    if launcher.react_ui_enabled:
        _ensure_react_build()
        node_port = launcher.node_api_port
        active_port = _start_node_api(node_port)
        if not active_port:
            return 1
        os.environ["NODE_API_URL"] = f"http://127.0.0.1:{active_port}"
        launcher_info["node_api_port"] = active_port
        launcher_info["react_ui"] = (ROOT / "dist" / "public" / "index.html").is_file()

    (log_dir / "launcher.json").write_text(json.dumps(launcher_info, indent=2), encoding="utf-8")

    url = f"http://{settings.host}:{settings.port}"
    want_react = launcher.react_ui_enabled and (
        ROOT / "dist" / "public" / "index.html"
    ).is_file()
    web_action = _prepare_monster_ai_web(
        settings.host, settings.port, want_react=want_react
    )
    if web_action == "fail":
        return 1
    if web_action == "reuse":
        print(f"Monster AI Web UI already running at {url} — reusing it.")
        print(f"Open this URL in your browser: {url}")
        if launcher.open_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        return 0

    print(f"Starting Monster AI Web UI at {url}")
    print(f"Open this URL in your browser: {url}")
    print("Keep this window open while using Monster AI.")
    if launcher.open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return subprocess.call([sys.executable, str(ROOT / "main.py")])


if __name__ == "__main__":
    sys.exit(main())