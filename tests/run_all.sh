#!/usr/bin/env bash
# Run every automatic test, each with the Python it needs. Sends no real input to any app.
# test_mac_gui.py opens one throwaway window that cannot take focus.
#
# Usage: tests/run_all.sh
# Exit 1 if a test fails. A test whose tool is not installed counts as SKIP and does not fail.
# Audacity venv override: AUDACITY_PY=/path/to/python tests/run_all.sh
set -uo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
audacity_py="${AUDACITY_PY:-$HOME/Audacity4-MCP/.venv/bin/python}"
failed=0

check() {
  local name="$1"
  shift
  echo "=== $name"
  if "$@"; then
    echo "PASS $name"
  else
    echo "FAIL $name"
    failed=1
  fi
}

check lint_skills python3 "$repo/tests/lint_skills.py"
check check_public python3 "$repo/tests/check_public.py"
check test_scripts python3 "$repo/tests/test_scripts.py"
check test_ignite_mcp python3 "$repo/tests/test_ignite_mcp.py"

if command -v uv >/dev/null; then
  check test_mac_gui uv run --directory "$repo/mcp/mac-gui" --frozen python "$repo/tests/test_mac_gui.py"
else
  echo "SKIP test_mac_gui: uv not found"
fi

if [ -x "$audacity_py" ]; then
  check test_audacity_mcp "$audacity_py" "$repo/tests/test_audacity_mcp.py"
else
  echo "SKIP test_audacity_mcp: no Python at $audacity_py"
fi

if [ "$failed" -ne 0 ]; then
  echo "Some tests failed."
  exit 1
fi
echo "All tests that ran passed."
