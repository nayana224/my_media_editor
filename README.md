# Media Editor

Windows와 Ubuntu에서 이미지와 영상을 빠르게 preview하고 편집하기 위한
PySide6 + FFmpeg 기반 데스크톱 앱입니다.

## 현재 구현 범위

- Dark desktop UI
- 여러 media file import
- Media Library에서 file 선택 및 preview
- 여러 file Drag & Drop
- PNG / JPG / JPEG preview
- WebM / MP4 preview
- Video Play / Pause
- Timeline seek
- `Ctrl+O` media import
- Standard Upscale 2x / 4x
  - Image: Lanczos scale 후 PNG 출력
  - Video: Lanczos scale 후 H.264 / AAC MP4 출력
  - Video timestamp passthrough (`-vsync 0`)

`Trim`, `Crop`, `Resize`, `Export`, AI Upscale은 다음 개발 단계에서 구현할
기능입니다. AI Upscale은 Real-ESRGAN 계열 backend를 별도 검토합니다.

## Architecture

현재 project는 여러 media asset을 보관하는 `MediaProject`를 기준으로 동작합니다.
GUI preview는 Qt Multimedia를 사용하고 실제 변환/렌더링 작업은 FFmpeg backend로
분리합니다.

```text
PySide6 GUI
    |
    +-- MediaProject / MediaAsset
    |
    +-- Qt Multimedia  -> Preview
    |
    +-- FFmpeg         -> Upscale / Export / future editing
```

## Ubuntu Setup

`setup.sh`는 현재 shell에 source하지 않습니다.

```bash
cd ~/inpyo_ws/my_media_editor
./scripts/setup.sh
```

## Run

```bash
cd ~/inpyo_ws/my_media_editor
./scripts/run.sh
```

## Check

```bash
cd ~/inpyo_ws/my_media_editor
./scripts/check.sh
```

## 지원 형식

Image input:

- PNG
- JPG
- JPEG

Video input:

- WebM
- MP4

Standard video upscale output은 현재 MP4(H.264 / AAC)입니다.

## Cross-platform 방향

- Ubuntu: 현재 개발 환경
- Windows: PySide6 코드와 FFmpeg backend를 동일하게 사용하도록 설계
- Release build: OS별 GitHub Actions runner에서 각각 build
- 초기 release는 portable executable/bundle을 먼저 만들고 이후 Windows installer와
  Linux AppImage 또는 `.deb`를 검토

FFmpeg executable bundle은 라이선스와 배포 조건을 확인한 뒤 release packaging 단계에서
결정합니다. 현재 development 환경에서는 system FFmpeg를 사용합니다.

## Roadmap

1. Video trim
2. WebM -> MP4 export
3. Crop / Resize / Rotate
4. 여러 video를 시간 순서로 붙이는 Sequence / Concat
5. Side-by-side / Top-bottom / 2x2 Grid layout compose
6. Export progress / cancel
7. AI Upscale
8. Windows / Ubuntu packaging 및 GitHub Release 자동화
