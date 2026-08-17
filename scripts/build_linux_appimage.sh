#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${PROJECT_ROOT}/build/package-linux"
DIST_ROOT="${PROJECT_ROOT}/dist"
VENV="${BUILD_ROOT}/venv"
APPDIR="${BUILD_ROOT}/MyMediaEditor.AppDir"
LINUXDEPLOY="${BUILD_ROOT}/linuxdeploy-x86_64.AppImage"
LINUXDEPLOY_VERSION="1-alpha-20251107-1"
DEPLOYMENT_ROOT="${PROJECT_ROOT}/deployment"

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "현재 build script는 Linux x86_64만 지원합니다." >&2
  exit 1
fi

for command in python3 curl patchelf; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "필수 command '${command}'를 찾지 못했습니다." >&2
    if [[ "${command}" == "patchelf" ]]; then
      echo "Ubuntu 22.04에서는 'sudo apt install -y patchelf'로 설치해 주세요." >&2
    fi
    exit 1
  fi
done

rm -rf "${BUILD_ROOT}" "${DEPLOYMENT_ROOT}"
rm -f "${PROJECT_ROOT}/MyMediaEditor.bin" "${PROJECT_ROOT}/deploy_main.bin"
mkdir -p "${BUILD_ROOT}" "${DIST_ROOT}"

python3 -m venv "${VENV}"
"${VENV}/bin/python" -m pip install --upgrade pip
"${VENV}/bin/python" -m pip install -e "${PROJECT_ROOT}"

pushd "${PROJECT_ROOT}" >/dev/null
"${VENV}/bin/pyside6-deploy" \
  "${PROJECT_ROOT}/deploy_main.py" \
  --name MyMediaEditor \
  --extra-modules Multimedia,MultimediaWidgets \
  --force
popd >/dev/null

STANDALONE_BIN=""
for candidate in \
  "${PROJECT_ROOT}/MyMediaEditor.bin" \
  "${PROJECT_ROOT}/deploy_main.bin" \
  "${DEPLOYMENT_ROOT}/MyMediaEditor.bin" \
  "${DEPLOYMENT_ROOT}/deploy_main.bin" \
  "${DEPLOYMENT_ROOT}/MyMediaEditor" \
  "${DEPLOYMENT_ROOT}/deploy_main"; do
  if [[ -f "${candidate}" && -x "${candidate}" ]]; then
    STANDALONE_BIN="${candidate}"
    break
  fi
done

if [[ -z "${STANDALONE_BIN}" && -d "${DEPLOYMENT_ROOT}" ]]; then
  STANDALONE_BIN="$(
    find "${DEPLOYMENT_ROOT}" -maxdepth 2 -type f -perm -u+x -print -quit
  )"
fi

if [[ -z "${STANDALONE_BIN}" ]]; then
  echo "pyside6-deploy 결과 실행 파일을 찾지 못했습니다." >&2
  echo "확인한 대표 경로:" >&2
  echo "  ${PROJECT_ROOT}/MyMediaEditor.bin" >&2
  echo "  ${PROJECT_ROOT}/deploy_main.bin" >&2
  echo "  ${DEPLOYMENT_ROOT}/" >&2
  exit 1
fi

echo "Standalone executable: ${STANDALONE_BIN}"

mkdir -p "${APPDIR}/usr/bin"
install -m 0755 "${STANDALONE_BIN}" "${APPDIR}/usr/bin/MyMediaEditor"

curl -L --fail --retry 3 \
  "https://github.com/linuxdeploy/linuxdeploy/releases/download/${LINUXDEPLOY_VERSION}/linuxdeploy-x86_64.AppImage" \
  -o "${LINUXDEPLOY}"
chmod +x "${LINUXDEPLOY}"

pushd "${DIST_ROOT}" >/dev/null
rm -f ./*.AppImage
APPIMAGE_EXTRACT_AND_RUN=1 "${LINUXDEPLOY}" \
  --appdir "${APPDIR}" \
  --executable "${APPDIR}/usr/bin/MyMediaEditor" \
  --desktop-file "${PROJECT_ROOT}/packaging/linux/MyMediaEditor.desktop" \
  --icon-file "${PROJECT_ROOT}/packaging/linux/my-media-editor.svg" \
  --output appimage

GENERATED="$(find . -maxdepth 1 -type f -name '*.AppImage' -print -quit)"
if [[ -z "${GENERATED}" ]]; then
  echo "AppImage 생성 결과를 찾지 못했습니다." >&2
  exit 1
fi

VERSION="$(
  "${VENV}/bin/python" -c \
    'import tomllib; print(tomllib.load(open("../pyproject.toml", "rb"))["project"]["version"])'
)"
OUTPUT="MyMediaEditor-${VERSION}-x86_64.AppImage"
mv "${GENERATED}" "${OUTPUT}"
chmod +x "${OUTPUT}"
echo "Created: ${DIST_ROOT}/${OUTPUT}"
popd >/dev/null
