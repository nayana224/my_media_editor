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
- Video Trim
  - Start / End를 초 단위로 지정
  - 현재 preview 위치를 Start 또는 End로 바로 입력
  - Trim 결과를 H.264 / AAC MP4로 출력
- MP4 Export
  - WebM -> MP4 변환
  - MP4 -> 호환성 높은 H.264 / AAC MP4 재출력
  - 입력 파일과 동일 경로로 저장하는 동작 차단
- Standard Upscale 2x / 4x
  - Image: Lanczos scale 후 PNG 출력
  - Video: Lanczos scale 후 H.264 / AAC MP4 출력
- FFmpeg video output 공통 처리
  - H.264 (`libx264`) + AAC
  - `yuv420p`
  - timestamp passthrough (`-vsync 0`)
  - 홀수 해상도 입력은 최대 1 px padding
- FFmpeg 작업은 `QProcess`로 실행하여 GUI thread를 block하지 않음
- 변환 결과를 Media Library에 자동 추가

`Crop`, `Resize`, Sequence / Concat, Layout Compose, AI Upscale은 이후 단계에서
구현합니다. AI Upscale은 Real-ESRGAN 계열 backend를 별도 검토합니다.

## Architecture

현재 project는 여러 media asset을 보관하는 `MediaProject`를 기준으로 동작합니다.
GUI preview는 Qt Multimedia를 사용하고 실제 변환/렌더링 작업은 FFmpeg backend로
분리합니다.

```text
PySide6 GUI
    |
    +-- MediaProject / MediaAsset
    |
    +-- Qt Multimedia  -> Preview / Seek
    |
    +-- FFmpeg
          |-- Trim
          |-- MP4 Export
          |-- Standard Upscale
          +-- future editing / compose
```

FFmpeg 작업은 현재 하나의 active job만 허용합니다. Trim, Export, Upscale 중 하나가
실행 중일 때 다른 FFmpeg 작업 버튼을 잠가 동일 파일에 대한 동시 변환을 방지합니다.

## Ubuntu Setup

`setup.sh`는 현재 shell에 source하지 않습니다.

```bash
cd ~/inpyo_ws/my_media_editor
git pull origin main
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

## Video Trim 사용법

1. Media Library에서 WebM 또는 MP4를 선택합니다.
2. 필요하면 preview를 재생하거나 timeline에서 원하는 위치로 이동합니다.
3. `Trim`을 누릅니다.
4. Start / End를 직접 입력하거나 `현재 위치` 버튼으로 preview 위치를 사용합니다.
5. 확인하면 원본과 같은 폴더에 `*_trimmed.mp4`가 생성됩니다.
6. 같은 이름이 이미 있으면 `_1`, `_2`처럼 고유 이름을 사용합니다.

Trim은 stream copy가 아니라 H.264 / AAC로 재인코딩합니다. 따라서 keyframe 위치에만
의존하지 않고 사용자가 지정한 구간을 정확하게 자르는 것을 우선합니다.

## WebM -> MP4 변환

1. WebM 파일을 선택합니다.
2. `Export MP4`를 누릅니다.
3. 저장 경로를 지정합니다.
4. H.264 / AAC MP4가 생성되고 Media Library에 자동 추가됩니다.

WebM의 기본 export 이름은 같은 stem의 `.mp4`입니다. 이미 해당 파일이 있으면 고유한
이름을 제안합니다. MP4 입력도 같은 export pipeline으로 재출력할 수 있습니다.

## 지원 형식

Image input:

- PNG
- JPG
- JPEG

Video input:

- WebM
- MP4

현재 video processing output은 MP4(H.264 / AAC)를 기본으로 합니다.

## Cross-platform 방향

- Ubuntu: 현재 개발 및 우선 검증 환경
- Windows: PySide6 코드와 FFmpeg backend를 동일하게 사용하도록 설계
- Release build: OS별 GitHub Actions runner에서 각각 build
- 초기 release는 portable executable/bundle을 먼저 만들고 이후 Windows installer와
  Linux AppImage 또는 `.deb`를 검토

FFmpeg executable bundle은 라이선스와 배포 조건을 확인한 뒤 release packaging 단계에서
결정합니다. 현재 development 환경에서는 system FFmpeg를 사용합니다.

## Roadmap

1. Crop / Resize / Rotate
2. 여러 video를 시간 순서로 붙이는 Sequence / Concat
3. Side-by-side / Top-bottom / 2x2 Grid layout compose
4. Export progress / cancel
5. AI Upscale
6. Windows / Ubuntu packaging 및 GitHub Release 자동화

기능 추가 시 README의 현재 구현 범위, 사용법, architecture와 roadmap도 함께 갱신합니다.
