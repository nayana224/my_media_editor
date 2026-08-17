# Media Editor

Windows와 Ubuntu에서 이미지와 영상을 Preview하면서 편집하고 변환하는 PySide6 + FFmpeg 기반 데스크톱 앱입니다.

## 현재 버전

`v0.1.0` release 준비 단계입니다.

현재 주요 기능:

- PNG / JPG / JPEG / WebM / MP4 import
- 여러 media를 관리하는 Media Library
- 영상 첫 frame 자동 Preview
- Trim / Crop / Resize / Rotate / Upscale / Speed
- Pending edit 기반 비파괴 편집
- Unified Live Preview
- Edited Timeline
- `Save As…` one-pass FFmpeg render
- WebM → MP4
- Sequence / Concat
- Drag & Drop
- Ubuntu / Windows standalone package build

자세한 변경 이력은 [CHANGELOG.md](CHANGELOG.md)를 확인하세요.

## 편집 방식

단일 미디어의 편집은 버튼을 누를 때마다 중간 파일을 만들지 않습니다.

```text
Trim → Crop → Rotate → Resize → Upscale → Speed → Save
```

각 값은 원본에 대한 Pending edit으로 유지되며, `Save As…`에서 FFmpeg를 한 번만 실행해 최종 파일을 만듭니다.

각 dialog와 메인 화면은 같은 `EditState`를 사용합니다.

```text
현재 Pending edits
      +
현재 dialog의 임시 값
      ↓
Live Preview
      ↓
OK
      ↓
메인 Preview 갱신
      ↓
Save As…
```

`Cancel`은 dialog에서 조절 중이던 임시 값을 Pending state에 기록하지 않습니다.

## Edited Timeline

메인 Timeline은 원본의 절대 시간이 아니라 최종 편집 결과의 시간축을 표시합니다.

예:

```text
원본: 32.200 s
Trim: 6.696 → 32.200 s
Speed: 2.00x

Edited Timeline:
00:00.000 → 00:12.752
```

Timeline에서 seek하면 내부적으로 원본 source position으로 변환해 올바른 frame으로 이동합니다.

## 주요 편집 UX

### Trim

- 실제 편집 상태 영상을 재생하면서 Start / End 설정
- 현재 Crop / Rotate / Resize 반영
- Pending Speed 반영
- Start / End slider
- `Start = 현재 위치`, `End = 현재 위치`, `전체 길이`

### Crop

- 원본 pixel 좌표계 유지
- 왼쪽 drag로 새 영역 생성
- 영역 내부 drag로 이동
- 모서리 handle resize
- `Ctrl + Wheel` zoom
- 가운데 휠 버튼 drag pan
- 자유 / 원본 / 16:9 / 4:3 / 1:1 aspect
- Final Preview에서 전체 Pending pipeline 확인

### Resize

- Original / 1080p / 720p / 480p / 360p preset
- Width / Height 직접 입력
- aspect ratio 유지
- 변경 즉시 Live Preview

### Rotate

- 원형 Dial
- 0° / 90° / 180° / 270° quick preset
- 90° 단위 snap
- 변경 즉시 Live Preview

### Upscale

- Standard Lanczos 2x / 4x
- 최종 예상 출력 해상도 표시
- Preview 성능을 위해 실제 초대형 bitmap 생성은 생략

### Speed

- 0.25x ~ 4.00x slider
- 0.5x / 1x / 1.5x / 2x / 4x quick preset
- 실제 영상 Play / Pause / Seek
- slider 변경 즉시 playback rate 반영
- Save 시 video `setpts` + audio `atempo`

## Sequence / Concat

- WebM / MP4 여러 clip append
- drag로 순서 변경
- 서로 다른 해상도는 첫 clip canvas 기준으로 aspect ratio 유지 후 정규화
- audio 없는 clip에는 같은 길이의 silence 생성

## 개발 환경 실행

Ubuntu 22.04:

```bash
cd ~/inpyo_ws/my_media_editor
git pull origin main
./scripts/setup.sh
./scripts/run.sh
```

`setup.sh`는 `source`하지 않습니다.

검증:

```bash
./scripts/check.sh
```

Terminal 실행 중 `Ctrl+C`를 보내면 재생과 FFmpeg child process를 정리한 뒤 종료합니다.

## 다운로드용 앱 빌드

현재 다음 package를 생성하도록 준비되어 있습니다.

```text
Ubuntu 22.04 x86_64
  → MyMediaEditor-0.1.0-x86_64.AppImage

Windows x64
  → MyMediaEditor-0.1.0-windows-x64.zip
     └─ MyMediaEditor.exe
```

Python / PySide6 standalone executable은 Qt 공식 `pyside6-deploy`로 생성합니다.

자세한 local build, GitHub Actions, GitHub Release 절차와 FFmpeg packaging 정책은 [docs/packaging.md](docs/packaging.md)를 확인하세요.

### GitHub Actions에서 받기

1. repository의 `Actions` 탭
2. `Build desktop packages`
3. `Run workflow`
4. 완료된 run의 `Artifacts`에서 Linux / Windows package 다운로드

`v*` tag를 push하면 두 OS build 성공 후 GitHub Release에 artifact를 자동 첨부하도록 workflow가 구성되어 있습니다.

## FFmpeg dependency

현재 `v0.1.0` package는 앱 자체의 standalone 배포를 먼저 검증하기 위해 FFmpeg / FFprobe binary를 포함하지 않습니다.

Ubuntu:

```bash
sudo apt update
sudo apt install -y ffmpeg
```

Windows에서는 `ffmpeg.exe`, `ffprobe.exe`가 PATH에서 실행 가능해야 합니다.

runtime은 향후 bundled FFmpeg를 바로 사용할 수 있도록 AppImage의 `$APPDIR/usr/bin`, executable 옆 `bin/`, system PATH 순으로 외부 tool 경로를 지원합니다.

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
    |       |-- QMediaPlayer
    |       |-- QVideoSink
    |       |-- QVideoFrame → QImage
    |       +-- dialog temporary override
    |
    +-- Edited Timeline
    |       +-- edited time ↔ source time mapping
    |
    +-- FFmpeg
    |       |-- one-pass Save
    |       +-- Sequence / Concat
    |
    +-- runtime_tools
    |       +-- packaged executable / system tool resolution
    |
    +-- Packaging
            |-- pyside6-deploy
            |-- Linux AppImage
            +-- Windows portable ZIP
```

## 문서

- [Packaging and Release](docs/packaging.md)
- [Changelog](CHANGELOG.md)

## Roadmap

1. Ubuntu AppImage clean-machine smoke test
2. Windows 10 / 11 portable smoke test
3. FFmpeg / FFprobe bundle license 조건 확정 및 bundle 적용
4. Timeline frame-step / J-K-L / marker / snap
5. Side-by-side / Top-bottom / 2x2 Grid compose
6. Export progress / cancel
7. 고해상도 source용 proxy preview
8. AI Upscale
9. Windows installer와 code signing 검토

기능이나 배포 방식이 변경되면 코드와 함께 README 및 기준 문서를 갱신합니다.
