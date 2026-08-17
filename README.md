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
  - 영상 선택 직후 첫 frame을 자동 decode하여 표시
  - 첫 frame 준비 중에는 audio를 mute하고 frame 확보 후 자동 pause
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
  - 초기 전체 프레임 상태에서도 첫 왼쪽 drag로 새 crop 영역 생성
  - 선택 영역 내부 drag로 crop rectangle 이동
  - 네 모서리 handle로 resize
  - `Ctrl + 마우스 휠`로 crop preview 확대/축소
  - 마우스 위치를 중심으로 zoom
  - `가운데 휠 버튼 drag`로 확대된 view 이동
  - `선택 영역 맞춤`, `전체 보기` 제공
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
- Terminal 종료 처리
  - `Ctrl+C` (`SIGINT`)와 `SIGTERM`을 처리
  - video playback을 중지하고 active FFmpeg process에 `terminate()` 요청
  - 제한 시간 안에 끝나지 않으면 `kill()` 후 application 종료

## Preview 동작

영상 파일을 선택하면 사용자가 `Play`를 누르지 않아도 첫 유효 video frame을 자동으로
준비합니다. 내부적으로 첫 frame이 decode될 때까지만 소리 없이 재생하고, frame이 도착하면
즉시 pause하고 위치를 0으로 되돌립니다.

영상 편집 dialog는 Qt Multimedia의 `QVideoSink`에서 현재 video frame을 가져와
`QImage` preview로 사용합니다. 따라서 Crop / Resize / Rotate / Upscale에서 현재 보고 있던
영상 frame을 기준으로 편집 결과를 확인할 수 있습니다.

Trim은 정지 frame만 보여주는 방식이 아니라 dialog 내부에 별도의 `QMediaPlayer`와
`QVideoWidget`을 사용합니다. Trim 창 안에서 영상을 재생하거나 seek한 뒤 현재 위치를
Start 또는 End로 바로 지정할 수 있습니다.

Video Crop은 현재 preview frame에서 pixel 영역을 선택하고, 해당 X / Y / Width / Height를
전체 영상에 동일하게 적용합니다.

## Architecture

```text
PySide6 GUI
    |
    +-- MediaProject / MediaAsset
    |       +-- Add / Remove
    |
    +-- Qt Multimedia
    |       |-- Main Preview / Seek
    |       |-- first-frame auto prime
    |       |-- QVideoSink current frame
    |       +-- Trim dialog playback
    |
    +-- Edit Dialogs
    |       |-- Trim
    |       |-- Interactive Crop + Zoom + Pan
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

Terminal에서 실행한 경우 `Ctrl+C`로 종료할 수 있습니다. 종료 시 재생을 중지하고 active
FFmpeg child process를 우선 정상 종료한 뒤 필요할 경우 강제 종료합니다.

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

1. 영상 파일을 선택하면 첫 frame이 자동 표시됩니다.
2. 필요하면 원하는 frame으로 seek한 뒤 `Crop`을 누릅니다.
3. 초기에는 전체 frame이 선택되어 있어도, 화면에서 왼쪽 drag를 시작하면 바로 새 crop rectangle이 생성됩니다.
4. crop rectangle을 만든 뒤에는 영역 내부 drag로 이동하고 네 모서리 handle로 크기를 조절합니다.
5. 세밀한 조정이 필요하면 crop preview 위에서 `Ctrl + 마우스 휠`을 사용합니다.
   - 위로 scroll: 확대
   - 아래로 scroll: 축소
   - 마우스 포인터 위치를 중심으로 확대/축소
6. 확대된 화면은 `가운데 휠 버튼`을 누른 채 drag하여 이동합니다.
7. 선택 영역이 작아졌다면 `선택 영역 맞춤`으로 해당 영역을 화면에 크게 채울 수 있습니다.
8. `전체 보기`를 누르면 원본 frame 전체 view로 돌아갑니다.
9. 필요하면 aspect preset 또는 정확한 pixel 값을 사용합니다.
10. `OK`를 누르면 전체 영상에 같은 crop 좌표가 적용됩니다.

### Resize

현재 frame preview를 보면서 preset 또는 custom 해상도를 선택합니다. `가로세로 비율 유지`가
켜져 있으면 원본 aspect ratio를 유지하면서 preset 영역 안에 들어가는 최대 크기를 계산합니다.

### Rotate

현재 frame을 보면서 회전 방향을 선택하면 preview가 즉시 갱신됩니다.

### Upscale

현재 frame과 예상 출력 해상도를 확인하면서 Standard 2x 또는 4x를 선택합니다. 현재
Standard Upscale은 Lanczos 기반이며 AI 복원은 아닙니다.

## 다른 편집기에서 참고할 UX 방향

기능을 그대로 복제하기보다 작은 데스크톱 편집기에 맞는 상호작용만 선별해서 적용합니다.

- Kdenlive 계열 UX
  - frame 단위 좌/우 이동
  - clip 경계, playhead, marker에 snap
  - timeline `Fit Zoom`
  - 4K 이상 source용 proxy workflow
  - configurable shortcut
- DaVinci Resolve Cut 계열 UX
  - 전체 sequence와 현재 작업 구간을 동시에 보는 dual timeline 개념
  - 현재 media를 빠르게 훑는 source-tape 성격의 browsing
  - 선택 clip을 sequence 끝에 즉시 추가하는 `Append at End`
  - trim 시 작업 지점을 크게 보여주는 집중형 editing view

현재 Crop의 `전체 보기` + 확대 view, `Ctrl + Wheel` zoom, 가운데 버튼 pan도 이와 같은
"전체 맥락을 유지하면서 필요한 곳만 정밀하게 편집"하는 방향으로 유지합니다.

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

1. Sequence / Concat
   - Media Library에서 여러 video 선택
   - drag로 순서 변경
   - `Append at End`
   - clip 경계 snap
2. Timeline usability
   - 좌/우 화살표 frame step
   - marker
   - Fit Zoom
   - 전체 sequence + 작업 구간을 함께 보는 compact dual-view
3. Side-by-side / Top-bottom / 2x2 Grid layout compose
4. Export progress / cancel
5. 고해상도 source용 proxy preview
6. AI Upscale
7. Windows / Ubuntu packaging 및 GitHub Release 자동화

기능 추가 시 README의 현재 구현 범위, 사용법, architecture와 roadmap도 함께 갱신합니다.
