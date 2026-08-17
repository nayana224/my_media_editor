from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from media_editor.edit_state import EditState
from media_editor.widgets import EditedVideoWidget


class SpeedDialog(QDialog):
    """실제 영상을 보면서 슬라이더와 preset으로 배속을 설정한다."""

    rate_changed = Signal(float)

    PRESETS = (0.5, 1.0, 1.5, 2.0, 4.0)

    def __init__(
        self,
        media_path: Path,
        current_rate: float,
        source_duration_ms: int,
        current_position_ms: int,
        edits: EditState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Speed")
        self.setModal(True)
        self.resize(780, 700)
        self.setMinimumSize(680, 620)

        self._source_duration_ms = max(0, source_duration_ms)
        self._syncing = False
        self._seek_dragging = False
        self._trim = edits.trim

        description = QLabel(
            "영상 Preview를 재생하면서 배속을 조절하세요. "
            "슬라이더 변경은 즉시 이 Preview에 반영됩니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        self.preview = EditedVideoWidget()
        self.preview.setMinimumHeight(340)
        self.preview.set_edit_provider(lambda: edits)

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoSink(self.preview.videoSink())
        self.player.setSource(QUrl.fromLocalFile(str(media_path)))
        self._preview_priming = True
        self._previous_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(True)
        self.preview.videoSink().videoFrameChanged.connect(
            self._on_first_preview_frame
        )

        self.play_button = QPushButton("▶ Play")
        self.play_button.setObjectName("primaryButton")
        self.play_button.clicked.connect(self._toggle_playback)

        if self._trim is None:
            timeline_start = 0
            timeline_end = max(0, source_duration_ms)
        else:
            timeline_start, timeline_end = self._trim

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(
            timeline_start,
            max(timeline_start, timeline_end),
        )
        self.position_slider.setValue(
            min(max(current_position_ms, timeline_start), timeline_end)
        )
        self.position_slider.sliderPressed.connect(self._seek_pressed)
        self.position_slider.sliderReleased.connect(self._seek_released)
        self.position_slider.sliderMoved.connect(self._seek_moved)

        self.position_label = QLabel()
        self.position_label.setObjectName("timeLabel")

        playback_row = QHBoxLayout()
        playback_row.addWidget(self.play_button)
        playback_row.addWidget(self.position_slider, stretch=1)
        playback_row.addWidget(self.position_label)

        self.rate_label = QLabel()
        self.rate_label.setObjectName("selectionInfo")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(25, 400)
        self.slider.setSingleStep(5)
        self.slider.setPageStep(25)
        self.slider.setTickInterval(25)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.25, 4.0)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setSingleStep(0.05)
        self.rate_spin.setSuffix("×")

        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Speed"))
        rate_row.addWidget(self.slider, stretch=1)
        rate_row.addWidget(self.rate_spin)

        scale_labels = QHBoxLayout()
        scale_labels.addWidget(QLabel("0.25×"))
        scale_labels.addStretch()
        scale_labels.addWidget(QLabel("1×"))
        scale_labels.addStretch()
        scale_labels.addWidget(QLabel("4×"))

        preset_layout = QHBoxLayout()
        for rate in self.PRESETS:
            button = QPushButton(f"{rate:g}×")
            button.setObjectName("secondaryButton")
            button.clicked.connect(
                lambda _checked=False, value=rate: self.set_rate(value)
            )
            preset_layout.addWidget(button)

        self.duration_label = QLabel()
        self.duration_label.setObjectName("selectionInfo")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(description)
        layout.addWidget(self.preview, stretch=1)
        layout.addLayout(playback_row)
        layout.addWidget(self.rate_label)
        layout.addLayout(rate_row)
        layout.addLayout(scale_labels)
        layout.addLayout(preset_layout)
        layout.addWidget(self.duration_label)
        layout.addWidget(buttons)

        self.slider.valueChanged.connect(self._slider_changed)
        self.rate_spin.valueChanged.connect(self._spin_changed)
        self.player.positionChanged.connect(self._position_changed)
        self.player.playbackStateChanged.connect(self._playback_state_changed)

        start_position = self.position_slider.value()
        self.player.setPosition(start_position)
        self.position_label.setText(self._format_time(start_position))
        self.set_rate(current_rate, emit_signal=False)
        self.player.play()

    @property
    def rate(self) -> float:
        return round(self.rate_spin.value(), 2)

    def set_rate(self, rate: float, emit_signal: bool = True) -> None:
        rate = min(4.0, max(0.25, float(rate)))
        self._syncing = True
        self.slider.setValue(round(rate * 100))
        self.rate_spin.setValue(rate)
        self._syncing = False

        self.player.setPlaybackRate(rate)
        self._refresh_info()
        if emit_signal:
            self.rate_changed.emit(self.rate)

    def reject(self) -> None:
        self._preview_priming = False
        self.player.stop()
        self.audio_output.setMuted(self._previous_muted)
        super().reject()

    def accept(self) -> None:
        self._preview_priming = False
        self.player.stop()
        self.audio_output.setMuted(self._previous_muted)
        super().accept()

    def _on_first_preview_frame(self, frame) -> None:
        if not self._preview_priming or not frame.isValid():
            return
        self._preview_priming = False
        self.player.pause()
        self.player.setPosition(self.position_slider.value())
        self.audio_output.setMuted(self._previous_muted)

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return

        if self._trim is not None:
            start_ms, end_ms = self._trim
            position = self.player.position()
            if position < start_ms or position >= end_ms:
                self.player.setPosition(start_ms)
        self.player.play()

    def _playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        self.play_button.setText(
            "Ⅱ Pause"
            if state == QMediaPlayer.PlaybackState.PlayingState
            else "▶ Play"
        )

    def _position_changed(self, position: int) -> None:
        if not self._seek_dragging:
            self.position_slider.setValue(position)
        self.position_label.setText(self._format_time(position))

        if (
            self._trim is not None
            and self.player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
            and position >= self._trim[1]
        ):
            self.player.pause()
            self.player.setPosition(self._trim[0])

    def _seek_pressed(self) -> None:
        self._seek_dragging = True

    def _seek_released(self) -> None:
        self._seek_dragging = False
        self.player.setPosition(self.position_slider.value())

    def _seek_moved(self, position: int) -> None:
        self.position_label.setText(self._format_time(position))

    def _slider_changed(self, value: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        self.rate_spin.setValue(value / 100)
        self._syncing = False
        self.player.setPlaybackRate(self.rate)
        self._refresh_info()
        self.rate_changed.emit(self.rate)

    def _spin_changed(self, value: float) -> None:
        if self._syncing:
            return
        self._syncing = True
        self.slider.setValue(round(value * 100))
        self._syncing = False
        self.player.setPlaybackRate(self.rate)
        self._refresh_info()
        self.rate_changed.emit(self.rate)

    def _refresh_info(self) -> None:
        rate = self.rate
        if rate < 1.0:
            description = "느리게"
        elif rate > 1.0:
            description = "빠르게"
        else:
            description = "원본 속도"

        self.rate_label.setText(f"{rate:.2f}× · {description}")

        if self._source_duration_ms <= 0:
            self.duration_label.setText(
                "예상 길이: 미디어 길이를 아직 읽지 못했습니다."
            )
            return

        output_ms = round(self._source_duration_ms / rate)
        self.duration_label.setText(
            f"예상 길이 {self._format_time(output_ms)} · "
            f"원본/선택 구간 {self._format_time(self._source_duration_ms)}"
        )

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds) / 1000
        minutes = int(total_seconds // 60)
        seconds = total_seconds - minutes * 60
        return f"{minutes:02d}:{seconds:05.2f}"
