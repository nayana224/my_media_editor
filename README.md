# Media Editor

Windows와 Ubuntu에서 이미지와 영상을 preview하면서 편집하기 위한
PySide6 + FFmpeg 기반 데스크톱 앱입니다.

## 현재 구현 범위

- Dark desktop UI
- 여러 media file import
- Media Library
  - `+ Add`, `Import Media`, `Ctrl+O`, Drag & Drop으로 file 추가
  - `− Remove` 또는 `Delete` key로 project에서 제거
  - Remove는 disk의 원본 file을 삭제하지 않음
- PNG / JPG / JPEG preview
- WebM / MP4 preview
- Video Play / Pause / Seek
- Preview-first 편집 dialog
  - Trim: dialog 안에서 실제 영상을 재생/seek하면서 Start / End 지정
  - Crop: 현재 video frame 또는 image를 직접 보면서 영역 선택
  - Resize: 현재 frame을 보면서 preset/custom 해상도 조절
  - Rotate: 현재 frame에 회전 결과를 즉시 preview
  - Upscale: 현재 frame과 예상 출력 해상도를 함께 표시
- Video Trim
  - Start / End slider와 초 단위 입력
  - `Start = 현재 위치`, `End = 현재 위치`, `전체 길이`
  - 선택 구간 길이 즉시 표시
- Crop
  - Image / Video 지원
  - preview 위에서 새 영역 drag
  - 영역 내부 drag로 이동
  - 네 모서리 handle로 resize
  - 자유 / 원본 비율 / 16:9 / 4:3 / 1:1 preset
  - `가운데 80%`, `전체 프레임`
  - X / Y / Width / Height 직접 수정 가능
- Resize
  - Original / 1080p / 720p / 480p / 360p preset
  - Custom width / height
  - 가로세로 비율 유지
- Rotate
  - 90° clockwise / 180° / 90° counter-clockwise
- Standard Upscale 2x / 4x
  - Image: Lanczos scale 후 PNG
  - Video: Lanczos scale 후 H.264 / AAC MP4
- MP4 Export
  - WebM -> MP4
  - MP4 -> H.264 / AAC MP4 재출력
- FFmpeg video output 공통 처리
  - H.264 (`libx264`) + AAC
  - `yuv420p`
  - timestamp passthrough (`-vsync 0`)
  - 홀수 해상도 입력은 최대 1 px padding
- FFmpeg 작업은 `QProcess`로 실행하여 GUI thread를 block하지 않음
- 편집 결과를 Media Library에 자동 추가하고 결과 file을 자동 선택

## Preview 동작

영상 편집 dialog는 Qt Multimedia의 `QVideoSink`에서 현재 video frame을 가져와
`QImage` preview로 사용합니다. 따라서 Crop / Resize / Rotate / Upscale에서 현재 보고 있던
영상 frame을 기준으로 편집 결과를 확인할 수 있습니다.

Trim은 정지 frame만 보여주는 방식이 아니라 dialog 내부에 별도의 `QMediaPlayer`와
`QVideoWidget`을 사용합니다. Trim 창 안에서 영상을 재생하거나 seek한 뒤 현재 위치를
Start 또는 End로 바로 지정할 수 있습니다.

Video Crop은 현재 preview frame에서 pixel 영역을 선택하고, 해당 X / Y / Width / Height를
전체 영상에 동일하게 적용합니다.

영상이 아직 decode되지 않아 현재 frame을 얻지 못한 경우에는 preview 안내 문구를
표시합니다. 이 경우 영상을 잠깐 재생하거나 seek한 뒤 dialog를 다시 열면 됩니다.

## Architecture

```text
PySide6 GUI
    |
    +-- MediaProject / MediaAsset
    |       +-- Add / Remove
    |
    +-- Qt Multimedia
    |       |-- Main Preview / Seek
    |       |-- QVideoSink current frame
    |       +-- Trim dialog playback
    |
    +-- Edit Dialogs
    |       |-- Trim
    |       |-- Interactive Crop
    |       |-- Resize live preview
    |       |-- Rotate live preview
    |       +-- Upscale preview
    |
    +-- FFmpeg
            |-- Trim
            |-- Crop
            |-- Resize
            |-- Rotate
            |-- MP4 Export
            |-- Standard Upscale
            +-- future concat / compose
```

FFmpeg 작업은 하나의 active job만 허용합니다. 편집이나 export 중에는 다른 FFmpeg 작업과
Media Library 변경 버튼을 잠가 동일 source에 대한 동시 변환을 방지합니다.

## Ubuntu Setup

`setup.sh`는 source하지 않습니다.

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

## 사용 흐름

### Trim

1. WebM 또는 MP4를 선택합니다.
2. `Trim`을 누릅니다.
3. Trim dialog 안에서 영상을 직접 재생하거나 timeline을 seek합니다.
4. 원하는 위치에서 `Start = 현재 위치` 또는 `End = 현재 위치`를 누릅니다.
5. Start / End slider 또는 초 단위 입력으로 미세 조정합니다.
6. 선택 구간 길이를 확인한 뒤 `OK`를 누릅니다.
7. `*_trimmed.mp4`가 생성되고 Media Library에 자동 추가됩니다.

Trim은 stream copy가 아니라 H.264 / AAC로 재인코딩하여 keyframe 위치보다 지정 구간의
정확성을 우선합니다.

### Crop

1. 영상에서 crop 판단에 적합한 frame으로 seek합니다.
2. `Crop`을 누릅니다.
3. 실제 frame 위에서 crop rectangle을 직접 그리거나 이동/resize합니다.
4. 필요하면 aspect preset 또는 정확한 pixel 값을 사용합니다.
5. `OK`를 누르면 전체 영상에 같은 crop 좌표가 적용됩니다.

### Resize

현재 frame preview를 보면서 preset 또는 custom 해상도를 선택합니다. `가로세로 비율 유지`가
켜져 있으면 원본 aspect ratio를 유지하면서 preset 영역 안에 들어가는 최대 크기를 계산합니다.

### Rotate

현재 frame을 보면서 회전 방향을 선택하면 preview가 즉시 갱신됩니다.

### Upscale

현재 frame과 예상 출력 해상도를 확인하면서 Standard 2x 또는 4x를 선택합니다. 현재
Standard Upscale은 Lanczos 기반이며 AI 복원은 아닙니다.

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

- Ubuntu: 현재 우선 개발 및 검증 환경
- Windows: 동일한 PySide6 + FFmpeg 구조 사용
- OS별 GitHub Actions runner에서 release build
- 초기 release는 portable executable/bundle
- 이후 Windows installer와 Linux AppImage 또는 `.deb` 검토

FFmpeg executable bundle은 라이선스와 배포 조건을 확인한 뒤 packaging 단계에서 결정합니다.
현재 development 환경에서는 system FFmpeg를 사용합니다.

## Roadmap

1. 여러 video를 시간 순서로 붙이는 Sequence / Concat
2. Side-by-side / Top-bottom / 2x2 Grid layout compose
3. Export progress / cancel
4. AI Upscale
5. Windows / Ubuntu packaging 및 GitHub Release 자동화

기능 추가 시 README의 현재 구현 범위, 사용법, architecture와 roadmap도 함께 갱신합니다.
