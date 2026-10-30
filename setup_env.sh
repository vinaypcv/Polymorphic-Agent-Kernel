#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== [PAK ENGINE] Starting Automated E2E Verification Setup ===${NC}"

if command -v py &> /dev/null; then
    PYTHON_BIN="py -3"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
elif command -v python &> /dev/null; then
    PYTHON_BIN="python"
else
    echo -e "${RED}Error: Python is not installed or not added to PATH.${NC}"
    exit 1
fi

echo -e "[PAK Engine] Using Python interpreter: ${GREEN}$PYTHON_BIN${NC}"

if [ -d ".venv" ]; then
    rm -rf .venv
fi

$PYTHON_BIN -m venv .venv

if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

python -m pip install --upgrade pip
pip install maturin pydantic pytest trio

maturin develop --release

PYTHONPATH=. pytest -v tests/test_kernel.py
echo -e "${GREEN}[SUCCESS] All system parameters verified cleanly.${NC}"