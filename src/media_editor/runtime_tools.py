import os
from pathlib import Path
import shutil
import sys


def configure_runtime_path() -> None:
    """배포 bundle의 tool 디렉터리를 PATH 앞쪽에 추가한다."""
    current_path = os.environ.get("PATH", "")
    entries = [
        str(directory)
        for directory in _runtime_tool_directories()
        if directory.is_dir()
    ]
    if not entries:
        return

    prefix = os.pathsep.join(entries)
    os.environ["PATH"] = (
        f"{prefix}{os.pathsep}{current_path}" if current_path else prefix
    )


def find_runtime_tool(name: str) -> str:
    """배포 bundle, Python package, PATH 순서로 외부 실행 파일을 찾는다."""
    executable_name = f"{name}.exe" if sys.platform == "win32" else name

    for directory in _runtime_tool_directories():
        candidate = directory / executable_name
        if candidate.is_file():
            return str(candidate)

    if name == "ffmpeg":
        try:
            from imageio_ffmpeg import get_ffmpeg_exe

            packaged_ffmpeg = Path(get_ffmpeg_exe())
            if packaged_ffmpeg.is_file():
                return str(packaged_ffmpeg)
        except (ImportError, RuntimeError):
            pass

    path = shutil.which(executable_name)
    if path is not None:
        return path

    raise FileNotFoundError(
        f"{name}를 찾을 수 없습니다. 앱과 함께 제공된 tool 또는 system PATH를 "
        "확인해 주세요."
    )


def _runtime_tool_directories() -> list[Path]:
    """지원하는 배포 형태별 bundled tool 검색 경로를 반환한다."""
    directories: list[Path] = []

    appdir = os.environ.get("APPDIR")
    if appdir:
        directories.append(Path(appdir) / "usr" / "bin")

    executable_dir = Path(sys.executable).resolve().parent
    directories.extend(
        [
            executable_dir / "bin",
            executable_dir,
        ]
    )

    return directories
