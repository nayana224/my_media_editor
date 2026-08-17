# Changelog

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
