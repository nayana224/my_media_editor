# Packaging and Release

이 문서는 My Media Editor의 Ubuntu / Windows 배포 기준 문서입니다.

## 지원 배포 형태

v0.1.0 기준으로 다음 artifact를 생성합니다.

```text
Ubuntu 22.04 x86_64
  → MyMediaEditor-0.1.0-x86_64.AppImage

Windows x64
  → MyMediaEditor-0.1.0-windows-x64.zip
     └─ MyMediaEditor.exe
```

Python과 PySide6를 사용자 PC에 별도로 설치할 필요가 없도록 Qt 공식 `pyside6-deploy`로 standalone executable을 생성합니다.

Linux standalone executable은 AppDir에 넣은 뒤 `linuxdeploy`로 AppImage를 생성합니다.

## FFmpeg 정책

v0.1.0 release artifact에는 FFmpeg / FFprobe binary를 포함하지 않습니다.

이유는 앱 코드와 패키징 안정성을 먼저 검증하고, FFmpeg binary 재배포 시 필요한 license / source 제공 조건을 명확히 정리한 뒤 bundle하기 위해서입니다.

현재 runtime은 다음 순서로 tool을 찾을 수 있도록 준비되어 있습니다.

```text
1. AppImage: $APPDIR/usr/bin/
2. standalone executable 옆 bin/
3. standalone executable 디렉터리
4. system PATH
```

따라서 이후 FFmpeg bundle을 추가해도 편집 기능 코드를 변경하지 않고 packaging만 확장할 수 있습니다.

현재 사용자는 `ffmpeg`와 `ffprobe`가 PATH에 있도록 준비해야 합니다.

Ubuntu 22.04:

```bash
sudo apt update
sudo apt install -y ffmpeg

ffmpeg -version
ffprobe -version
```

Windows에서는 FFmpeg를 설치한 뒤 `ffmpeg.exe`와 `ffprobe.exe`가 PATH에서 실행되는지 확인합니다.

```powershell
ffmpeg -version
ffprobe -version
```

## Ubuntu local build

전제 조건:

- Ubuntu 22.04 x86_64
- Python 3.10+
- `python3-venv`
- `curl`
- `patchelf`

`pyside6-deploy`가 Linux에서 사용하는 Nuitka standalone/onefile build는 system `patchelf` command가 필요합니다.

설치:

```bash
sudo apt update
sudo apt install -y python3-venv curl patchelf
```

확인:

```bash
patchelf --version
curl --version
```

실행:

```bash
cd ~/inpyo_ws/my_media_editor
bash scripts/build_linux_appimage.sh
```

build script는 시작 시 `python3`, `curl`, `patchelf`를 확인하고 누락된 필수 command가 있으면 실제 build 전에 종료합니다.

결과:

```text
dist/MyMediaEditor-0.1.0-x86_64.AppImage
```

실행:

```bash
chmod +x dist/MyMediaEditor-0.1.0-x86_64.AppImage
./dist/MyMediaEditor-0.1.0-x86_64.AppImage
```

build script는 별도 `build/package-linux/venv`를 생성하므로 개발용 `.venv`를 수정하지 않습니다.

`pyside6-deploy` 출력 위치와 이름은 PySide 버전에 따라 달라질 수 있습니다. 실제 확인된 PySide6 6.11.1 환경에서는 프로젝트 루트에 `MyMediaEditor.bin`이 생성됩니다. build script는 프로젝트 루트의 `MyMediaEditor.bin` / `deploy_main.bin`을 우선 확인하고, 필요한 경우 `deployment/` 경로도 fallback으로 탐색합니다.

Nuitka의 `zstandard` 미설치 경고는 onefile 압축 최적화 관련 경고이고, `ccache` 미설치 경고는 재빌드 속도 최적화 관련 경고입니다. 둘 다 현재 AppImage build의 필수 조건은 아닙니다.

## Windows local build

전제 조건:

- Windows x64
- Python 3.10+
- PowerShell
- Visual Studio C++ build tools (`dumpbin` 사용 가능 환경)

PowerShell에서:

```powershell
cd C:\path\to\my_media_editor
.\scripts\build_windows.ps1
```

결과:

```text
dist\MyMediaEditor-0.1.0-windows-x64.zip
```

ZIP을 풀고 `MyMediaEditor.exe`를 실행합니다.

## GitHub Actions

`.github/workflows/build-release.yml`은 다음 환경에서 별도로 build합니다.

```text
ubuntu-22.04
  → AppImage

windows-2025
  → Windows portable ZIP
```

Linux runner에서는 build 전에 `patchelf`와 `curl`을 apt로 설치합니다.

수동 build:

1. GitHub repository의 `Actions` 탭으로 이동
2. `Build desktop packages` 선택
3. `Run workflow` 선택
4. 완료 후 workflow run의 `Artifacts`에서 OS별 파일 다운로드

## GitHub Release

`v*` tag가 push되면 Linux / Windows build가 모두 성공한 뒤 GitHub Release를 만들고 두 artifact를 첨부합니다.

예정 release 흐름:

```bash
git tag v0.1.0
git push origin v0.1.0
```

생성 대상:

```text
GitHub Releases / v0.1.0
├── MyMediaEditor-0.1.0-x86_64.AppImage
└── MyMediaEditor-0.1.0-windows-x64.zip
```

## Build implementation

Standalone executable:

```text
pyside6-deploy
  └─ Nuitka
```

Linux AppImage:

```text
standalone binary
  ↓
AppDir
  ↓
linuxdeploy
  ↓
AppImage
```

Qt Multimedia 모듈 누락을 방지하기 위해 deployment 명령에서 `Multimedia,MultimediaWidgets`를 명시적으로 포함합니다.

## Validation

release 전 최소 확인 항목:

- `scripts/check.sh` 통과
- Ubuntu artifact가 Python / PySide6 설치 없이 시작되는지
- Windows artifact가 Python / PySide6 설치 없이 시작되는지
- 이미지 import / preview
- MP4 / WebM import / preview
- Trim / Crop / Resize / Rotate / Upscale / Speed Pending edit
- `Save As…`
- Sequence / Concat
- `Ctrl+C` 안전 종료(Ubuntu terminal 실행 시)
- FFmpeg가 없을 때 사용자가 이해할 수 있는 오류가 표시되는지

## 남은 packaging 작업

1. Ubuntu AppImage 실제 clean-machine smoke test
2. Windows 10 / 11 portable smoke test
3. FFmpeg / FFprobe bundle의 license 조건 확정
4. FFmpeg bundle 적용
5. Windows installer(MSIX 또는 setup executable) 검토
6. AppImage / Windows code signing 검토
