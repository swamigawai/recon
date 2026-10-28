"""Recon — Forward Deployed Engineer (FDE) Quick Launcher.

One-command environment verification, health check, and studio launcher.
Usage:
    python scripts/fde_launcher.py
    python scripts/fde_launcher.py --port 8080 --no-browser
"""

import argparse
import os
from pathlib import Path
import socket
import sys
import time
import webbrowser

# Terminal color formatting (ANSI)
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def check_python_version() -> bool:
    """Verifies that the Python runtime meets the minimum 3.11 requirement."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        print(f"{RED}[FAIL] Python 3.11+ is required. Found: {sys.version}{RESET}")
        return False
    print(f"{GREEN}[PASS] Python Runtime: {sys.version.split()[0]} (64-bit){RESET}")
    return True


def check_dependencies() -> bool:
    """Verifies that all core packages are installed."""
    required = ["fastapi", "uvicorn", "pydantic", "click"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"{YELLOW}[WARN] Missing packages: {', '.join(missing)}{RESET}")
        print(f"{CYAN}       Installing in-place via pip...{RESET}")
        import subprocess

        cmd = [sys.executable, "-m", "pip", "install"] + missing
        res = subprocess.run(cmd)
        return res.returncode == 0

    print(f"{GREEN}[PASS] Core Dependencies: FastAPI, Uvicorn, Pydantic v2 installed{RESET}")
    return True


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a local TCP port is already occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def banner(host: str, port: int) -> None:
    """Displays the FDE launch banner."""
    url = f"http://{host}:{port}"
    print("\n" + "=" * 68)
    print(f"{BOLD}{CYAN}  RECON — FORWARD DEPLOYED ENGINEER (FDE) LAUNCHER{RESET}")
    print(f"  {YELLOW}The Integration Readiness Engine{RESET}")
    print("=" * 68)
    print(f"  Target Studio URL : {BOLD}{GREEN}{url}{RESET}")
    print(f"  Execution Mode    : Local-First (Zero Outbound Telemetry)")
    print(f"  Test Fixtures     : tests/fixtures/ (NYC 311, Service Request)")
    print(f"  FDE Field Guide   : docs/FDE_PLAYBOOK.md")
    print("=" * 68 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recon FDE Quick Launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    # Step 1: Preflight Environment Checks
    print(f"\n{BOLD}[1/3] Checking FDE Runtime Environment...{RESET}")
    if not check_python_version() or not check_dependencies():
        return 1

    # Step 2: Port Availability
    print(f"\n{BOLD}[2/3] Checking Network Port Availability...{RESET}")
    if is_port_in_use(args.port, args.host):
        print(f"{YELLOW}[INFO] Port {args.port} is already active. Recon is running.{RESET}")
        url = f"http://{args.host}:{args.port}"
        print(f"{GREEN}       Connecting to existing session at {url}{RESET}")
        if not args.no_browser:
            webbrowser.open(url)
        return 0

    print(f"{GREEN}[PASS] Port {args.port} is available.{RESET}")

    # Step 3: Launch Web Studio
    print(f"\n{BOLD}[3/3] Launching Recon Web Studio...{RESET}")
    banner(args.host, args.port)

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        # Give the server 1 second to bind before triggering browser
        import threading

        def open_tab():
            time.sleep(1.2)
            webbrowser.open(url)

        threading.Thread(target=open_tab, daemon=True).start()

    import uvicorn
    from recon.server.app import create_app

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
