import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaPlayer, QVideoFrame
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton

from media_editor.app_live_helpers import LiveDialogMixin
from media_editor.main_window import MainWindow
from media_editor.media import MediaKind
from media_editor.preview_transform import apply_preview_edits
from media_editor.sequence_dialog import SequenceDialog
from media_editor.sequence_export import (
    build_sequence_command,
    make_sequence_output_path,
)
from media_editor.speed_feature import install_speed_feature
from media_editor.style import APP_STYLE
from media_editor.timeline_model import (
    build_timeline_mapping,
    format_timeline_time,
)
from media_editor.widgets import EditedVideoWidget


class PreviewReadyMainWindow(LiveDialogMixin, MainWindow):
    """누적 live preview, 편집 결과 timeline과 Sequence를 제공한다."""

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
        self._speed_controller = install_speed_feature(self)
        self._refresh_pending_preview()
        self._refresh_timeline()
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
        if hasattr(self, "_speed_controller"):
            self._speed_controller.refresh()
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
        else:
            self._refresh_pending_preview()

        if hasattr(self, "_speed_controller"):
            self._speed_controller.apply_current_rate()
            self._speed_controller.refresh()

        self._refresh_timeline()

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
        if hasattr(self, "timeline"):
            self._refresh_timeline()

    def _reset_current_edits(self) -> None:
        super()._reset_current_edits()
        self.player.setPlaybackRate(1.0)
        self._refresh_pending_preview()
        self._refresh_timeline()
        if hasattr(self, "_speed_controller"):
            self._speed_controller.refresh()

    def _timeline_mapping(self):
        return build_timeline_mapping(
            self.player.duration(),
            self._current_edits(),
        )

    def _refresh_timeline(self) -> None:
        """Trim/Speed를 반영한 편집 결과 기준 timeline으로 갱신한다."""
        if (
            self.current_asset is None
            or self.current_asset.kind is not MediaKind.VIDEO
            or self.player.duration() <= 0
        ):
            self.timeline.setRange(0, 0)
            self.timeline.setValue(0)
            self.current_time.setText("00:00.000")
            self.duration_time.setText("00:00.000")
            self.timeline.setToolTip("")
            return

        mapping = self._timeline_mapping()
        self.timeline.setRange(0, mapping.output_duration_ms)

        source_position = self.player.position()
        if (
            not self._preview_priming
            and (
                source_position < mapping.source_start_ms
                or source_position > mapping.source_end_ms
            )
        ):
            source_position = mapping.source_start_ms
            self.player.setPosition(source_position)

        output_position = mapping.source_to_output_ms(source_position)
        if not self._slider_is_pressed:
            self.timeline.setValue(output_position)

        self.current_time.setText(format_timeline_time(output_position))
        self.duration_time.setText(
            format_timeline_time(mapping.output_duration_ms)
        )
        self.timeline.setToolTip(
            "편집 결과 timeline · "
            f"source {format_timeline_time(mapping.source_start_ms)} → "
            f"{format_timeline_time(mapping.source_end_ms)} · "
            f"Speed {mapping.speed:.2f}×"
        )

    def _on_duration_changed(self, duration: int) -> None:
        del duration
        self._refresh_timeline()

    def _on_position_changed(self, position: int) -> None:
        if (
            self.current_asset is None
            or self.current_asset.kind is not MediaKind.VIDEO
            or self.player.duration() <= 0
        ):
            return

        mapping = self._timeline_mapping()
        output_position = mapping.source_to_output_ms(position)

        if not self._slider_is_pressed:
            self.timeline.setValue(output_position)
        self.current_time.setText(format_timeline_time(output_position))

        if self._preview_priming:
            return

        if (
            self.player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
            and position >= mapping.source_end_ms
        ):
            self.player.pause()
            self.player.setPosition(mapping.source_start_ms)

    def _on_slider_pressed(self) -> None:
        self._slider_is_pressed = True

    def _on_slider_released(self) -> None:
        self._slider_is_pressed = False
        if (
            self.current_asset is None
            or self.current_asset.kind is not MediaKind.VIDEO
        ):
            return

        mapping = self._timeline_mapping()
        source_position = mapping.output_to_source_ms(
            self.timeline.value()
        )
        self.player.setPosition(source_position)
        self.current_time.setText(
            format_timeline_time(self.timeline.value())
        )

    def _on_slider_moved(self, position: int) -> None:
        self.current_time.setText(format_timeline_time(position))

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

        mapping = self._timeline_mapping()
        self.player.setPosition(mapping.source_start_ms)
        self.audio_output.setMuted(False)

        if hasattr(self, "_speed_controller"):
            self._speed_controller.apply_current_rate()

        self._refresh_timeline()

    def _toggle_playback(self) -> None:
        if self._preview_priming:
            self._preview_priming = False
            self.audio_output.setMuted(False)

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return

        mapping = self._timeline_mapping()
        position = self.player.position()
        if (
            position < mapping.source_start_ms
            or position >= mapping.source_end_ms
        ):
            self.player.setPosition(mapping.source_start_ms)

        if hasattr(self, "_speed_controller"):
            self._speed_controller.apply_current_rate()

        self.player.play()

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

    signal_pump = QTimer()
    signal_pump.setInterval(200)
    signal_pump.timeout.connect(lambda: None)
    signal_pump.start()

    app.aboutToQuit.connect(window.shutdown)
    window.show()

    raise SystemExit(app.exec())
