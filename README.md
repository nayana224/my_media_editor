# Media Editor

Windows와 Ubuntu에서 이미지와 영상을 preview하면서 편집하기 위한 PySide6 + FFmpeg 기반 데스크톱 앱입니다.

## 편집 방식

단일 미디어의 `Trim`, `Crop`, `Rotate`, `Resize`, `Upscale`, `Speed`는 버튼을 누를 때마다 파일을 생성하지 않습니다. 각 편집 값은 원본 파일에 대한 **Pending edits**로 누적되고, `Save As…`를 눌렀을 때 FFmpeg를 한 번만 실행하여 최종 파일을 만듭니다.

적용 순서는 다음과 같이 고정합니다.

```text
Trim → Crop → Rotate → Resize → Upscale → Speed → Save
```

중간 MP4/PNG 파일과 반복 재인코딩을 만들지 않으며 Media Library에서 다른 파일로 이동해도 각 파일의 Pending edits는 별도로 유지됩니다.

## Preview 원칙

사용자는 항상 **현재 저장될 결과에 가까운 화면을 보면서 편집**하는 것을 기본 원칙으로 합니다.

- 영상 선택 직후 첫 frame 자동 표시
- Crop / Rotate / Resize 변경 후 메인 Preview 즉시 갱신
- Speed는 실제 재생 속도로 Preview
- Trim이 있으면 해당 구간 안에서 재생
- Reset edits 시 즉시 원본 Preview 복원
- Upscale은 화면 구도를 바꾸지 않으므로 예상 출력 해상도만 표시

영상은 `QMediaPlayer → QVideoSink → QVideoFrame → QImage` 경로로 frame을 받아 Pending edit을 화면용으로 빠르게 적용합니다. 최종 Save는 같은 `EditState`를 FFmpeg one-pass filter chain으로 변환합니다.

고해상도 source에서는 Preview 때문에 메모리와 CPU 사용량이 과도해지지 않도록 화면용 frame 크기를 제한합니다. 최종 저장 해상도에는 영향을 주지 않습니다.

## 현재 구현 기능

- Dark desktop UI
- 여러 media file import
- Media Library
  - `+ Add`, `Import Media`, `Ctrl+O`, Drag & Drop
  - `− Remove` / `Delete`로 project에서 제거
  - disk 원본은 삭제하지 않음
- PNG / JPG / JPEG
- WebM / MP4
- Play / Pause / Seek
- 첫 frame 자동 Preview
- Pending edit live preview
- `Reset edits`
- `Save As…` / `Ctrl+Shift+S`
- 추천 파일명 `<원본이름>_edited.mp4` / `<원본이름>_edited.png`
- Sequence / Concat
- `Ctrl+C` / `SIGTERM` 안전 종료

## Trim

- dialog 안에서 실제 영상 재생 / seek
- Start / End 지정
- Pending Trim 상태이면 메인 Play도 해당 범위로 제한

## Crop

실제 frame 위에서 직접 작업합니다.

- 왼쪽 drag: 새 crop 영역 생성
- 영역 안쪽 drag: crop 영역 이동
- 모서리 handle: 크기 조절
- `Ctrl + Wheel`: 확대 / 축소
- 가운데 휠 버튼 drag: 확대 화면 pan
- `선택 영역 맞춤`
- `전체 보기`
- 자유 / 원본 / 16:9 / 4:3 / 1:1 aspect
- X / Y / Width / Height 직접 수정

## Rotate

Rotate는 라디오 버튼만 선택하는 방식 대신 **직접 돌려보는 dial UI**를 사용합니다.

```text
          0°
           ▲
      ┌────●────┐
270° ◀    dial    ▶ 90°
      └─────────┘
           ▼
          180°
```

- dial drag로 0° / 90° / 180° / 270° 이동
- `0°`, `↻ 90°`, `180°`, `↺ 90°` quick preset
- dial을 움직일 때 dialog Preview 즉시 회전
- 기존 Crop 상태가 있으면 Crop 결과 위에서 회전 Preview
- 기존 Resize가 있으면 최종 화면 비율까지 함께 Preview
- OK 후 메인 Preview 즉시 갱신
- 0° 선택 시 Pending Rotate 제거

현재 최종 Save는 영상 호환성과 예측 가능한 canvas 처리를 위해 90° 단위 회전을 지원합니다.

## Resize

- Original / 1080p / 720p / 480p / 360p / Custom
- aspect ratio 유지 선택
- OK 후 메인 Preview 즉시 갱신

## Upscale

- Standard Lanczos 2x / 4x
- 실제 출력 해상도는 Save 시 적용
- Preview에서는 불필요한 초대형 bitmap 생성을 피함

## Speed

Speed는 숫자만 입력하는 창이 아니라 **실제 영상을 보면서 조절하는 dialog**입니다.

```text
┌──────────────────────────────────────────────┐
│             실제 편집 상태 Preview            │
│                                              │
├──────────────────────────────────────────────┤
│ ▶ Play  ─────────────●────────────  00:12.30 │
│                                              │
│ 0.25x ───────────────●─────────────── 4.00x  │
│                                  [1.50x]      │
│                                              │
│ [0.5x] [1x] [1.5x] [2x] [4x]               │
│ 예상 길이 00:21.47                           │
└──────────────────────────────────────────────┘
```

- 0.25x ~ 4.00x slider
- 0.5x / 1x / 1.5x / 2x / 4x preset
- 0.05x 단위 숫자 미세 조절
- Speed dialog 내부 Play / Pause / Seek
- Crop / Rotate / Resize 등 현재 Pending 화면 편집도 Speed Preview에 같이 표시
- slider를 움직이면 dialog의 실제 영상 playbackRate 즉시 변경
- OK 후 메인 player도 같은 playbackRate 유지
- 미디어를 다시 선택해도 해당 파일의 Pending Speed 복원
- Cancel 시 기존 속도로 복원
- 1.00x 선택 시 Pending Speed 제거
- 예상 출력 길이 표시

최종 Save에서는 video에 `setpts`를 적용하고 audio에는 FFmpeg `atempo`를 사용합니다. 0.25x와 4x 같은 범위에서는 여러 `atempo`를 연결하여 처리합니다.

## 연속 편집 예

```text
input.mp4
  ↓ Crop
메인 Preview 즉시 갱신
  ↓ Rotate dial 90°
메인 Preview 즉시 갱신
  ↓ Resize 1280×720
메인 Preview 즉시 갱신
  ↓ Speed 1.5x
실제 1.5x 속도로 Preview
  ↓ Save As…
input_edited.mp4
```

하단에는 현재 상태가 표시됩니다.

```text
Pending edits: Crop 1200x800 · Rotate 90° · Resize 1280x720 · Speed 1.50x
```

## Save workflow

1. 원하는 편집들을 순서와 관계없이 설정
2. 메인 Preview에서 누적 결과 확인
3. `Save As…` 또는 `Ctrl+Shift+S`
4. 추천된 `_edited` 이름 확인
5. 필요하면 파일명 / 저장 폴더 수정
6. FFmpeg가 모든 Pending edit을 한 번에 렌더링
7. 결과 파일을 Media Library에 자동 추가

Video output:

- H.264 (`libx264`)
- AAC
- MP4
- 홀수 해상도는 마지막에 최대 1 px padding

Image output:

- PNG

WebM을 별도 편집 없이 `Save As…`해도 MP4로 변환할 수 있습니다.

## Sequence / Concat

- WebM / MP4 여러 clip append
- drag로 순서 변경
- 서로 다른 해상도는 첫 clip canvas 기준으로 aspect ratio 유지 후 정규화
- audio 없는 clip에는 같은 길이의 silence 생성

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
    |       |-- Upscale
    |       +-- Speed
    |
    +-- Live Preview
    |       |-- QMediaPlayer
    |       |-- QVideoSink
    |       |-- QVideoFrame.toImage()
    |       |-- preview_transform.py
    |       +-- playbackRate
    |
    +-- Edit Dialogs
    |       |-- Trim playback
    |       |-- Crop + Zoom + Pan
    |       |-- Rotate dial
    |       |-- Resize
    |       |-- Upscale
    |       +-- Speed video preview + slider
    |
    +-- FFmpeg
            |-- one-pass Save pipeline
            |-- setpts + atempo
            |-- H.264 / AAC MP4
            +-- Sequence / Concat
```

## UX 참고 방향

전문 편집기의 모든 기능을 복제하지 않고, 작은 앱에 유용한 interaction만 선택적으로 가져옵니다.

- Kdenlive Transform: monitor에서 직접 transform 결과를 확인하는 방식
- Kdenlive Rotate: 90° 단위 빠른 회전 접근
- Kdenlive Speed: mouse 기반 speed change와 pitch compensation 개념
- Kdenlive timeline: 가운데 마우스 버튼 기반 pan과 direct manipulation

현재 앱에서는 이를 단순화하여 Crop zoom/pan, Rotate dial, Speed live video preview처럼 **mouse로 직접 조절하고 즉시 결과를 보는 UX**를 우선합니다.

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

Terminal에서는 `Ctrl+C`로 안전하게 종료할 수 있습니다.

## Check

```bash
cd ~/inpyo_ws/my_media_editor
./scripts/check.sh
```

## Cross-platform 방향

- Ubuntu: 현재 우선 개발 및 검증 환경
- Windows: 동일한 PySide6 + FFmpeg 구조
- OS별 GitHub Actions runner에서 release build
- 초기 release: portable executable / bundle
- 이후 Windows installer + Linux AppImage 또는 `.deb`

FFmpeg executable bundle은 라이선스와 배포 조건을 확인한 뒤 packaging 단계에서 결정합니다. 현재 development 환경에서는 system FFmpeg를 사용합니다.

## Roadmap

1. Timeline usability
   - 좌/우 화살표 frame step
   - J / K / L playback control
   - clip 경계 snap
   - marker
   - Fit Zoom
2. Sequence / Concat UI 통합 보강
3. Side-by-side / Top-bottom / 2x2 Grid layout compose
4. Export progress / cancel
5. 고해상도 source용 proxy preview
6. AI Upscale
7. Windows / Ubuntu packaging 및 GitHub Release 자동화

기능 추가 시 README의 현재 구현 범위, 사용법, architecture와 roadmap도 함께 갱신합니다.
