"""Recon — Forward Deployed Engineer (FDE) Bulletproof Quick Launcher.

Zero-friction, self-healing environment verification, dependency resolution,
health check, and web studio launcher for any operating system (Windows, macOS, Linux).

Usage:
    python scripts/fde_launcher.py
    python scripts/fde_launcher.py --host 0.0.0.0 --port 8000
    python scripts/fde_launcher.py --no-browser
"""

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

# Ensure repository root and 'src' directory are on sys.path regardless of execution directory
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Terminal color formatting (ANSI with safe fallback)
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
BOLD = "\033[1m" if USE_COLOR else ""
GREEN = "\033[32m" if USE_COLOR else ""
CYAN = "\033[36m" if USE_COLOR else ""
YELLOW = "\033[33m" if USE_COLOR else ""
RED = "\033[31m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""


def check_python_version() -> bool:
    """Verifies that the Python runtime meets the minimum 3.11 requirement."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        print(f"{RED}[FAIL] Python 3.11+ is required. Found: {sys.version.split()[0]}{RESET}")
        print(f"       Please install Python 3.11 or newer from: https://www.python.org/downloads/")
        return False
    arch = "64-bit" if sys.maxsize > 2**32 else "32-bit"
    print(f"{GREEN}[PASS] Python Runtime: {sys.version.split()[0]} ({arch}){RESET}")
    return True


def check_and_heal_dependencies() -> bool:
    """Verifies and automatically self-installs missing dependencies in-place."""
    core_modules = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "python-multipart": "multipart",
    }
    missing_pkgs = []
    for pkg_name, import_mod in core_modules.items():
        try:
            __import__(import_mod)
        except ImportError:
            missing_pkgs.append(pkg_name)

    # Check if recon module itself imports
    try:
        import recon
    except ImportError:
        missing_pkgs.append("recon (local package)")

    if not missing_pkgs:
        print(f"{GREEN}[PASS] Core Dependencies: FastAPI, Uvicorn, Pydantic v2, Python-Multipart installed{RESET}")
        return True

    print(f"{YELLOW}[WARN] Missing required dependencies: {', '.join(missing_pkgs)}{RESET}")
    print(f"{CYAN}       Self-healing environment: Installing package and dependencies in editable mode...{RESET}")

    install_cmd = [sys.executable, "-m", "pip", "install", "-e", str(REPO_ROOT)]
    res = subprocess.run(install_cmd)
    if res.returncode == 0:
        print(f"{GREEN}[PASS] Dependencies and Recon package successfully installed.{RESET}")
        return True

    # Fallback to requirements.txt
    req_file = REPO_ROOT / "requirements.txt"
    if req_file.is_file():
        print(f"{YELLOW}[WARN] Editable install had issues; falling back to requirements.txt...{RESET}")
        res2 = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        if res2.returncode == 0:
            print(f"{GREEN}[PASS] Dependencies installed from requirements.txt.{RESET}")
            return True

    print(f"{RED}[FAIL] Automatic dependency installation failed. Please run:{RESET}")
    print(f"       pip install -r requirements.txt")
    return False


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a local TCP port is already occupied."""
    bind_target = "127.0.0.1" if host in ("0.0.0.0", "") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((bind_target, port)) == 0


def verify_existing_recon(port: int, host: str = "127.0.0.1") -> bool:
    """Probes /api/health to confirm if an active process on port is indeed Recon."""
    check_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
    try:
        url = f"http://{check_host}:{port}/api/health"
        req = urllib.request.Request(url, headers={"User-Agent": "Recon-Launcher"})
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok" and "Recon" in data.get("engine", "")
    except Exception:
        return False


def resolve_available_port(desired_port: int, host: str = "127.0.0.1") -> tuple[int, bool]:
    """Resolves an open port or identifies an existing active Recon session.

    Returns:
        tuple[int, bool]: (resolved_port, is_already_recon)
    """
    if not is_port_in_use(desired_port, host):
        return desired_port, False

    # Check if the active process is Recon
    if verify_existing_recon(desired_port, host):
        return desired_port, True

    # Port is occupied by a foreign application; auto-find next open port
    print(f"{YELLOW}[WARN] Port {desired_port} is in use by another program.{RESET}")
    for candidate in range(desired_port + 1, desired_port + 25):
        if not is_port_in_use(candidate, host):
            print(f"{CYAN}[INFO] Auto-selected available port {candidate} for Recon Web Studio.{RESET}")
            return candidate, False

    return desired_port, False


def banner(host: str, port: int) -> None:
    """Displays the FDE launch banner."""
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{display_host}:{port}"
    print("\n" + "=" * 68)
    print(f"{BOLD}{CYAN}  RECON — FORWARD DEPLOYED ENGINEER (FDE) LAUNCHER{RESET}")
    print(f"  {YELLOW}The Integration Readiness Engine (Production Grade){RESET}")
    print("=" * 68)
    print(f"  Target Studio URL : {BOLD}{GREEN}{url}{RESET}")
    print(f"  Execution Mode    : Local-First (Zero Cloud Dependencies / Air-Gapped)")
    print(f"  Sample Fixtures   : examples/sample_raw_feed.csv -> examples/sample_target_schema.json")
    print(f"  Diagnostic Doctor : python -m recon.cli doctor")
    print("=" * 68 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recon FDE Quick Launcher")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Initial port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    # Step 1: Preflight Environment Checks
    print(f"\n{BOLD}[1/3] Checking FDE Runtime Environment...{RESET}")
    if not check_python_version() or not check_and_heal_dependencies():
        return 1

    # Step 2: Port Availability & Conflict Resolution
    print(f"\n{BOLD}[2/3] Checking Network Port Availability...{RESET}")
    active_port, is_already_recon = resolve_available_port(args.port, args.host)

    display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    url = f"http://{display_host}:{active_port}"

    if is_already_recon:
        print(f"{YELLOW}[INFO] Recon Web Studio is already actively serving on {url}.{RESET}")
        print(f"{GREEN}       Connecting to existing active session.{RESET}")
        if not args.no_browser:
            webbrowser.open(url)
        return 0

    print(f"{GREEN}[PASS] Port {active_port} is ready for binding.{RESET}")

    # Step 3: Launch Web Studio
    print(f"\n{BOLD}[3/3] Launching Recon Web Studio...{RESET}")
    banner(args.host, active_port)

    if not args.no_browser:
        # Give uvicorn 1 second to start serving before opening browser
        import threading

        def open_tab():
            time.sleep(1.0)
            webbrowser.open(url)

        threading.Thread(target=open_tab, daemon=True).start()

    try:
        import uvicorn
        from recon.server.app import create_app

        app = create_app()
        uvicorn.run(app, host=args.host, port=active_port, log_level="info")
        return 0
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INFO] Recon Web Studio stopped cleanly by user.{RESET}")
        return 0
    except Exception as exc:
        print(f"\n{RED}[FATAL] Could not start server: {exc}{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
