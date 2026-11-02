#!/usr/bin/env bash
# Recon — Zero-Friction Local Launcher for macOS / Linux
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================================"
echo "  RECON — ZERO-FRICTION LOCAL LAUNCHER (macOS / Linux)"
echo "  Automated Environment Verifier, Self-Healer & Web Studio"
echo "======================================================================"
echo ""

# 1. Resolve Python 3.11+ executable
PYTHON_BIN=""
for cmd in python3.11 python3.12 python3.13 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
            PYTHON_BIN="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.11+ is required but was not found on your system."
    echo "Please install Python 3.11+ via brew (macOS) or your Linux package manager:"
    echo "  macOS:         brew install python@3.11"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install -y python3.11 python3.11-venv"
    echo "  Fedora/RHEL:   sudo dnf install -y python3.11"
    exit 1
fi

echo "[1/3] Detected runtime: $($PYTHON_BIN --version)"

# 2. Virtual environment setup (.venv)
if [ ! -d ".venv" ]; then
    echo "[2/3] Setting up isolated virtual environment (.venv)..."
    "$PYTHON_BIN" -m venv .venv || {
        echo "[WARN] Could not create virtualenv. Continuing with system Python..."
    }
fi

if [ -f ".venv/bin/python" ]; then
    ACTIVE_PY=".venv/bin/python"
else
    ACTIVE_PY="$PYTHON_BIN"
fi

# 3. Check and self-heal dependencies
echo "[3/3] Verifying runtime dependencies..."
if ! "$ACTIVE_PY" -c "import recon, fastapi, uvicorn, pydantic, multipart" >/dev/null 2>&1; then
    echo "      Installing Recon dependencies via pip..."
    "$ACTIVE_PY" -m pip install --upgrade pip --quiet || true
    "$ACTIVE_PY" -m pip install -e . --quiet || "$ACTIVE_PY" -m pip install -r requirements.txt --quiet
fi

echo ""
exec "$ACTIVE_PY" scripts/fde_launcher.py "$@"
