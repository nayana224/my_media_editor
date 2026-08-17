from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QPushButton

from media_editor.media import MediaKind
from media_editor.project import MediaAsset
from media_editor.speed_dialog import SpeedDialog


class SpeedController(QObject):
    """Speed dialog, pending state와 QMediaPlayer playbackRate를 동기화한다."""

    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.button = QPushButton("Speed")
        self.button.setObjectName("toolButton")
        self.button.clicked.connect(self._open_dialog)

        root_layout = window.centralWidget().layout()
        playback_card = root_layout.itemAt(root_layout.count() - 1).widget()
        controls_layout = playback_card.layout().itemAt(2).layout()
        save_index = controls_layout.indexOf(window.save_button)
        controls_layout.insertWidget(max(0, save_index), self.button)

        window.media_list.currentItemChanged.connect(self._selection_changed)
        window.reset_edits_button.clicked.connect(self._reset_clicked)
        window.player.playbackRateChanged.connect(self._rate_changed)

        self.refresh()

    def refresh(self) -> None:
        asset = self.window.current_asset
        is_video = isinstance(asset, MediaAsset) and asset.kind is MediaKind.VIDEO
        self.button.setEnabled(is_video and self.window._ffmpeg_process is None)

        if not is_video:
            self.button.setText("Speed")
            return

        state = self.window._current_edits()
        rate = 1.0 if state is None or state.speed is None else state.speed
        self.button.setText(
            "Speed" if abs(rate - 1.0) < 1e-9 else f"Speed {rate:.2f}×"
        )

    def apply_current_rate(self) -> None:
        asset = self.window.current_asset
        if asset is None or asset.kind is not MediaKind.VIDEO:
            self.window.player.setPlaybackRate(1.0)
            return

        state = self.window._current_edits()
        rate = 1.0 if state is None or state.speed is None else state.speed
        self.window.player.setPlaybackRate(rate)

    def _selection_changed(self, current, previous) -> None:
        del current, previous
        self.apply_current_rate()
        self.refresh()

    def _reset_clicked(self) -> None:
        self.apply_current_rate()
        self.refresh()

    def _rate_changed(self, rate: float) -> None:
        del rate
        self.refresh()

    def _open_dialog(self) -> None:
        asset = self.window.current_asset
        if (
            asset is None
            or asset.kind is not MediaKind.VIDEO
            or self.window._ffmpeg_process is not None
        ):
            return

        state = self.window._current_edits()
        if state is None:
            return

        previous_rate = state.speed if state.speed is not None else 1.0
        source_duration_ms = self.window.player.duration()
        if state.trim is not None:
            source_duration_ms = state.trim[1] - state.trim[0]

        previous_position = self.window.player.position()
        self.window.player.pause()

        dialog = SpeedDialog(
            asset.path,
            previous_rate,
            source_duration_ms,
            previous_position,
            state,
            self.window,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.window.player.setPlaybackRate(previous_rate)
            self.refresh()
            return

        rate = dialog.rate
        state.speed = None if abs(rate - 1.0) < 1e-9 else rate
        self.window.player.setPlaybackRate(rate)
        self.window.player.setPosition(previous_position)
        self.window._update_edit_status()
        if hasattr(self.window, "_refresh_pending_preview"):
            self.window._refresh_pending_preview()
        self.window._update_media_tools()
        self.refresh()


def install_speed_feature(window) -> SpeedController:
    """MainWindow에 Speed UI를 설치하고 controller를 반환한다."""
    return SpeedController(window)
