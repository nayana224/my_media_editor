# Media Editor

Windows와 Ubuntu에서 이미지와 영상을 preview하면서 편집하기 위한
PySide6 + FFmpeg 기반 데스크톱 앱입니다.

## 편집 방식

단일 미디어의 `Trim`, `Crop`, `Rotate`, `Resize`, `Upscale`은 버튼을 누를 때마다 파일을
생성하지 않습니다. 각 편집 값은 원본 파일에 대한 **Pending edits**로 누적되고,
`Save As…`를 눌렀을 때 FFmpeg를 한 번만 실행하여 최종 파일을 만듭니다.

적용 순서는 항상 다음과 같이 고정합니다.

```text
Trim → Crop → Rotate → Resize → Upscale → Save
```

이 방식은 중간 MP4/PNG 파일이 계속 생기는 문제와 반복 재인코딩으로 인한 불필요한 화질
손실을 줄입니다. Media Library에서 다른 파일로 이동해도 각 파일의 Pending edits는 별도로
유지됩니다.

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
- 비파괴 Pending edit workflow
  - Trim / Crop / Rotate / Resize / Upscale 값을 누적
  - 하단에서 현재 Pending edits 표시
  - `Reset edits`로 현재 파일의 편집 값 전체 초기화
  - `Save As…` 또는 `Ctrl+Shift+S`에서 최종 렌더링
  - 추천 파일명은 `<원본이름>_edited.mp4` 또는 `<원본이름>_edited.png`
  - Save dialog에서 파일명과 폴더를 자유롭게 수정 가능
- Preview-first 편집 dialog
  - Trim: dialog 안에서 실제 영상을 재생/seek하면서 Start / End 지정
  - Crop: 현재 video frame 또는 image를 직접 보면서 영역 선택
  - Resize: 현재 frame을 보면서 preset/custom 해상도 조절
  - Rotate: 현재 frame에 회전 결과를 즉시 preview
  - Upscale: 현재 frame과 예상 출력 해상도를 함께 표시
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
  - X / Y / Width / Height 직접 수정 가능
- Resize
  - Original / 1080p / 720p / 480p / 360p preset
  - Custom width / height
  - 가로세로 비율 유지
- Rotate
  - 90° clockwise / 180° / 90° counter-clockwise
- Standard Upscale 2x / 4x
  - Lanczos 기반
  - AI 복원이 아니라 고품질 일반 확대
- Sequence / Concat backend 및 dialog
  - WebM / MP4 clip append
  - drag & drop 순서 변경
  - 서로 다른 해상도는 첫 clip canvas에 aspect ratio 유지 후 정규화
  - 오디오 없는 clip에는 같은 길이의 silence 생성
- FFmpeg video output
  - H.264 (`libx264`) + AAC
  - `yuv420p`
  - 홀수 해상도는 마지막에 최대 1 px padding
- FFmpeg 작업은 `QProcess`로 실행하여 GUI thread를 block하지 않음
- Save 결과를 Media Library에 자동 추가하고 결과 file을 자동 선택
- Terminal 종료 처리
  - `Ctrl+C` (`SIGINT`)와 `SIGTERM` 처리
  - active playback 및 FFmpeg child process 정리

## Save workflow

예를 들어 하나의 WebM에 다음 작업을 한다고 가정합니다.

```text
input.webm
  ├─ Trim: 2.0 s ~ 18.5 s
  ├─ Crop: 1200 x 800
  ├─ Rotate: 90°
  ├─ Resize: 1280 x 720
  └─ Upscale: 2x
```

각 dialog에서 `OK`를 눌러도 이 시점에는 파일을 만들지 않습니다. 하단에는 다음처럼 상태가
표시됩니다.

```text
Pending edits: Trim 2.000-18.500s · Crop 1200x800 · Rotate 90° · Resize 1280x720 · Upscale 2x
```

마지막에 `Save As…`를 누르면 기본 제안 경로가 다음처럼 열립니다.

```text
input_edited.mp4
```

사용자는 Save dialog에서 `experiment_result.mp4`처럼 이름을 바꾸거나 다른 폴더를 선택할 수
있습니다. Save가 성공하면 원본 파일의 Pending edits를 비우고 결과 파일을 Media Library에
추가합니다.

이미지는 기본적으로 `<원본이름>_edited.png`를 제안합니다.

## Preview 동작

영상 파일을 선택하면 사용자가 `Play`를 누르지 않아도 첫 유효 video frame을 자동으로
준비합니다. 내부적으로 첫 frame이 decode될 때까지만 소리 없이 재생하고, frame이 도착하면
즉시 pause하고 위치를 0으로 되돌립니다.

영상 편집 dialog는 Qt Multimedia의 `QVideoSink`에서 현재 video frame을 가져와
`QImage` preview로 사용합니다.

Trim은 dialog 내부에 별도의 `QMediaPlayer`와 `QVideoWidget`을 사용합니다. Trim 창 안에서
영상을 재생하거나 seek한 뒤 현재 위치를 Start 또는 End로 바로 지정할 수 있습니다.

Video Crop은 현재 preview frame에서 pixel 영역을 선택하며 최종 Save 시 같은 좌표를 전체
영상에 적용합니다.

## Architecture

```text
PySide6 GUI
    |
    +-- MediaProject / MediaAsset
    |
    +-- EditState
    |       |-- Trim
    |       |-- Crop
    |       |-- Rotate
    |       |-- Resize
    |       +-- Upscale
    |
    +-- Qt Multimedia
    |       |-- Main Preview / Seek
    |       |-- first-frame auto prime
    |       |-- QVideoSink current frame
    |       +-- Trim dialog playback
    |
    +-- Edit Dialogs
    |       |-- Interactive Crop + Zoom + Pan
    |       |-- Resize preview
    |       |-- Rotate preview
    |       +-- Upscale preview
    |
    +-- FFmpeg
            |-- one-pass Save pipeline
            |-- H.264 / AAC MP4
            +-- Sequence / Concat backend
```

단일 미디어 Save의 filter chain은 `Crop → Rotate → Resize → Upscale` 순서로 구성하고,
video Trim은 같은 FFmpeg command의 시간 구간 옵션으로 함께 적용합니다.

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

Terminal에서 실행한 경우 `Ctrl+C`로 안전하게 종료할 수 있습니다.

## Check

```bash
cd ~/inpyo_ws/my_media_editor
./scripts/check.sh
```

## 주요 사용법

### Trim

1. WebM 또는 MP4를 선택합니다.
2. `Trim`을 누릅니다.
3. dialog 안에서 영상을 재생하거나 seek합니다.
4. Start / End를 지정한 뒤 `OK`를 누릅니다.
5. Trim 값이 Pending edits에 추가됩니다.
6. 다른 편집을 계속한 뒤 마지막에 `Save As…`를 누릅니다.

### Crop

1. 원하는 frame으로 seek한 뒤 `Crop`을 누릅니다.
2. 왼쪽 drag로 crop rectangle을 새로 그립니다.
3. 영역 내부 drag로 이동하고 모서리 handle로 크기를 조절합니다.
4. `Ctrl + Wheel`로 zoom하고 가운데 휠 버튼 drag로 view를 이동합니다.
5. `OK`를 누르면 Crop 값만 Pending edits에 저장됩니다.
6. Resize / Rotate / Upscale 등을 계속 설정할 수 있습니다.

### Resize / Rotate / Upscale

각 dialog의 `OK`는 즉시 파일을 만들지 않고 현재 파일의 Pending edits를 갱신합니다. 같은
기능을 다시 열면 기존 설정을 수정할 수 있습니다.

### Reset edits

`Reset edits`는 원본 파일을 건드리지 않고 현재 파일에 쌓인 Pending edits만 모두 제거합니다.

### Save As

1. 원하는 편집을 모두 설정합니다.
2. `Save As…` 또는 `Ctrl+Shift+S`를 누릅니다.
3. 추천된 `<원본이름>_edited` 이름을 그대로 쓰거나 수정합니다.
4. 저장 폴더를 선택합니다.
5. FFmpeg가 누적 편집을 한 번에 렌더링합니다.

## 지원 형식

Image input:

- PNG
- JPG
- JPEG

Video input:

- WebM
- MP4

Save output:

- Image: PNG
- Video: MP4 (H.264 / AAC)

WebM을 별도 편집 없이 `Save As…`해도 MP4로 변환할 수 있습니다.

## Cross-platform 방향

- Ubuntu: 현재 우선 개발 및 검증 환경
- Windows: 동일한 PySide6 + FFmpeg 구조 사용
- OS별 GitHub Actions runner에서 release build
- 초기 release는 portable executable/bundle
- 이후 Windows installer와 Linux AppImage 또는 `.deb` 검토

FFmpeg executable bundle은 라이선스와 배포 조건을 확인한 뒤 packaging 단계에서 결정합니다.
현재 development 환경에서는 system FFmpeg를 사용합니다.

## Roadmap

1. Pending edit의 main preview 합성 표시
2. Timeline usability
   - 좌/우 화살표 frame step
   - clip 경계 snap
   - marker
   - Fit Zoom
3. Sequence / Concat UI 통합 보강
4. Side-by-side / Top-bottom / 2x2 Grid layout compose
5. Export progress / cancel
6. 고해상도 source용 proxy preview
7. AI Upscale
8. Windows / Ubuntu packaging 및 GitHub Release 자동화

기능 추가 시 README의 현재 구현 범위, 사용법, architecture와 roadmap도 함께 갱신합니다.
