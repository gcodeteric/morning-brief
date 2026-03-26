"""SimulaNewsMachine — Windows-first dashboard launcher helper."""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from config import OUTPUT_FILE
from dashboard_data import CARDS_DIR
from dashboard_overrides import ensure_overrides_file

PROJECT_ROOT = Path(__file__).resolve().parent
DASHBOARD_APP = PROJECT_ROOT / "dashboard_app.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
DEFAULT_TIMEOUT_SECONDS = 45


def build_dashboard_url(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    return f"http://{host}:{port}/"


def is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def is_dashboard_ready(url: str, timeout_seconds: float = 1.5) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": "SimulaLauncher/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return 200 <= getattr(response, "status", 200) < 500
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 500
    except Exception:
        return False


def wait_for_dashboard(
    url: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    poll_interval: float = 0.5,
    process: subprocess.Popen | None = None,
) -> bool:
    deadline = time.time() + max(timeout_seconds, 1.0)
    while time.time() < deadline:
        if is_dashboard_ready(url):
            return True
        if process is not None and process.poll() is not None:
            return False
        time.sleep(max(poll_interval, 0.1))
    return False


def start_streamlit_dashboard(
    python_executable: str | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> subprocess.Popen:
    python_executable = python_executable or sys.executable
    command = [
        python_executable,
        "-m",
        "streamlit",
        "run",
        str(DASHBOARD_APP),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    return subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def open_local_path(path_like) -> tuple[bool, str]:
    try:
        path = Path(path_like)
        if not path.exists():
            return False, f"Caminho não existe: {path}"
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True, str(path)
    except Exception as exc:
        return False, str(exc)


def resolve_operational_target(name: str) -> Path:
    mapping = {
        "overrides": ensure_overrides_file(),
        "brief-folder": OUTPUT_FILE.parent,
        "cards-folder": CARDS_DIR,
        "project-root": PROJECT_ROOT,
    }
    return Path(mapping[name])


def open_browser_when_ready(
    python_executable: str | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    open_browser_flag: bool = True,
) -> int:
    if not DASHBOARD_APP.exists():
        print(f"ERRO: dashboard_app.py não foi encontrado em {DASHBOARD_APP}")
        return 1

    url = build_dashboard_url(host, port)
    print(f"Dashboard target: {url}")

    if is_dashboard_ready(url):
        print("Dashboard já está online.")
        if open_browser_flag:
            if webbrowser.open(url):
                print("Browser aberto com sucesso.")
            else:
                print(f"Não foi possível abrir o browser automaticamente. Abre manualmente: {url}")
        return 0

    if is_port_in_use(host, port):
        print(f"ERRO: a porta {port} já está ocupada, mas o dashboard não respondeu como pronto.")
        print(f"Confirma se já existe outra instância e tenta abrir manualmente: {url}")
        return 1

    try:
        process = start_streamlit_dashboard(python_executable=python_executable, host=host, port=port)
    except Exception as exc:
        print(f"ERRO: não foi possível arrancar o dashboard: {exc}")
        return 1

    print("A iniciar o dashboard...")
    print("A aguardar readiness local antes de abrir o browser...")
    ready = wait_for_dashboard(url, timeout_seconds=timeout_seconds, process=process)
    if not ready:
        print("ERRO: o dashboard não ficou pronto dentro do tempo esperado.")
        print(f"URL esperada: {url}")
        return 1

    print("Dashboard online.")
    if open_browser_flag:
        if webbrowser.open(url):
            print("Browser aberto depois da readiness check.")
        else:
            print(f"Não foi possível abrir o browser automaticamente. Abre manualmente: {url}")
    else:
        print(f"Browser automático desactivado. Abre manualmente: {url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SimulaNewsMachine dashboard launcher helper")
    subparsers = parser.add_subparsers(dest="command")

    dashboard_parser = subparsers.add_parser("dashboard", help="Arranca o dashboard e abre o browser quando estiver pronto")
    dashboard_parser.add_argument("--host", default=DEFAULT_HOST)
    dashboard_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    dashboard_parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    dashboard_parser.add_argument("--no-browser", action="store_true")

    open_parser = subparsers.add_parser("open", help="Abre um alvo operacional local")
    open_parser.add_argument("target", choices=["overrides", "brief-folder", "cards-folder", "project-root"])

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "dashboard"

    if command == "dashboard":
        return open_browser_when_ready(
            python_executable=sys.executable,
            host=args.host,
            port=args.port,
            timeout_seconds=args.timeout,
            open_browser_flag=not args.no_browser,
        )

    if command == "open":
        path = resolve_operational_target(args.target)
        if args.target == "cards-folder" and not path.exists():
            print(f"Cards folder ainda não existe: {path}")
            return 1
        ok, message = open_local_path(path)
        if ok:
            print(f"Aberto: {message}")
            return 0
        print(f"ERRO: {message}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
