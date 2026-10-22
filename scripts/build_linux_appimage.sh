#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${PROJECT_ROOT}/build/package-linux"
DIST_ROOT="${PROJECT_ROOT}/dist"
VENV="${BUILD_ROOT}/venv"
APPDIR="${BUILD_ROOT}/MyMediaEditor.AppDir"
LINUXDEPLOY="${BUILD_ROOT}/linuxdeploy-x86_64.AppImage"
LINUXDEPLOY_VERSION="1-alpha-20251107-1"
DEPLOYMENT_ROOT="${BUILD_ROOT}/deployment"

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "Linux x86_64만 지원합니다." >&2
  exit 1
fi
for command in python3 curl patchelf gcc; do
  command -v "${command}" >/dev/null || { echo "필수 command: ${command}" >&2; exit 1; }
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "빌드에는 Python 3.11+가 필요합니다.")'

rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}" "${DIST_ROOT}"
python3 -m venv "${VENV}"
"${VENV}/bin/python" -m pip install -e "${PROJECT_ROOT}" -r "${PROJECT_ROOT}/packaging/requirements-build.txt"

# Explicit onefile mode and output path; never guess an executable from a .dist directory.
"${VENV}/bin/python" -m nuitka \
  "${PROJECT_ROOT}/deploy_main.py" \
  --onefile \
  --enable-plugin=pyside6 \
  --output-dir="${DEPLOYMENT_ROOT}" \
  --output-filename=MyMediaEditor.bin \
  --assume-yes-for-downloads \
  --noinclude-qt-translations \
  --include-qt-plugins=multimedia,networkinformation,platforminputcontexts \
  --nofollow-import-to=imageio_ffmpeg

STANDALONE_BIN="${DEPLOYMENT_ROOT}/MyMediaEditor.bin"
[[ -x "${STANDALONE_BIN}" ]] || { echo "Nuitka onefile 결과가 없습니다." >&2; exit 1; }
"${VENV}/bin/python" "${PROJECT_ROOT}/scripts/bundle_ffmpeg.py" \
  --platform linux-x86_64 --destination "${APPDIR}/usr" --cache "${PROJECT_ROOT}/build/downloads"
install -m 0755 "${STANDALONE_BIN}" "${APPDIR}/usr/bin/MyMediaEditor"

curl -L --fail --retry 3 \
  "https://github.com/linuxdeploy/linuxdeploy/releases/download/${LINUXDEPLOY_VERSION}/linuxdeploy-x86_64.AppImage" \
  -o "${LINUXDEPLOY}"
chmod +x "${LINUXDEPLOY}"
VERSION="$("${VENV}/bin/python" -c 'import importlib.metadata; print(importlib.metadata.version("media-editor"))')"
OUTPUT="${DIST_ROOT}/MyMediaEditor-${VERSION}-x86_64.AppImage"
rm -f "${OUTPUT}"
OUTPUT="${OUTPUT}" APPIMAGE_EXTRACT_AND_RUN=1 "${LINUXDEPLOY}" \
  --appdir "${APPDIR}" \
  --executable "${APPDIR}/usr/bin/MyMediaEditor" \
  --executable "${APPDIR}/usr/bin/ffmpeg" \
  --executable "${APPDIR}/usr/bin/ffprobe" \
  --desktop-file "${PROJECT_ROOT}/packaging/linux/MyMediaEditor.desktop" \
  --icon-file "${PROJECT_ROOT}/packaging/linux/my-media-editor.svg" \
  --output appimage
[[ -f "${OUTPUT}" ]] || { echo "AppImage 결과가 없습니다." >&2; exit 1; }
chmod +x "${OUTPUT}"
echo "Created: ${OUTPUT}"
