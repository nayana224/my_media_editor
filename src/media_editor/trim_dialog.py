from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class TrimDialog(QDialog):
    """실제 영상을 재생하면서 trim 구간을 선택한다."""

    def __init__(
        self,
        duration_ms: int,
        current_position_ms: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trim Video")
        self.setModal(True)
        self.resize(820, 720)
        self.setMinimumSize(700, 620)

        self._duration_ms = duration_ms
        self._syncing = False
        self._seek_dragging = False

        media_path = self._current_media_path(parent)
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.video_widget.setMinimumHeight(360)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        if media_path is not None:
            self.player.setSource(QUrl.fromLocalFile(str(media_path)))

        self.play_button = QPushButton("▶ Play")
        self.play_button.setObjectName("primaryButton")
        self.play_button.clicked.connect(self._toggle_playback)

        self.preview_position = QSlider(Qt.Orientation.Horizontal)
        self.preview_position.setRange(0, duration_ms)
        self.preview_position.setValue(current_position_ms)
        self.preview_position.sliderPressed.connect(self._on_seek_pressed)
        self.preview_position.sliderReleased.connect(self._seek_released)
        self.preview_position.sliderMoved.connect(self._preview_seek_label)

        self.preview_time = QLabel(self._format_time(current_position_ms))
        self.preview_time.setObjectName("timeLabel")

        playback = QHBoxLayout()
        playback.addWidget(self.play_button)
        playback.addWidget(self.preview_position, stretch=1)
        playback.addWidget(self.preview_time)

        self.start_slider = self._create_range_slider()
        self.end_slider = self._create_range_slider()
        self.start_spin = self._create_time_spin()
        self.end_spin = self._create_time_spin()

        duration_seconds = duration_ms / 1000
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(0.0, duration_seconds)

        self.start_slider.setValue(0)
        self.end_slider.setValue(duration_ms)
        self.start_spin.setValue(0.0)
        self.end_spin.setValue(duration_seconds)

        self.start_slider.valueChanged.connect(self._sync_from_sliders)
        self.end_slider.valueChanged.connect(self._sync_from_sliders)
        self.start_spin.valueChanged.connect(self._sync_from_spins)
        self.end_spin.valueChanged.connect(self._sync_from_spins)

        self.range_info = QLabel()
        self.range_info.setObjectName("selectionInfo")

        quick = QHBoxLayout()
        start_current = QPushButton("Start = 현재 위치")
        end_current = QPushButton("End = 현재 위치")
        reset = QPushButton("전체 길이")
        for button in (start_current, end_current, reset):
            button.setObjectName("secondaryButton")
        start_current.clicked.connect(
            lambda: self.start_slider.setValue(self.player.position())
        )
        end_current.clicked.connect(
            lambda: self.end_slider.setValue(self.player.position())
        )
        reset.clicked.connect(self._reset_range)
        quick.addWidget(start_current)
        quick.addWidget(end_current)
        quick.addWidget(reset)
        quick.addStretch()

        start_row = self._build_range_row(
            "Start", self.start_slider, self.start_spin
        )
        end_row = self._build_range_row(
            "End", self.end_slider, self.end_spin
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        description = QLabel(
            "영상 자체를 재생하거나 seek하면서 남길 시작/끝 지점을 정하세요."
        )
        description.setObjectName("dialogDescription")
        layout.addWidget(description)
        layout.addWidget(self.video_widget, stretch=1)
        layout.addLayout(playback)
        layout.addWidget(self.range_info)
        layout.addLayout(quick)
        layout.addWidget(start_row)
        layout.addWidget(end_row)
        layout.addWidget(buttons)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.playbackStateChanged.connect(
            self._on_playback_state_changed
        )
        self.player.setPosition(current_position_ms)
        self._update_range_info()

    @property
    def start_ms(self) -> int:
        return self.start_slider.value()

    @property
    def end_ms(self) -> int:
        return self.end_slider.value()

    @staticmethod
    def _current_media_path(parent: QWidget | None) -> Path | None:
        if parent is None:
            return None
        asset = getattr(parent, "current_asset", None)
        path = getattr(asset, "path", None)
        return Path(path) if path is not None else None

    def _create_range_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, self._duration_ms)
        slider.setSingleStep(100)
        slider.setPageStep(1000)
        return slider

    def _create_time_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setSingleStep(0.1)
        spin.setSuffix(" s")
        return spin

    def _build_range_row(
        self,
        name: str,
        slider: QSlider,
        spin: QDoubleSpinBox,
    ) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(name)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        layout.addWidget(slider, stretch=1)
        layout.addWidget(spin)
        return row

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        self.play_button.setText(
            "Ⅱ Pause"
            if state == QMediaPlayer.PlaybackState.PlayingState
            else "▶ Play"
        )

    def _on_seek_pressed(self) -> None:
        self._seek_dragging = True

    def _on_position_changed(self, position: int) -> None:
        if not self._seek_dragging:
            self.preview_position.setValue(position)
            self.preview_time.setText(self._format_time(position))

    def _preview_seek_label(self, position: int) -> None:
        self.preview_time.setText(self._format_time(position))

    def _seek_released(self) -> None:
        self._seek_dragging = False
        self.player.setPosition(self.preview_position.value())

    def _sync_from_sliders(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        self.start_spin.setValue(self.start_ms / 1000)
        self.end_spin.setValue(self.end_ms / 1000)
        self._syncing = False
        self._update_range_info()

    def _sync_from_spins(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        self.start_slider.setValue(round(self.start_spin.value() * 1000))
        self.end_slider.setValue(round(self.end_spin.value() * 1000))
        self._syncing = False
        self._update_range_info()

    def _reset_range(self) -> None:
        self.start_slider.setValue(0)
        self.end_slider.setValue(self._duration_ms)

    def _update_range_info(self) -> None:
        selected = max(0, self.end_ms - self.start_ms)
        self.range_info.setText(
            f"선택 구간  {self._format_time(self.start_ms)} → "
            f"{self._format_time(self.end_ms)}  ·  "
            f"길이 {selected / 1000:.3f} s"
        )

    def _validate_and_accept(self) -> None:
        if self.end_ms <= self.start_ms:
            QMessageBox.warning(
                self,
                "Trim Video",
                "End는 Start보다 뒤에 있어야 합니다.",
            )
            return
        self.player.stop()
        self.accept()

    def reject(self) -> None:
        self.player.stop()
        super().reject()

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds) / 1000
        minutes = int(total_seconds // 60)
        seconds = total_seconds - minutes * 60
        return f"{minutes:02d}:{seconds:06.3f}"
