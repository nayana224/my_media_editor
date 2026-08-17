import os

from media_editor.runtime_tools import configure_runtime_path


def _configure_qt_multimedia_logging() -> None:
    """일반 실행에서 Qt Multimedia의 FFmpeg 진단 로그를 숨긴다."""
    existing_rules = os.environ.get("QT_LOGGING_RULES", "").strip()
    quiet_rules = "qt.multimedia.ffmpeg=false;qt.multimedia.ffmpeg.*=false"
    os.environ["QT_LOGGING_RULES"] = (
        f"{existing_rules};{quiet_rules}" if existing_rules else quiet_rules
    )
    os.environ.setdefault("QT_FFMPEG_DEBUG", "0")


def main() -> None:
    """배포 환경을 준비한 뒤 GUI application을 시작한다."""
    configure_runtime_path()
    _configure_qt_multimedia_logging()

    from media_editor.app import main as app_main

    app_main()
