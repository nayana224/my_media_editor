import sys

from PySide6.QtMultimedia import QVideoFrame
from PySide6.QtWidgets import QApplication

from media_editor.main_window import MainWindow
from media_editor.media import MediaKind
from media_editor.style import APP_STYLE


class PreviewReadyMainWindow(MainWindow):
    """영상 import 직후 첫 frame을 자동으로 준비하는 MainWindow."""

    def __init__(self) -> None:
        super().__init__()
        self._preview_priming = False
        self.video_widget.videoSink().videoFrameChanged.connect(
            self._on_preview_frame_changed
        )

    def _load_asset(self, asset) -> None:
        self._cancel_preview_priming()
        super()._load_asset(asset)

        if asset.kind is MediaKind.VIDEO:
            self._prime_video_preview()

    def _prime_video_preview(self) -> None:
        """소리 없이 첫 유효 frame을 decode한 뒤 즉시 pause한다."""
        self._preview_priming = True
        self.audio_output.setMuted(True)
        self.player.setPosition(0)
        self.player.play()

    def _on_preview_frame_changed(self, frame: QVideoFrame) -> None:
        if not self._preview_priming or not frame.isValid():
            return

        self._preview_priming = False
        self.player.pause()
        self.player.setPosition(0)
        self.audio_output.setMuted(False)

    def _toggle_playback(self) -> None:
        if self._preview_priming:
            self._preview_priming = False
            self.audio_output.setMuted(False)

        super()._toggle_playback()

    def _cancel_preview_priming(self) -> None:
        if not self._preview_priming:
            return

        self._preview_priming = False
        self.audio_output.setMuted(False)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Media Editor")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)

    window = PreviewReadyMainWindow()
    window.show()

    raise SystemExit(app.exec())
