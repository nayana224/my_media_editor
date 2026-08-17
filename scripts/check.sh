#!/usr/bin/env bash
        set -euo pipefail

        PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
        PYTHON="${PROJECT_ROOT}/.venv/bin/python"

        if [[ ! -x "${PYTHON}" ]]; then
          PYTHON="python3"
        fi

        PYTHONPATH="${PROJECT_ROOT}/src" "${PYTHON}" -m unittest discover \
          -s "${PROJECT_ROOT}/tests" \
          -v

        PYTHONPATH="${PROJECT_ROOT}/src" "${PYTHON}" -m compileall -q \
          "${PROJECT_ROOT}/src"
