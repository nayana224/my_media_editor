# Ubuntu 24 수동 확인 가이드

## 1. 확인할 실행 파일

PR의 최신 성공 Actions 실행에서 `linux-x86_64` artifact를 다운로드하고 ZIP을 풉니다.
그 안의 `MyMediaEditor-0.1.2-x86_64.AppImage`는 Ubuntu 22.04에서 만든 배포본입니다.
Ubuntu 24에서 소스를 실행하거나 직접 다시 빌드한 결과와 혼동하지 마세요.

AppImage를 보관한 폴더에서 터미널을 열어 실행합니다.

```bash
chmod +x MyMediaEditor-0.1.2-x86_64.AppImage
APPIMAGE_EXTRACT_AND_RUN=1 ./MyMediaEditor-0.1.2-x86_64.AppImage
```

`APPIMAGE_EXTRACT_AND_RUN=1`은 FUSE 설치 없이 실행하도록 합니다.
실제 화면을 확인할 때는 `QT_QPA_PLATFORM=offscreen`을 설정하지 않습니다.
Python, PySide6, FFmpeg를 추가 설치하지 않습니다.

## 2. 자동 진단 먼저 실행

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./MyMediaEditor-0.1.2-x86_64.AppImage \
  --self-test --self-test-report "$PWD/ubuntu24-check.json"
echo $?
```

종료 코드가 `0`, JSON의 `status`가 `passed`이면 자동 진단 통과입니다.
창이 잠깐 보였다 닫힐 수 있습니다. 진단 후에는 위의 일반 실행 명령으로 앱을 다시 엽니다.
이 진단은 이미지 저장, MP4/WebM 변환·프레임 디코딩, 무음 영상을 섞은 합치기와 한글 경로를 확인합니다.
스피커에서 실제 소리가 나는지와 사용자 조작은 아래에서 따로 확인합니다.

## 3. 화면에서 확인할 항목 (약 10분)

원본을 덮어쓰지 않도록 확인용 미디어 복사본과 새 출력 폴더를 준비합니다.
PNG/JPG 1개, 소리 있는 MP4 1개, WebM 1개, 소리 없는 MP4 1개면 충분합니다.

| 순서 | 조작 | 정상 결과 |
| --- | --- | --- |
| 1 | 앱을 열고 창 크기를 늘리고 줄이기 | 글자·버튼이 잘리지 않고 한글이 보임 |
| 2 | Import Media로 이미지와 영상을 불러오기 | 목록과 첫 화면이 표시됨 |
| 3 | 파일 관리자에서 파일을 앱으로 끌어놓기 | 동일하게 가져오기 성공 |
| 4 | MP4와 WebM 각각 재생·일시정지·탐색 | 화면이 정상이며 소리 있는 영상의 소리가 들림 |
| 5 | 영상 Trim, Speed 0.5x/2x 조절 | 선택 구간·재생 속도가 반영됨 |
| 6 | Crop, Rotate, Resize 적용 후 Cancel 및 OK | Cancel은 기존 상태 유지, OK는 편집 상태 반영 |
| 7 | Save As로 새 MP4 및 PNG 저장 | 파일이 생성되고 앱 또는 다른 재생기로 열림 |
| 8 | 소리 있는 MP4와 무음 MP4를 Sequence로 합치기 | 지정 순서로 재생되고 무음 구간은 무음 유지 |
| 9 | 공백·한글이 포함된 폴더에서 가져오기·저장 | 예: `편집 확인/결과 영상.mp4`에서 성공 |
| 10 | 영상 재생 중 앱 종료 후 다시 열기 | 창이 닫히고 재실행 가능, 잔여 변환 작업 없음 |

저장된 결과는 앱에서 다시 불러와 해상도·회전·길이를 확인하고, Ubuntu 기본 영상 재생기로도 재생해 봅니다.
작업 중 오류 대화상자, 검은 화면, 화면 깨짐, 소리 끊김이 있었는지 기록합니다.

## 4. X11과 Wayland

현재 세션은 터미널에서 확인할 수 있습니다.

```bash
echo "$XDG_SESSION_TYPE"
```

`x11` 또는 `wayland`가 표시됩니다. 먼저 현재 로그인 세션에서 위 항목을 확인합니다.
다른 세션도 검사하려면 저장 중인 작업을 모두 끝낸 뒤 로그아웃하고, 로그인 화면에서 사용자를 선택한 후
톱니바퀴 메뉴에 제공되는 `Ubuntu` 또는 `Ubuntu on Xorg` 세션을 선택합니다.
현재 시스템이 해당 선택지를 제공할 때만 전환하세요. 다른 세션을 확인하지 못했다면 미확인으로 기록합니다.

Wayland 세션에서 네이티브 Wayland를 명시해 검사할 때는 다음 명령을 사용합니다.

```bash
QT_QPA_PLATFORM=wayland APPIMAGE_EXTRACT_AND_RUN=1 ./MyMediaEditor-0.1.2-x86_64.AppImage
```

X11 또는 Wayland 세션의 XWayland 경로를 검사할 때는 다음 명령을 사용합니다.

```bash
QT_QPA_PLATFORM=xcb APPIMAGE_EXTRACT_AND_RUN=1 ./MyMediaEditor-0.1.2-x86_64.AppImage
```

X11 세션에서 `QT_QPA_PLATFORM=wayland`를 설정하는 것은 유효한 Wayland 검증이 아닙니다.
CI의 Xvfb 검증도 실제 Wayland나 스피커 검증을 대신하지 않습니다.

## 5. 문제가 생기면 남길 정보

실행 로그를 남기려면 다음처럼 실행합니다.

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./MyMediaEditor-0.1.2-x86_64.AppImage > ubuntu24-app.log 2>&1
```

Ubuntu 버전, `XDG_SESSION_TYPE` 결과, 어떤 파일에 어떤 조작을 했는지,
기대한 결과와 실제 결과, 자동 진단 JSON 및 로그를 함께 남깁니다.
원본 미디어에 개인정보가 있으면 파일 자체 대신 형식·해상도·길이만 알려 주세요.
