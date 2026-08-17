# Media Editor

Ubuntu에서 이미지와 영상을 빠르게 preview하고 편집하기 위한
PySide6 기반 데스크톱 앱입니다.

## 현재 구현 범위

- Dark desktop UI
- Drag & Drop
- PNG / JPG / JPEG preview
- WebM / MP4 preview
- Video Play / Pause
- Timeline seek
- `Ctrl+O` 파일 열기

`Trim`, `Crop`, `Rotate`, `Resize`, `Export` 버튼은 다음 개발 단계에서
구현할 기능이며 현재는 의도적으로 비활성화되어 있습니다.

## Workspace

```bash
mkdir -p ~/inpyo_ws
cd ~/inpyo_ws
unzip media_editor.zip
cd media_editor
```

## Setup

`setup.sh`는 현재 shell에 source하지 않습니다.

```bash
cd ~/inpyo_ws/media_editor
./scripts/setup.sh
```

## Run

```bash
cd ~/inpyo_ws/media_editor
./scripts/run.sh
```

## Check

```bash
cd ~/inpyo_ws/media_editor
./scripts/check.sh
```

## 지원 형식

Image:

- PNG
- JPG
- JPEG

Video:

- WebM
- MP4

영상 preview는 Qt Multimedia를 사용합니다. Linux의 실제 codec/backend
지원 여부는 설치된 Qt Multimedia 환경과 영상 codec에 따라 달라질 수 있습니다.

## 다음 단계

1. Image rotate / crop / resize
2. Video trim
3. Video crop / resize
4. Export via FFmpeg
5. Export progress / cancel
