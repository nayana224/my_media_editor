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

중간 MP4/PNG 파일과 반복 재인코딩을 만들지 않으며 Media Library에서 다른 파일로 이동해도
각 파일의 Pending edits는 별도로 유지됩니다.

## Live Preview

Pending edit을 변경하면 메인 Preview도 즉시 같은 편집 상태를 반영합니다.

```text
원본 frame
   ↓
Crop
   ↓
Rotate
   ↓
Resize
   ↓
메인 Preview
```

영상은 `QMediaPlayer → QVideoSink`에서 decode frame을 받고, 화면용 `QImage`에 현재
`EditState`를 적용하여 재생 중에도 Crop / Rotate / Resize 결과를 표시합니다. Save는 같은
`EditState`를 FFmpeg filter chain으로 변환하므로 Preview와 최종 렌더링이 같은 편집 상태를
공유합니다.

고해상도 영상에서 Preview 때문에 메모리와 CPU 사용량이 과도해지지 않도록 화면용 frame은
최대 크기를 제한합니다. Standard Upscale 2x / 4x는 화면의 구도나 비율을 바꾸지 않으므로
Preview에서 거대한 2x/4x bitmap을 만들지 않고, 실제 출력 pixel 수는 Save 시 FFmpeg에서
적용합니다.

Trim이 Pending 상태이면 Play 시 Trim 시작 위치 밖에 있을 경우 자동으로 Start로 이동하고,
End에 도달하면 pause 후 Start로 돌아갑니다.

## 현재 구현 범위

- Dark desktop UI
- 여러 media file import
- Media Library
  - `+ Add`, `Import Media`, `Ctrl+O`, Drag & Drop
  - `− Remove` 또는 `Delete`로 project에서 제거
  - Remove는 disk 원본 파일을 삭제하지 않음
- PNG / JPG / JPEG
- WebM / MP4
- 영상 선택 직후 첫 frame 자동 Preview
- Video Play / Pause / Seek
- Pending edit live preview
  - Crop 즉시 반영
  - Rotate 즉시 반영
  - Resize 즉시 반영
  - Trim 구간 playback 반영
  - Upscale은 예상 출력 해상도만 유지하고 화면 구성은 동일
- 비파괴 Pending edit workflow
  - Trim / Crop / Rotate / Resize / Upscale 누적
  - 하단에서 Pending edits 표시
  - `Reset edits`
  - `Save As…` / `Ctrl+Shift+S`
  - 추천 이름 `<원본이름>_edited.mp4` 또는 `<원본이름>_edited.png`
  - Save dialog에서 이름과 저장 폴더 수정 가능
- Trim GUI
  - dialog에서 실제 영상 재생 / seek
  - Start / End 지정
- Crop GUI
  - 실제 frame에서 drag로 영역 생성
  - 내부 drag로 이동
  - 모서리 handle resize
  - `Ctrl + Wheel` zoom
  - 가운데 휠 버튼 drag pan
  - 선택 영역 맞춤 / 전체 보기
  - 자유 / 원본 / 16:9 / 4:3 / 1:1
  - X / Y / Width / Height 직접 수정
- Resize
  - Original / 1080p / 720p / 480p / 360p / Custom
  - aspect ratio 유지
- Rotate
  - 90° clockwise / 180° / 90° counter-clockwise
- Standard Upscale
  - 2x / 4x Lanczos
- Sequence / Concat
  - WebM / MP4 append
  - drag로 순서 변경
  - 서로 다른 해상도는 첫 clip canvas 기준으로 aspect ratio 유지 후 정규화
  - audio 없는 clip에는 같은 길이의 silence 생성
- FFmpeg output
  - Video: H.264 (`libx264`) + AAC / MP4
  - Image: PNG
  - 홀수 해상도는 마지막에 최대 1 px padding
- FFmpeg는 `QProcess`로 실행하여 GUI thread를 block하지 않음
- Save 결과를 Media Library에 자동 추가
- `Ctrl+C` (`SIGINT`) / `SIGTERM` 안전 종료

## Save workflow

예:

```text
input.webm
  ├─ Trim: 2.0 s ~ 18.5 s
  ├─ Crop: 1200 x 800
  ├─ Rotate: 90°
  ├─ Resize: 1280 x 720
  └─ Upscale: 2x
```

각 dialog에서 `OK`를 누르면 파일 대신 편집 상태가 갱신되고 메인 Preview도 새 상태로
갱신됩니다.

```text
Pending edits: Trim 2.000-18.500s · Crop 1200x800 · Rotate 90° · Resize 1280x720 · Upscale 2x
```

마지막에 `Save As…`를 누르면 기본적으로 다음 이름을 제안합니다.

```text
input_edited.mp4
```

Save dialog에서 `experiment_result.mp4`처럼 파일명과 폴더를 자유롭게 변경할 수 있습니다.
Save 성공 후 결과 파일을 Media Library에 추가합니다.

## Preview와 Save의 역할

```text
QMediaPlayer
    ↓
QVideoSink
    ↓
QImage 빠른 Preview 변환
    ↓
사용자 확인

EditState
    ↓
Save As
    ↓
FFmpeg one-pass filter chain
    ↓
최종 MP4 / PNG
```

Preview는 인터랙션을 위한 빠른 화면 표시이고 Save는 실제 품질의 렌더링입니다. 두 경로는
동일한 `EditState`를 사용합니다.

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
    +-- Live Preview
    |       |-- QMediaPlayer
    |       |-- QVideoSink
    |       |-- QVideoFrame.toImage()
    |       +-- preview_transform.py
    |
    +-- Edit Dialogs
    |       |-- Trim playback
    |       |-- Crop + Zoom + Pan
    |       |-- Resize
    |       |-- Rotate
    |       +-- Upscale
    |
    +-- FFmpeg
            |-- one-pass Save pipeline
            |-- H.264 / AAC MP4
            +-- Sequence / Concat
```

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

## 주요 사용법

### Trim

1. 영상 선택
2. `Trim`
3. dialog에서 재생 / seek
4. Start / End 설정
5. `OK`
6. 메인 재생도 해당 구간으로 제한
7. 다른 편집 후 `Save As…`

### Crop

1. 원하는 frame으로 seek
2. `Crop`
3. 왼쪽 drag로 rectangle 생성
4. 내부 drag로 이동 / handle로 resize
5. `Ctrl + Wheel` zoom, 가운데 휠 drag pan
6. `OK`
7. 메인 Preview에 Crop 결과 즉시 반영

### Resize / Rotate

`OK` 후 메인 Preview가 즉시 새 화면 비율 / 회전 상태로 갱신됩니다.

### Upscale

2x / 4x 출력 해상도는 Pending 상태와 최종 Save에 반영됩니다. 화면의 구도 자체는 동일하므로
메인 Preview에서 거대한 2x / 4x frame을 만들지는 않습니다.

### Reset edits

원본 파일을 변경하지 않고 현재 파일에 쌓인 Pending edits를 제거하고 Preview를 원본 상태로
되돌립니다.

### Save As

1. 편집을 모두 설정
2. `Save As…` 또는 `Ctrl+Shift+S`
3. 추천된 `_edited` 이름 확인
4. 필요하면 이름 / 폴더 수정
5. FFmpeg가 누적 편집을 한 번에 렌더링

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
- Windows: 동일한 PySide6 + FFmpeg 구조
- OS별 GitHub Actions runner에서 release build
- 초기 release: portable executable / bundle
- 이후 Windows installer와 Linux AppImage 또는 `.deb`

FFmpeg executable bundle은 라이선스와 배포 조건을 확인한 뒤 packaging 단계에서 결정합니다.
현재 development 환경에서는 system FFmpeg를 사용합니다.

## Roadmap

1. Timeline usability
   - 좌/우 화살표 frame step
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
