from media_editor.runtime_tools import configure_runtime_path


def main() -> None:
    """배포 환경을 준비한 뒤 GUI application을 시작한다."""
    configure_runtime_path()

    from media_editor.app import main as app_main

    app_main()
