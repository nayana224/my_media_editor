# Media Editor

Windows와 Ubuntu에서 이미지와 영상을 빠르게 preview하고 편집하기 위한
PySide6 + FFmpeg 기반 데스크톱 앱입니다.

## 현재 구현 범위

- Dark desktop UI
- 여러 media file import
- Media Library
  - 여러 file 추가
  - `+ Add`로 file 추가
  - `− Remove` 또는 `Delete` key로 project에서 file 제거
  - 제거는 project 목록에서만 수행하며 원본 file은 삭제하지 않음
- 여러 file Drag & Drop
- PNG / JPG / JPEG preview
- WebM / MP4 preview
- Video Play / Pause
- Timeline seek
- `Ctrl+O` media import
- Video Trim
  - Start / End를 각각 slider로 조절
  - 시간 값을 초 단위로 직접 입력 가능
  - 현재 preview 위치를 Start 또는 End로 바로 지정
  - `Start = 0`, `End = 끝`, `전체 길이` 빠른 설정
  - 선택 구간 길이를 dialog에서 즉시 표시
  - Trim 결과를 H.264 / AAC MP4로 출력
- Crop
  - Image / Video 모두 지원
  - 현재 preview를 보면서 crop 영역을 마우스로 직접 선택
  - 선택 영역 내부 drag로 위치 이동
  - 네 모서리 handle drag로 크기 조절
  - 자유 / 원본 비율 / 16:9 / 4:3 / 1:1 aspect preset
  - `가운데 80%`, `전체 프레임` 빠른 선택
  - X / Y / Width / Height pixel 값을 함께 표시하고 직접 수정 가능
- Resize
  - Image / Video 모두 지원
  - Original / 1080p / 720p / 480p / 360p preset
  - Custom width / height 입력
  - 가로세로 비율 유지 option
  - 최종 출력 크기와 원본 대비 scale 표시
- Rotate
  - Image / Video 모두 지원
  - 90° clockwise / 180° / 90° counter-clockwise를 radio button으로 바로 선택
- Standard Upscale 2x / 4x
  - 전용 GUI에서 2x / 4x 선택
  - Image: Lanczos scale 후 PNG 출력
  - Video: Lanczos scale 후 H.264 / AAC MP4 출력
- MP4 Export
  - WebM -> MP4 변환
  - MP4 -> 호환성 높은 H.264 / AAC MP4 재출력
  - 입력 파일과 동일 경로로 저장하는 동작 차단
- FFmpeg video output 공통 처리
  - H.264 (`libx264`) + AAC
  - `yuv420p`
  - timestamp passthrough (`-vsync 0`)
  - 홀수 해상도 입력은 최대 1 px padding
- FFmpeg 작업은 `QProcess`로 실행하여 GUI thread를 block하지 않음
- 편집 결과를 Media Library에 자동 추가하고 결과 file을 자동 선택

Sequence / Concat, Layout Compose, Export progress / cancel, AI Upscale은 이후 단계에서
구현합니다. AI Upscale은 Real-ESRGAN 계열 backend를 별도 검토합니다.

## Architecture

현재 project는 여러 media asset을 보관하는 `MediaProject`를 기준으로 동작합니다.
GUI preview는 Qt Multimedia를 사용하고 실제 변환/렌더링 작업은 FFmpeg backend로
분리합니다.

```text
PySide6 GUI
    |
    +-- MediaProject / MediaAsset
    |       +-- Add / Remove
    |
    +-- Qt Multimedia  -> Preview / Seek
    |
    +-- Edit Dialogs
    |       |-- Trim slider
    |       |-- Interactive Crop selection
    |       |-- Resize preset / custom
    |       |-- Rotate
    |       +-- Upscale
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

FFmpeg 작업은 현재 하나의 active job만 허용합니다. 편집이나 export 중에는 다른 FFmpeg
작업과 Media Library 변경 버튼을 잠가 동일 source에 대한 동시 변환을 방지합니다.

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

## Media Library 사용법

- 상단 `Import Media`, 왼쪽 `+ Add`, `Ctrl+O`, Drag & Drop 중 하나로 file을 추가합니다.
- Media Library에서 항목을 선택하면 preview가 전환됩니다.
- 선택한 항목을 `− Remove` 또는 `Delete` key로 project에서 제거할 수 있습니다.
- Remove는 disk의 실제 원본 file을 삭제하지 않습니다.

## Video Trim 사용법

1. Media Library에서 WebM 또는 MP4를 선택합니다.
2. preview를 재생하거나 timeline에서 원하는 위치로 이동합니다.
3. `Trim`을 누릅니다.
4. Start / End slider를 움직여 남길 구간을 지정합니다.
5. 필요하면 시간 입력란에 초 단위 값을 직접 입력합니다.
6. `현재 위치 사용`을 누르면 Trim dialog를 열기 직전의 preview 위치가 적용됩니다.
7. `Start = 0`, `End = 끝`, `전체 길이` 버튼으로 빠르게 범위를 초기화할 수 있습니다.
8. dialog 하단에서 최종 선택 영상 길이를 확인하고 실행합니다.
9. 원본과 같은 폴더에 `*_trimmed.mp4`가 생성됩니다.

Trim은 stream copy가 아니라 H.264 / AAC로 재인코딩합니다. 따라서 keyframe 위치에만
의존하지 않고 사용자가 지정한 구간을 정확하게 자르는 것을 우선합니다.

## Crop / Resize / Rotate

### Crop

`Crop`을 누르면 현재 preview가 큰 편집 canvas로 열립니다.

- 빈 영역에서 drag: 새 crop 영역 생성
- 선택 영역 안에서 drag: crop 영역 이동
- 네 모서리의 흰색 handle drag: 크기 조절
- 3등분 guide line으로 화면 구도 확인
- 자유 / 원본 비율 / 16:9 / 4:3 / 1:1 aspect preset
- `가운데 80%`, `전체 프레임` 빠른 선택
- 정확한 좌표가 필요하면 X / Y / Width / Height 값을 직접 수정

선택 영역의 크기, 위치, 원본 대비 면적 비율도 dialog에서 바로 확인할 수 있습니다.

Video crop은 `Crop`을 누른 시점의 현재 preview frame을 기준으로 영역을 선택하며,
선택한 pixel 좌표는 전체 영상 frame에 동일하게 적용됩니다.

### Resize

`Resize`에서 preset 해상도를 선택하거나 custom width / height를 입력할 수 있습니다.
`가로세로 비율 유지`가 켜져 있으면 원본 aspect ratio를 유지하면서 preset 영역 안에
들어가는 최대 크기를 계산합니다. dialog 하단에서 최종 출력 크기와 원본 대비 scale을
확인할 수 있습니다.

### Rotate

`Rotate` dialog에서 90° clockwise, 180°, 90° counter-clockwise 중 하나를 바로 선택합니다.

Image 편집 결과는 PNG, Video 편집 결과는 H.264 / AAC MP4로 생성합니다. 원본은
덮어쓰지 않고 `_cropped`, `_resized`, `_rotated` suffix를 붙입니다.

## Upscale

`Upscale` dialog에서 Standard 2x 또는 4x를 선택합니다. 현재 Standard Upscale은 Lanczos
filter 기반이며 AI 복원 기능은 아닙니다. AI Upscale은 추후 Real-ESRGAN backend로
별도 추가할 예정입니다.

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

1. 여러 video를 시간 순서로 붙이는 Sequence / Concat
2. Side-by-side / Top-bottom / 2x2 Grid layout compose
3. Export progress / cancel
4. AI Upscale
5. Windows / Ubuntu packaging 및 GitHub Release 자동화

기능 추가 시 README의 현재 구현 범위, 사용법, architecture와 roadmap도 함께 갱신합니다.
