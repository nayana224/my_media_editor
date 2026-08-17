import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaPlayer, QVideoFrame
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton

from media_editor.main_window import MainWindow
from media_editor.media import MediaKind
from media_editor.preview_transform import apply_preview_edits
from media_editor.sequence_dialog import SequenceDialog
from media_editor.sequence_export import (
    build_sequence_command,
    make_sequence_output_path,
)
from media_editor.style import APP_STYLE
from media_editor.widgets import EditedVideoWidget


class PreviewReadyMainWindow(MainWindow):
    """첫 frame, pending edit live preview와 Sequence를 제공한다."""

    def __init__(self) -> None:
        super().__init__()

        old_video_widget = self.video_widget
        video_layout = self.preview.video_page.layout()
        if video_layout is not None:
            video_layout.removeWidget(old_video_widget)
        old_video_widget.deleteLater()

        self.video_widget = EditedVideoWidget()
        self.video_widget.set_edit_provider(self._current_edits)
        self.player.setVideoSink(self.video_widget.videoSink())
        self.preview.set_video_widget(self.video_widget)

        self._preview_priming = False
        self.video_widget.videoSink().videoFrameChanged.connect(
            self._on_preview_frame_changed
        )

        self._install_sequence_button()
        self._refresh_pending_preview()
        self._update_media_tools()

    def _install_sequence_button(self) -> None:
        """Header에 Sequence 진입 버튼을 추가한다."""
        root_layout = self.centralWidget().layout()
        header_layout = root_layout.itemAt(0).layout()

        self.sequence_button = QPushButton("Sequence")
        self.sequence_button.setObjectName("secondaryButton")
        self.sequence_button.clicked.connect(self._request_sequence)
        header_layout.insertWidget(
            max(0, header_layout.count() - 1),
            self.sequence_button,
        )

    def _update_media_tools(self) -> None:
        super()._update_media_tools()
        if not hasattr(self, "sequence_button"):
            return

        video_count = sum(
            asset.kind is MediaKind.VIDEO for asset in self.project.assets
        )
        self.sequence_button.setEnabled(
            video_count >= 2 and self._ffmpeg_process is None
        )

    def _request_sequence(self) -> None:
        if self._ffmpeg_process is not None:
            return

        dialog = SequenceDialog(
            self.project.assets,
            self.current_asset,
            self,
        )
        if not dialog.exec():
            return

        paths = dialog.sequence_paths
        default_path = make_sequence_output_path(paths[0])
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sequence",
            str(default_path),
            "MP4 Video (*.mp4)",
        )
        if not filename:
            return

        output_path = Path(filename)
        if output_path.suffix.lower() != ".mp4":
            output_path = output_path.with_suffix(".mp4")

        try:
            command = build_sequence_command(paths)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            self._show_error(str(exc))
            return

        command.append(str(output_path))
        self._start_ffmpeg_job(command, output_path, "Sequence Export")

    def _load_asset(self, asset) -> None:
        self._cancel_preview_priming()
        super()._load_asset(asset)

        if asset.kind is MediaKind.VIDEO:
            self._prime_video_preview()
            return

        self._refresh_pending_preview()

    def _source_media_size(self) -> tuple[int, int] | None:
        if self.current_asset is None:
            return None

        image = self._source_preview_image()
        if image.isNull():
            return None
        return image.width(), image.height()

    def _source_preview_image(self):
        if self.current_asset is None:
            from PySide6.QtGui import QImage

            return QImage()

        if self.current_asset.kind is MediaKind.IMAGE:
            from PySide6.QtGui import QImage

            return QImage(str(self.current_asset.path))

        return self.video_widget.source_image()

    def current_preview_image(self):
        source = self._source_preview_image()
        if source.isNull():
            return source
        return apply_preview_edits(source, self._current_edits())

    def _refresh_pending_preview(self) -> None:
        if not hasattr(self, "video_widget") or self.current_asset is None:
            return

        if self.current_asset.kind is MediaKind.VIDEO:
            self.preview.set_video_widget(self.video_widget)
            if isinstance(self.video_widget, EditedVideoWidget):
                self.video_widget.refresh_edits()
            return

        image = self.current_preview_image()
        if not image.isNull():
            self.preview.set_image_data(image)

    def _update_edit_status(self) -> None:
        super()._update_edit_status()
        if hasattr(self, "preview"):
            self._refresh_pending_preview()

    def _reset_current_edits(self) -> None:
        super()._reset_current_edits()
        self._refresh_pending_preview()

    def _request_trim(self) -> None:
        super()._request_trim()
        self._refresh_pending_preview()

    def _request_crop(self) -> None:
        super()._request_crop()
        self._refresh_pending_preview()

    def _request_resize(self) -> None:
        super()._request_resize()
        self._refresh_pending_preview()

    def _request_rotate(self) -> None:
        super()._request_rotate()
        self._refresh_pending_preview()

    def _request_upscale(self) -> None:
        super()._request_upscale()
        self._refresh_pending_preview()

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

        state = self._current_edits()
        if state is not None and state.trim is not None:
            self.player.setPosition(state.trim[0])
        else:
            self.player.setPosition(0)

        self.audio_output.setMuted(False)

    def _toggle_playback(self) -> None:
        if self._preview_priming:
            self._preview_priming = False
            self.audio_output.setMuted(False)

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return

        state = self._current_edits()
        if state is not None and state.trim is not None:
            start_ms, end_ms = state.trim
            position = self.player.position()
            if position < start_ms or position >= end_ms:
                self.player.setPosition(start_ms)

        self.player.play()

    def _on_position_changed(self, position: int) -> None:
        super()._on_position_changed(position)

        if self._preview_priming:
            return

        state = self._current_edits()
        if (
            state is None
            or state.trim is None
            or self.player.playbackState()
            != QMediaPlayer.PlaybackState.PlayingState
        ):
            return

        start_ms, end_ms = state.trim
        if position >= end_ms:
            self.player.pause()
            self.player.setPosition(start_ms)

    def _cancel_preview_priming(self) -> None:
        if not getattr(self, "_preview_priming", False):
            return

        self._preview_priming = False
        self.audio_output.setMuted(False)

    def shutdown(self) -> None:
        """재생 및 FFmpeg child process를 정리한다."""
        self._cancel_preview_priming()
        self.player.stop()

        process = getattr(self, "_ffmpeg_process", None)
        if process is None:
            return

        process.terminate()
        if not process.waitForFinished(1500):
            process.kill()
            process.waitForFinished(1000)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Media Editor")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)

    window = PreviewReadyMainWindow()
    shutting_down = {"active": False}

    def request_shutdown(signum=None, frame=None) -> None:
        del signum, frame
        if shutting_down["active"]:
            return
        shutting_down["active"] = True
        window.shutdown()
        app.closeAllWindows()
        app.quit()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    # Qt event loop 중에도 Python signal handler가 처리될 기회를 준다.
    signal_pump = QTimer()
    signal_pump.setInterval(200)
    signal_pump.timeout.connect(lambda: None)
    signal_pump.start()

    app.aboutToQuit.connect(window.shutdown)
    window.show()

    raise SystemExit(app.exec())
