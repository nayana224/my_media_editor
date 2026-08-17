#!/usr/bin/env bash
        set -euo pipefail

        PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

        if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
          echo "가상환경이 없습니다. 먼저 ./scripts/setup.sh를 실행해 주세요." >&2
          exit 1
        fi

        exec "${PROJECT_ROOT}/.venv/bin/python" -m media_editor
