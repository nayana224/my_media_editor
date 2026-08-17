# Media Editor

Windows와 Ubuntu에서 이미지와 영상을 preview하면서 편집하기 위한 PySide6 + FFmpeg 기반 데스크톱 앱입니다.

## 핵심 편집 방식

단일 미디어의 `Trim`, `Crop`, `Rotate`, `Resize`, `Upscale`, `Speed`는 버튼을 누를 때마다 파일을 만들지 않습니다. 각 편집 값은 원본에 대한 **Pending edits**로 누적되고, `Save As…`에서 FFmpeg를 한 번만 실행해 최종 파일을 만듭니다.

최종 렌더 순서는 항상 다음과 같습니다.

```text
Trim → Crop → Rotate → Resize → Upscale → Speed → Save
```

중간 MP4/PNG 파일을 만들지 않고 반복 재인코딩을 피합니다. Media Library에서 다른 파일로 이동해도 각 파일의 Pending edits는 독립적으로 유지됩니다.

## Unified Live Preview 원칙

모든 편집 기능은 같은 원칙을 사용합니다.

```text
현재 Pending edits
      +
지금 dialog에서 조절 중인 임시 값
      ↓
최종 pipeline 순서로 Preview 재계산
      ↓
사용자가 바로 확인
```

즉, `Crop → Rotate → Resize → Speed`처럼 이어서 작업해도 이후 dialog는 항상 앞에서 설정한 편집을 포함한 최신 결과를 보여줍니다.

- Trim: 현재 Crop / Rotate / Resize와 Speed를 반영한 영상을 재생하면서 Start / End 설정
- Crop: 원본 좌표계에서 안전하게 영역을 선택하면서 별도의 **Final Preview**에 전체 누적 결과 즉시 표시
- Resize: 현재 누적 상태 위에서 Width / Height 변경을 즉시 Preview
- Rotate: Dial을 움직일 때 전체 누적 결과를 포함해 즉시 Preview
- Upscale: 현재 최종 구도를 그대로 보여주고 2x / 4x 예상 출력 해상도를 표시
- Speed: 현재 편집 상태의 영상을 실제 playbackRate로 재생
- OK 후 메인 Preview도 즉시 같은 Pending 상태로 갱신
- Cancel은 dialog 임시 값을 Pending state에 기록하지 않음

Preview는 `QMediaPlayer → QVideoSink → QVideoFrame → QImage` 경로로 frame을 받아 빠르게 계산합니다. 최종 Save는 같은 `EditState`를 FFmpeg one-pass pipeline으로 변환하므로 Preview와 최종 렌더가 같은 편집 상태를 공유합니다.

고해상도 source에서는 Preview용 bitmap 크기를 제한해 UI 성능을 유지합니다. 최종 저장 해상도에는 영향을 주지 않습니다.

## Edited Timeline

메인 재생 슬라이더는 원본 파일의 절대 시간이 아니라 **현재 편집 결과의 시간축**을 표시합니다.

예를 들어 원본이 `32.200s`이고 다음 Trim이 있으면:

```text
Trim: 6.696s → 32.200s
```

메인 timeline은 다음처럼 자동으로 다시 맞춰집니다.

```text
00:00.000 ├────────────────────────────┤ 00:25.504
```

여기에 `Speed 2.00x`를 적용하면 결과 영상 길이가 절반이므로 즉시 다음처럼 바뀝니다.

```text
00:00.000 ├────────────────────────────┤ 00:12.752
```

내부 `QMediaPlayer`는 원본 source 위치를 사용하지만 UI는 `timeline_model.py`에서 다음 변환을 사용합니다.

```text
Edited time = (Source time - Trim start) / Speed
Source time = Trim start + Edited time × Speed
```

따라서 편집 결과 timeline에서 5초 위치로 seek해도 실제 source의 올바른 frame으로 이동합니다.

- Trim 변경 즉시 timeline 시작을 0으로 재기준화
- Speed 변경 즉시 timeline 전체 길이 갱신
- Reset edits 시 원본 전체 길이로 복원
- Media 선택 변경 시 해당 파일의 Pending Trim / Speed 기준으로 복원
- 현재 시간 / 전체 시간을 `MM:SS.mmm`으로 표시
- timeline tooltip에는 source 구간과 현재 Speed를 표시

이 규칙은 이후 frame-step, marker, snap 기능에서도 공통 기준으로 사용합니다.

## 현재 구현 기능

- Dark desktop UI
- PNG / JPG / JPEG / WebM / MP4 input
- 여러 media import
- Media Library
  - `+ Add`, `Import Media`, `Ctrl+O`, Drag & Drop
  - `− Remove` / `Delete`로 project에서 제거
  - disk 원본 파일은 삭제하지 않음
- 영상 선택 직후 첫 frame 자동 Preview
- Play / Pause / Edited Timeline Seek
- Unified Pending edit live preview
- `Reset edits`
- `Save As…` / `Ctrl+Shift+S`
- 추천 파일명 `<원본이름>_edited.mp4` / `<원본이름>_edited.png`
- Sequence / Concat
- `Ctrl+C` / `SIGTERM` 안전 종료

## Trim

Trim dialog 자체에서 영상을 재생하고 seek할 수 있습니다.

- Start / End slider
- 초 단위 직접 입력
- `Start = 현재 위치`
- `End = 현재 위치`
- `전체 길이`
- 기존 Crop / Rotate / Resize가 Preview에 그대로 적용
- Pending Speed가 있으면 Trim Preview도 같은 배속으로 재생
- 선택한 원본 구간 길이와 Speed 적용 후 예상 길이 표시
- OK 후 메인 timeline은 선택 구간을 `0 → 결과 길이`로 다시 표시

## Crop

Crop 좌표는 FFmpeg Save와 동일하게 **원본 pixel 좌표계**에서 유지합니다.

작업 canvas:

- 왼쪽 drag: 새 crop 영역 생성
- 영역 내부 drag: crop 영역 이동
- 모서리 handle: 크기 조절
- `Ctrl + Wheel`: 확대 / 축소
- 가운데 휠 버튼 drag: 화면 pan
- `선택 영역 맞춤`
- `전체 보기`
- 자유 / 원본 / 16:9 / 4:3 / 1:1 aspect
- X / Y / Width / Height 직접 수정

별도의 **Final Preview**는 현재 crop rectangle을 임시 적용한 뒤 기존 Rotate / Resize 등 전체 Pending pipeline을 즉시 다시 계산해서 보여줍니다.

## Rotate

Rotate는 원형 Dial + quick preset 방식입니다.

- Dial drag
- `0°`, `↻ 90°`, `180°`, `↺ 90°` quick preset
- 90° 단위 snap
- Dial 변경 즉시 전체 Pending pipeline Preview 갱신
- 0° 선택 시 Pending Rotate 제거

## Resize

- Original / 1080p / 720p / 480p / 360p preset
- Width / Height 직접 입력
- aspect ratio 유지
- 수치 변경 즉시 전체 Pending pipeline Preview 갱신
- 원래 크기로 복원하면 Pending Resize 제거

## Upscale

- Standard Lanczos 2x / 4x
- 현재 Crop / Rotate / Resize 결과를 그대로 Preview
- 예상 최종 출력 pixel 수 즉시 표시
- Preview에서는 성능을 위해 실제 2x / 4x 초대형 bitmap을 만들지 않음
- 실제 upscale은 Save 시 FFmpeg에서 적용

## Speed

Speed dialog 안에서 현재 편집 결과 영상을 직접 재생하면서 배속을 조절합니다.

- 0.25x ~ 4.00x slider
- 0.5x / 1x / 1.5x / 2x / 4x quick preset
- 0.05x 단위 숫자 입력
- Play / Pause / Seek
- 최신 Pending 화면 상태 표시
- slider 변경 즉시 실제 playbackRate 변경
- OK 후 메인 player와 Edited Timeline도 같은 speed로 갱신
- 미디어를 다시 선택해도 Pending Speed 복원
- Cancel 시 기존 속도 복원
- 1.00x 선택 시 Pending Speed 제거
- 예상 출력 길이 표시

최종 Save에서는 video에 `setpts`를 적용하고 audio에는 FFmpeg `atempo`를 사용합니다. 0.25x와 4x 경계에서는 여러 `atempo` filter를 연결합니다.

## 연속 편집 예

```text
input.mp4
  ↓ Crop
Final Preview + 메인 Preview 갱신
  ↓ Rotate 90°
Crop + Rotate 결과 즉시 표시
  ↓ Resize 1280×720
Crop + Rotate + Resize 결과 즉시 표시
  ↓ Speed 1.5x
같은 최종 화면을 실제 1.5x로 재생 + timeline 길이 갱신
  ↓ Trim
같은 화면 + 1.5x 속도로 구간 선택
  ↓ Edited Timeline
선택된 최종 결과 길이를 0초부터 표시
  ↓ Save As…
input_edited.mp4
```

## Save workflow

1. 원하는 편집들을 설정
2. 각 dialog와 메인 Preview에서 누적 결과 확인
3. 메인 Edited Timeline에서 최종 재생 길이와 seek 동작 확인
4. `Save As…` 또는 `Ctrl+Shift+S`
5. 추천된 `_edited` 이름 확인
6. 필요하면 파일명 / 저장 폴더 수정
7. FFmpeg가 모든 Pending edit을 한 번에 렌더링
8. 결과 파일을 Media Library에 자동 추가

Video output:

- MP4
- H.264 (`libx264`)
- AAC
- 홀수 해상도는 마지막에 최대 1 px padding

Image output: PNG

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
    +-- Unified Live Preview
    |       |-- source frame
    |       |-- copied EditState
    |       |-- dialog temporary override
    |       |-- preview_transform.py
    |       +-- live_edit_dialogs.py
    |
    +-- Edited Timeline
    |       |-- timeline_model.py
    |       |-- Trim rebase to 0
    |       |-- Speed duration mapping
    |       +-- edited time ↔ source time seek
    |
    +-- Video Preview
    |       |-- QMediaPlayer
    |       |-- QVideoSink
    |       |-- QVideoFrame.toImage()
    |       +-- playbackRate
    |
    +-- FFmpeg
            |-- one-pass Save pipeline
            |-- setpts + atempo
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
