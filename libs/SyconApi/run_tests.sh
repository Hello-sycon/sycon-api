#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run_tests.sh [pytest args...]
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

if [ ! -f pyproject.toml ]; then
  echo "ERROR: pyproject.toml not found. Lance le script depuis la racine du repo." >&2
  exit 1
fi

VENV_DIR=".venv"
PYTHON_CMD="${PYTHON:-python3}"

echo ">>> Using Python: $($PYTHON_CMD --version 2>&1 | tr -d '\n')"
# create venv if missing
if [ ! -d "$VENV_DIR" ]; then
  echo ">>> Creating virtualenv in $VENV_DIR ..."
  $PYTHON_CMD -m venv "$VENV_DIR"
fi

# activate venv
# shellcheck source=/dev/null
. "$VENV_DIR/bin/activate"

echo ">>> Upgrading pip / setuptools / wheel ..."
pip install -U pip setuptools wheel >/dev/null

echo ">>> Installing package editable (pip install -e .) ..."
if pip install -e . >/dev/null 2>&1; then
  echo ">>> Package installed editable."
else
  echo ">>> Warning: pip install -e . failed — falling back to PYTHONPATH=src"
  export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"
fi

echo ">>> Installing test deps (pytest, pytest-cov, requests-mock) ..."
pip install -U pytest pytest-cov requests-mock >/dev/null

# run pytest with coverage; forward any user args
PYTEST_ARGS=( --cov=sycon_api --cov-report=term-missing --cov-report=html -q )
if [ "$#" -ne 0 ]; then
  PYTEST_ARGS+=( "$@" )
fi

echo ">>> Running pytest ..."
pytest "${PYTEST_ARGS[@]}"
EXIT_CODE=$?

echo
echo ">>> Done. Coverage HTML report: $REPO_ROOT/htmlcov/index.html"
echo ">>> Return code: $EXIT_CODE"
exit $EXIT_CODE
