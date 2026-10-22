# Packaging and Release

## 배포 대상과 실행

v0.1.1부터 다음 배포 파일에 Python, PySide6, FFmpeg와 FFprobe를 포함합니다.
사용자는 Python이나 FFmpeg를 따로 설치할 필요가 없습니다.

| 대상 | 파일 | 실행 |
| --- | --- | --- |
| Ubuntu 22.04 / 24.04 x86_64 | `MyMediaEditor-0.1.1-x86_64.AppImage` | 실행 권한을 주고 실행 |
| Windows 10 22H2 / Windows 11 x64 | `MyMediaEditor-0.1.1-windows-x64.zip` | 전체 압축을 풀고 `MyMediaEditor.exe` 실행 |

이 표는 지원 목표입니다. CI의 실제 검증 환경은 Ubuntu 22.04와 Windows Server 2025입니다.
Ubuntu 24.04, X11/Wayland, Windows 10/11의 실제 데스크톱 검증은 공개 배포 전에 별도로 수행합니다.
ARM64, 32비트 Windows, 다른 Linux 배포판의 호환성은 보장하지 않습니다.

Windows에서는 EXE와 함께 `bin/` 및 `third-party/`를 유지합니다.
Linux의 FFmpeg/FFprobe는 AppImage 내부 `usr/bin/`에 있습니다.
AppImage 실행 시 FUSE 오류가 나면 다음과 같이 실행합니다.

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./MyMediaEditor-0.1.1-x86_64.AppImage
```

## 고정한 도구와 다운로드

- 앱 의존성: PySide6 6.11.1, imageio-ffmpeg 0.6.0 (`pyproject.toml`)
- 패키징: Nuitka 4.1.3, zstandard 0.25.0 (`packaging/requirements-build.txt`)
- FFmpeg/FFprobe: BtbN의 8.1 release branch 빌드 `n8.1.3-9-g29e619e767`, 2026-09-30 월말 보존본
- Linux AppImage 도구: linuxdeploy `1-alpha-20251107-1`

`packaging/ffmpeg.json`에 OS별 FFmpeg archive URL과 SHA256을 고정합니다.
`scripts/bundle_ffmpeg.py`는 새 다운로드와 캐시를 모두 검증한 뒤 두 실행 파일과
공급자의 LICENSE/문서를 복사합니다. `latest` URL이나 시스템 PATH의 도구를 패키지에 복사하지 않습니다.
외부 archive 경로를 그대로 추출하지 않습니다.

BtbN 월말 빌드는 공급자의 보존 정책상 2년간 유지됩니다. 보존 기간 만료 전에 검증한 새 빌드로
URL·해시를 함께 갱신하거나 배포자가 허용된 저장소에 해당 archive를 보존해야 합니다.

앱의 도구 검색 순서는 다음과 같습니다.

1. AppImage의 `$APPDIR/usr/bin`
2. Nuitka 원본 실행 파일 옆 `bin/` 및 실행 파일 디렉터리
3. 실행 중인 프로그램의 `bin/` 및 디렉터리
4. 개발 환경의 imageio-ffmpeg (FFmpeg만) 및 시스템 PATH

Nuitka onefile의 임시 추출 디렉터리와 원본 EXE 위치를 구분합니다.
FFprobe도 같은 검색 함수를 사용합니다.

## Linux local build

Ubuntu x86_64, Python 3.11 이상, C compiler, venv, curl, patchelf가 필요합니다.
Ubuntu 22.04 기본 Python은 3.10이므로 Python 3.11 이상을 별도로 준비합니다.
CI에서는 Python 3.11을 사용합니다.

```bash
sudo apt install -y build-essential python3-venv curl patchelf libegl1 libgl1 libpulse0
bash scripts/build_linux_appimage.sh
```

빌드는 전용 `build/package-linux/venv`를 만들고, Nuitka `--onefile`을 명시해
`build/package-linux/deployment/MyMediaEditor.bin`을 생성합니다.
결과 파일을 정확한 경로에서 확인하며 `.dist` 폴더의 임의 실행 파일을 선택하지 않습니다.
FFmpeg와 FFprobe를 추가한 뒤 linuxdeploy로 AppImage를 만듭니다.

```bash
chmod +x dist/MyMediaEditor-0.1.1-x86_64.AppImage
QT_QPA_PLATFORM=offscreen APPIMAGE_EXTRACT_AND_RUN=1 \
  ./dist/MyMediaEditor-0.1.1-x86_64.AppImage --self-test
```

## Windows local build

Windows x64, Python 3.11 이상 x64, PowerShell, Visual Studio C++ build tools가 필요합니다.
Visual Studio의 x64 Native Tools Command Prompt에서 PowerShell을 열어 실행합니다.

```powershell
.\scripts\build_windows.ps1
Expand-Archive dist\MyMediaEditor-0.1.1-windows-x64.zip -DestinationPath build\verify-windows
$env:QT_QPA_PLATFORM = "offscreen"
& .\build\verify-windows\MyMediaEditor.exe --self-test
if ($LASTEXITCODE -ne 0) { throw "Package self-test failed" }
```

스크립트는 모든 Python/pip/Nuitka 호출의 종료 코드를 확인합니다.
빌드 환경은 `build/package-windows/venv`이며, onefile 결과를 정확한 경로에서 복사합니다.
버전은 설치한 앱의 metadata에서 읽으므로 로컬 경로의 따옴표를 Python 코드에 삽입하지 않습니다.

## 완성 패키지 검증

`--self-test`는 앱의 실제 실행 파일에서 다음을 검사하며 성공 시 0, 실패 시 1을 반환합니다.
`--self-test-report <path>`를 추가하면 JSON 결과를 저장합니다.

- 두 실행 도구가 패키지에 있는지 (시스템 도구로 대체하지 않음)
- 앱 창과 Qt GUI 초기화
- PNG 이미지 크기 변경 및 저장
- H.264/AAC MP4 저장
- VP9/Opus WebM 생성 및 MP4 변환
- 소리 있는 영상과 무음 영상의 Sequence/Concat
- Qt Multimedia에서 MP4와 WebM 프레임 실제 디코딩
- 공백·한글 경로

진단 중 PATH는 비워집니다. 진단의 변환 명령에는 실행 제한 시간이 있고, CI는 전체 진단을
3분으로 제한합니다. 실제 사용자 GUI 조작, 오디오 장치 출력, GPU별 동작, X11/Wayland는
자동 진단만으로 검증되지 않습니다.

## GitHub Actions / Release

main push, `v*` tag push, main 대상 PR, 수동 실행에서 OS별 테스트·빌드를 수행합니다.
PR은 배포하지 않습니다. 빌드 작업은 읽기 권한만 사용합니다.

- Linux: 완성 AppImage 자체의 진단
- Windows: ZIP을 별도 한글·공백 경로에 푼 뒤 EXE 자체의 진단
- 진단을 통과한 경우에만 OS별 package artifact 업로드
- 실패 시 가능한 JSON 진단 결과 별도 업로드
- main: 양쪽 성공 후 `app-latest` 갱신
- `v*` tag: 양쪽 성공 후 해당 GitHub Release 생성

같은 ref의 중복 실행은 취소합니다. 안정 버전의 tag는 해당 `pyproject.toml` 버전과 맞춰 사용합니다.
수동 workflow 실행 또는 PR의 Actions 결과에서 시험 빌드 파일을 받을 수 있습니다.

## 제3자 고지와 공개 배포 전 확인

FFmpeg GPL variant를 사용하며 `libx264` 인코더가 포함됩니다.
공급자가 archive에 제공한 LICENSE와 문서, 다운로드 URL/SHA256/빌드 recipe 링크가
`third-party/ffmpeg/` (Linux: `usr/third-party/ffmpeg/`)에 포함됩니다.
해당 링크를 모든 의존성의 완전한 대응 소스 제공으로 간주하지 않습니다.

공개 배포자는 FFmpeg와 포함 라이브러리, Qt/PySide6의 고지·소스 제공 등 배포 조건을 검토하고
필요한 자료를 함께 제공해야 합니다. 이 저장소의 패키징 변경은 법적 준수를 보증하지 않습니다.

공개 배포 전 수동 확인:

- Python/FFmpeg/FFprobe가 없는 Ubuntu 22.04/24.04, Windows 10/11에서 실행
- X11 및 Wayland의 창 표시, Drag & Drop, 파일 대화상자
- 실제 스피커 재생, 긴 영상 탐색, Trim/Speed/Crop/Rotate 및 저장
- 읽기 전용 설치 위치, 공백·한글 사용자 폴더에서 실행
- 제3자 라이선스와 대응 소스 제공 준비
- Windows installer 및 코드 서명은 별도 후속 작업
