#!/usr/bin/env bash
set -euo pipefail

VCAN_IF="vcan0"
PYTHON_SCRIPT="can_bus.py"
PYTHON_CMD="python3"

# -------------------------
# Cleanup handler
# -------------------------
cleanup() {
    echo ""
    echo "[*] Shutting down..."

    if [[ -n "${PY_PID:-}" ]] && kill -0 "$PY_PID" 2>/dev/null; then
        echo "[*] Stopping Python program (PID $PY_PID)"
        kill "$PY_PID"
        wait "$PY_PID" 2>/dev/null || true
    fi

    if ip link show "$VCAN_IF" &>/dev/null; then
        echo "[*] Bringing down $VCAN_IF"
        sudo ip link set down "$VCAN_IF" || true
        echo "[*] Removing $VCAN_IF"
        sudo ip link delete "$VCAN_IF" || true
    fi

    if lsmod | grep -q "^vcan"; then
        echo "[*] Unloading vcan module"
        sudo modprobe -r vcan || true
    fi

    echo "[*] Cleanup complete"
}

trap cleanup EXIT INT TERM

# -------------------------
# Setup
# -------------------------
echo "[*] Loading vcan module"
sudo modprobe vcan

if ! ip link show "$VCAN_IF" &>/dev/null; then
    echo "[*] Creating $VCAN_IF"
    sudo ip link add dev "$VCAN_IF" type vcan
fi

echo "[*] Bringing up $VCAN_IF"
sudo ip link set up "$VCAN_IF"

# -------------------------
# Start Python program
# -------------------------
echo "[*] Starting Python program"
$PYTHON_CMD "$PYTHON_SCRIPT" &
PY_PID=$!

echo "[*] Python running with PID $PY_PID"
echo "[*] Press Ctrl+C to stop"

# -------------------------
# Wait
# -------------------------
wait "$PY_PID"
