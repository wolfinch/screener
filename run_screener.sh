#!/usr/bin/env bash
# run_screener.sh — launch the Wolfinch Screener via uv
#
# Usage:
#   ./run_screener.sh --config config/screener.yml [options]
#   ./run_screener.sh --config config/screener.yml --clean
#   ./run_screener.sh --config config/screener.yml --port 8080
#
# Wolfinch shared packages (utils, yahoofin, nasdaq, robinhood exchange)
# are plain source directories without their own pyproject.toml, so they  
# are added to PYTHONPATH here rather than as uv path dependencies.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WOLFINCH_DIR="$(cd "${SCRIPT_DIR}/../wolfinch" && pwd)"

export PYTHONPATH="${WOLFINCH_DIR}/pkgs:${WOLFINCH_DIR}/exchanges:${WOLFINCH_DIR}:${PYTHONPATH:-}"

exec uv run --project "${SCRIPT_DIR}" python screener.py "$@"
