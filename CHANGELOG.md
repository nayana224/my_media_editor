# Changelog

## 0.1.2

- Crop 모서리·네 변을 첫 드래그부터 조절하고 반대쪽 경계를 고정.
- 비정사각형 픽셀 영상의 미리보기와 원본 자르기 좌표를 분리해 Save As 실패 수정.
- 원본을 벗어난 Crop 값을 저장 전에 확인하고 FFmpeg 오류 로그는 펼쳐서 표시.
- 비정사각형 픽셀 영상의 실제 Crop 저장을 패키지 진단에 추가.

## 0.1.1

- Ubuntu 22.04를 배포 빌드 기준으로 제한하고, 같은 AppImage의 22.04/24.04/26.04 호환성 검사 추가.
- Qt X11용 xcb-cursor와 관련 라이브러리 동봉, 실제 X11 자동 진단 추가.
- Ubuntu 24용 수동 확인 가이드 추가.

- Linux/Windows에 SHA256으로 고정한 FFmpeg와 FFprobe 동봉.
- Nuitka/PySide6 빌드 버전과 onefile 출력 경로 고정.
- Windows 빌드 오류 처리와 Python 3.11+ 사전 검사.
- Nuitka onefile의 원본 EXE 옆 도구 검색 및 FFprobe 공통 경로 처리.
- 완성 AppImage/추출 ZIP의 실제 GUI·미디어 자체 진단을 CI 배포 조건으로 추가.
- 공급자 고지·빌드 정보 동봉 및 배포 안내 갱신.


## v0.1.0

첫 desktop release 준비 버전입니다.

### Editing

- PNG / JPG / JPEG / WebM / MP4 import
- Media Library
- 영상 첫 frame 자동 Preview
- Trim
- Crop
- Resize
- Rotate
- Standard Upscale 2x / 4x
- Speed 0.25x ~ 4.00x
- Pending edit 기반 비파괴 편집
- Unified Live Preview
- Edited Timeline
- `Save As…` one-pass FFmpeg render
- Sequence / Concat

### Usability

- Drag & Drop
- Crop zoom / pan
- Rotate Dial
- Speed live playback
- 추천 저장 파일명
- `Ctrl+C` / SIGTERM 안전 종료

### Packaging

- Qt 공식 `pyside6-deploy` 기반 standalone build 진입점
- Ubuntu x86_64 AppImage build script
- Windows x64 portable ZIP build script
- Ubuntu / Windows GitHub Actions build
- `v*` tag 기반 GitHub Release 자동 생성
- bundled tool 탐색을 위한 runtime path bootstrap

### Known limitations

- v0.1.0 artifact에는 FFmpeg / FFprobe binary를 포함하지 않음
- Windows installer는 아직 제공하지 않고 portable ZIP을 우선 제공
- AI Upscale 미구현
