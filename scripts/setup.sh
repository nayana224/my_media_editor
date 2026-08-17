#!/usr/bin/env bash
        if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
          echo "setup.sh는 source하지 말고 './scripts/setup.sh'로 실행해 주세요."
          return 1
        fi

        set -euo pipefail

        PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

        echo "[1/4] Installing Ubuntu packages..."
        sudo apt update
        sudo apt install -y ffmpeg python3-venv

        echo "[2/4] Creating Python virtual environment..."
        if [[ ! -d "${PROJECT_ROOT}/.venv" ]]; then
          python3 -m venv "${PROJECT_ROOT}/.venv"
        else
          echo "Reusing existing virtual environment."
        fi

        echo "[3/4] Installing Media Editor..."
        "${PROJECT_ROOT}/.venv/bin/python" -m pip install --upgrade pip
        "${PROJECT_ROOT}/.venv/bin/python" -m pip install -e "${PROJECT_ROOT}"

        echo "[4/4] Done."
        echo "Run: ${PROJECT_ROOT}/scripts/run.sh"
