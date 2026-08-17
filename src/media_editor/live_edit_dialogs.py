from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QDial,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from media_editor.edit_state import EditState
from media_editor.preview_transform import apply_preview_edits
from media_editor.transform_dialogs import CropDialog, ImagePreviewLabel
from media_editor.widgets import EditedVideoWidget


def _source_image(parent: QWidget | None) -> QImage:
    """현재 media의 편집 전 source frame/image를 가져온다."""
    if parent is None:
        return QImage()

    getter = getattr(parent, "_source_preview_image", None)
    if callable(getter):
        image = getter()
        if isinstance(image, QImage) and not image.isNull():
            return image.copy()

    current_asset = getattr(parent, "current_asset", None)
    if current_asset is not None:
        path = getattr(current_asset, "path", None)
        kind = getattr(getattr(current_asset, "kind", None), "value", "")
        if path is not None and kind == "image":
            image = QImage(str(path))
            if not image.isNull():
                return image

    return QImage()


def _pending_state(
    parent: QWidget | None,
    **overrides,
) -> EditState:
    """현재 Pending edits 복사본에 dialog 임시 값을 적용한다."""
    state = None
    if parent is not None:
        getter = getattr(parent, "_current_edits", None)
        if callable(getter):
            state = getter()

    copied = replace(state) if isinstance(state, EditState) else EditState()
    for name, value in overrides.items():
        setattr(copied, name, value)
    return copied


def _render_pending(
    parent: QWidget | None,
    **overrides,
) -> QImage:
    """현재 전체 pipeline + dialog 임시 값을 preview용 image로 계산한다."""
    return apply_preview_edits(
        _source_image(parent),
        _pending_state(parent, **overrides),
    )


class LiveCropDialog(CropDialog):
    """원본 좌표 crop 작업과 최종 pipeline preview를 동시에 보여준다."""

    def __init__(
        self,
        source_width: int,
        source_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(source_width, source_height, parent)
        self.setWindowTitle("Crop · Live Preview")
        self._preview_parent = parent

        self.final_title = QLabel("Final Preview")
        self.final_title.setObjectName("sectionTitle")
        self.final_preview = ImagePreviewLabel(QImage())
        self.final_preview.setMinimumSize(360, 200)
        self.final_preview.setMaximumHeight(260)

        layout = self.layout()
        info_index = layout.indexOf(self.info)
        layout.insertWidget(info_index, self.final_title)
        layout.insertWidget(info_index + 1, self.final_preview)

        self.crop_preview.selection_changed.connect(
            lambda _rect: self._refresh_final_preview()
        )
        self._refresh_final_preview()

    def _refresh_final_preview(self) -> None:
        self.final_preview.set_preview_image(
            _render_pending(
                self._preview_parent,
                crop=self.crop_preview.source_rect,
            )
        )


class LiveResizeDialog(QDialog):
    """누적 편집 결과를 보면서 Resize를 즉시 조절한다."""

    PRESETS = [
        ("Original", None),
        ("1920 × 1080", (1920, 1080)),
        ("1280 × 720", (1280, 720)),
        ("854 × 480", (854, 480)),
        ("640 × 360", (640, 360)),
    ]

    def __init__(
        self,
        source_width: int,
        source_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resize · Live Preview")
        self.setModal(True)
        self.resize(800, 680)
        self._parent_window = parent
        self._source_width = source_width
        self._source_height = source_height
        self._syncing = False

        self.preview = ImagePreviewLabel(_render_pending(parent, resize=None))
        self.preview.setMinimumHeight(360)

        self.width_spin = self._spin(source_width)
        self.height_spin = self._spin(source_height)
        self.keep_ratio = QCheckBox("가로세로 비율 유지")
        self.keep_ratio.setChecked(True)

        preset_row = QHBoxLayout()
        for label, size in self.PRESETS:
            button = QPushButton(label)
            button.setObjectName("secondaryButton")
            button.clicked.connect(
                lambda _checked=False, value=size: self._set_preset(value)
            )
            preset_row.addWidget(button)

        self.info = QLabel()
        self.info.setObjectName("selectionInfo")

        form = QFormLayout()
        form.addRow("Width", self.width_spin)
        form.addRow("Height", self.height_spin)
        form.addRow("", self.keep_ratio)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("현재 Pending edits를 포함한 최종 화면을 보면서 크기를 조절하세요.")
        )
        layout.addWidget(self.preview, stretch=1)
        layout.addLayout(preset_row)
        layout.addWidget(self.info)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.width_spin.valueChanged.connect(self._width_changed)
        self.height_spin.valueChanged.connect(self._height_changed)
        self._refresh()

    @property
    def output_size(self) -> tuple[int, int]:
        return self.width_spin.value(), self.height_spin.value()

    def _spin(self, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, 16384)
        spin.setValue(value)
        spin.setSuffix(" px")
        return spin

    def _set_preset(self, size: tuple[int, int] | None) -> None:
        if size is None:
            width, height = self._source_width, self._source_height
        else:
            width, height = size
            if self.keep_ratio.isChecked():
                scale = min(
                    width / self._source_width,
                    height / self._source_height,
                )
                width = max(1, round(self._source_width * scale))
                height = max(1, round(self._source_height * scale))

        self._syncing = True
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self._syncing = False
        self._refresh()

    def _width_changed(self, width: int) -> None:
        if not self._syncing and self.keep_ratio.isChecked():
            self._syncing = True
            self.height_spin.setValue(
                max(
                    1,
                    round(width * self._source_height / self._source_width),
                )
            )
            self._syncing = False
        self._refresh()

    def _height_changed(self, height: int) -> None:
        if not self._syncing and self.keep_ratio.isChecked():
            self._syncing = True
            self.width_spin.setValue(
                max(
                    1,
                    round(height * self._source_width / self._source_height),
                )
            )
            self._syncing = False
        self._refresh()

    def _refresh(self) -> None:
        width, height = self.output_size
        self.preview.set_preview_image(
            _render_pending(
                self._parent_window,
                resize=(width, height),
            )
        )
        self.info.setText(
            f"최종 Resize {width} × {height} px · 변경 즉시 Preview 반영"
        )


class LiveRotateDialog(QDialog):
    """Dial과 quick preset으로 누적 결과를 보며 90도 단위 회전한다."""

    def __init__(
        self,
        initial_degrees: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rotate · Live Preview")
        self.setModal(True)
        self.resize(800, 700)
        self._parent_window = parent

        self.preview = ImagePreviewLabel(QImage())
        self.preview.setMinimumHeight(390)

        self.dial = QDial()
        self.dial.setRange(0, 3)
        self.dial.setSingleStep(1)
        self.dial.setPageStep(1)
        self.dial.setNotchesVisible(True)
        self.dial.setWrapping(True)
        self.dial.setFixedSize(120, 120)

        self.angle_label = QLabel()
        self.angle_label.setObjectName("selectionInfo")

        dial_row = QHBoxLayout()
        dial_row.addStretch()
        dial_row.addWidget(self.dial)
        dial_row.addStretch()

        quick = QHBoxLayout()
        for text, degrees in (
            ("0°", 0),
            ("↻ 90°", 90),
            ("180°", 180),
            ("↺ 90°", 270),
        ):
            button = QPushButton(text)
            button.setObjectName("secondaryButton")
            button.clicked.connect(
                lambda _checked=False, value=degrees: self.set_degrees(value)
            )
            quick.addWidget(button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Dial을 돌리면 현재 Crop / Resize 등 모든 Pending edits를 포함한 "
                "최종 화면이 즉시 갱신됩니다."
            )
        )
        layout.addWidget(self.preview, stretch=1)
        layout.addWidget(self.angle_label)
        layout.addLayout(dial_row)
        layout.addLayout(quick)
        layout.addWidget(buttons)

        self.dial.valueChanged.connect(self._refresh)
        self.set_degrees(initial_degrees)

    @property
    def degrees(self) -> int:
        return self.dial.value() * 90

    def set_degrees(self, degrees: int) -> None:
        snapped = (round(degrees / 90) * 90) % 360
        self.dial.setValue(snapped // 90)
        self._refresh()

    def _refresh(self) -> None:
        rotation = None if self.degrees == 0 else self.degrees
        self.preview.set_preview_image(
            _render_pending(
                self._parent_window,
                rotation=rotation,
            )
        )
        self.angle_label.setText(
            f"회전 {self.degrees}° · 변경 즉시 최종 Preview 반영"
        )


class LiveUpscaleDialog(QDialog):
    """현재 전체 편집 결과와 최종 pixel 수를 함께 보여준다."""

    def __init__(
        self,
        current_scale: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Upscale · Live Preview")
        self.setModal(True)
        self.resize(760, 620)
        self._parent_window = parent
        self._scale = current_scale if current_scale in (2, 4) else 2

        self.preview = ImagePreviewLabel(_render_pending(parent))
        self.preview.setMinimumHeight(350)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(0, 1)
        self.scale_slider.setSingleStep(1)
        self.scale_slider.setValue(0 if self._scale == 2 else 1)

        self.info = QLabel()
        self.info.setObjectName("selectionInfo")

        quick = QHBoxLayout()
        for scale in (2, 4):
            button = QPushButton(f"{scale}×")
            button.setObjectName("secondaryButton")
            button.clicked.connect(
                lambda _checked=False, value=scale: self.set_scale(value)
            )
            quick.addWidget(button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "현재 최종 화면을 유지한 채 출력 pixel 수를 확대합니다. "
                "Preview는 성능을 위해 실제 2×/4× bitmap을 만들지 않습니다."
            )
        )
        layout.addWidget(self.preview, stretch=1)
        layout.addWidget(self.scale_slider)
        layout.addLayout(quick)
        layout.addWidget(self.info)
        layout.addWidget(buttons)

        self.scale_slider.valueChanged.connect(self._slider_changed)
        self._refresh_info()

    @property
    def scale(self) -> int:
        return self._scale

    def set_scale(self, scale: int) -> None:
        self._scale = 2 if scale == 2 else 4
        self.scale_slider.setValue(0 if self._scale == 2 else 1)
        self._refresh_info()

    def _slider_changed(self, value: int) -> None:
        self._scale = 2 if value == 0 else 4
        self._refresh_info()

    def _refresh_info(self) -> None:
        getter = getattr(self._parent_window, "_current_media_size", None)
        size = getter() if callable(getter) else None
        if size is None:
            self.info.setText(f"Upscale {self._scale}×")
            return

        width, height = size
        self.info.setText(
            f"예상 출력 {width * self._scale} × {height * self._scale} px · "
            "현재 누적 편집 결과 Preview 유지"
        )


class LiveTrimDialog(QDialog):
    """누적 공간 편집과 Speed를 그대로 반영해 Trim 구간을 조절한다."""

    def __init__(
        self,
        duration_ms: int,
        current_position_ms: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trim · Live Preview")
        self.setModal(True)
        self.resize(840, 740)
        self.setMinimumSize(720, 640)

        self._duration_ms = duration_ms
        self._syncing = False
        self._seek_dragging = False
        self._parent_window = parent
        state = _pending_state(parent)

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.preview = EditedVideoWidget()
        self.preview.setMinimumHeight(360)
        self.preview.set_edit_provider(lambda: _pending_state(parent))
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoSink(self.preview.videoSink())

        media_path = self._current_media_path(parent)
        if media_path is not None:
            self.player.setSource(QUrl.fromLocalFile(str(media_path)))

        self.player.setPlaybackRate(
            1.0 if state.speed is None else state.speed
        )

        self.play_button = QPushButton("▶ Play")
        self.play_button.setObjectName("primaryButton")
        self.play_button.clicked.connect(self._toggle_playback)

        self.preview_position = QSlider(Qt.Orientation.Horizontal)
        self.preview_position.setRange(0, duration_ms)
        self.preview_position.setValue(current_position_ms)
        self.preview_position.sliderPressed.connect(self._seek_pressed)
        self.preview_position.sliderReleased.connect(self._seek_released)
        self.preview_position.sliderMoved.connect(self._seek_moved)

        self.preview_time = QLabel(self._format_time(current_position_ms))
        self.preview_time.setObjectName("timeLabel")

        playback = QHBoxLayout()
        playback.addWidget(self.play_button)
        playback.addWidget(self.preview_position, stretch=1)
        playback.addWidget(self.preview_time)

        self.start_slider = self._range_slider()
        self.end_slider = self._range_slider()
        self.start_spin = self._time_spin()
        self.end_spin = self._time_spin()

        self.start_slider.setValue(0)
        self.end_slider.setValue(duration_ms)
        self.start_spin.setRange(0.0, duration_ms / 1000)
        self.end_spin.setRange(0.0, duration_ms / 1000)
        self.start_spin.setValue(0.0)
        self.end_spin.setValue(duration_ms / 1000)

        self.start_slider.valueChanged.connect(self._sync_sliders)
        self.end_slider.valueChanged.connect(self._sync_sliders)
        self.start_spin.valueChanged.connect(self._sync_spins)
        self.end_spin.valueChanged.connect(self._sync_spins)

        self.range_info = QLabel()
        self.range_info.setObjectName("selectionInfo")

        quick = QHBoxLayout()
        for text, callback in (
            ("Start = 현재 위치", lambda: self.start_slider.setValue(self.player.position())),
            ("End = 현재 위치", lambda: self.end_slider.setValue(self.player.position())),
            ("전체 길이", self._reset_range),
        ):
            button = QPushButton(text)
            button.setObjectName("secondaryButton")
            button.clicked.connect(callback)
            quick.addWidget(button)
        quick.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "현재 Crop / Rotate / Resize와 Speed를 반영한 영상으로 "
                "Trim 시작/끝을 정합니다."
            )
        )
        layout.addWidget(self.preview, stretch=1)
        layout.addLayout(playback)
        layout.addWidget(self.range_info)
        layout.addLayout(quick)
        layout.addWidget(self._range_row("Start", self.start_slider, self.start_spin))
        layout.addWidget(self._range_row("End", self.end_slider, self.end_spin))
        layout.addWidget(buttons)

        self.player.positionChanged.connect(self._position_changed)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
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
        asset = getattr(parent, "current_asset", None) if parent is not None else None
        path = getattr(asset, "path", None)
        return Path(path) if path is not None else None

    def _range_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, self._duration_ms)
        slider.setSingleStep(100)
        slider.setPageStep(1000)
        return slider

    def _time_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setSingleStep(0.1)
        spin.setSuffix(" s")
        return spin

    def _range_row(
        self,
        name: str,
        slider: QSlider,
        spin: QDoubleSpinBox,
    ) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(name))
        layout.addWidget(slider, stretch=1)
        layout.addWidget(spin)
        return row

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return

        if self.player.position() < self.start_ms or self.player.position() >= self.end_ms:
            self.player.setPosition(self.start_ms)
        self.player.play()

    def _playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.play_button.setText(
            "Ⅱ Pause"
            if state == QMediaPlayer.PlaybackState.PlayingState
            else "▶ Play"
        )

    def _position_changed(self, position: int) -> None:
        if not self._seek_dragging:
            self.preview_position.setValue(position)
        self.preview_time.setText(self._format_time(position))

        if (
            self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            and position >= self.end_ms
        ):
            self.player.pause()
            self.player.setPosition(self.start_ms)

    def _seek_pressed(self) -> None:
        self._seek_dragging = True

    def _seek_released(self) -> None:
        self._seek_dragging = False
        self.player.setPosition(self.preview_position.value())

    def _seek_moved(self, position: int) -> None:
        self.preview_time.setText(self._format_time(position))

    def _sync_sliders(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        self.start_spin.setValue(self.start_ms / 1000)
        self.end_spin.setValue(self.end_ms / 1000)
        self._syncing = False
        self._update_range_info()

    def _sync_spins(self) -> None:
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
        state = _pending_state(self._parent_window)
        speed = 1.0 if state.speed is None else state.speed
        output = selected / speed
        self.range_info.setText(
            f"선택 {self._format_time(self.start_ms)} → "
            f"{self._format_time(self.end_ms)} · "
            f"원본 구간 {selected / 1000:.3f}s · "
            f"현재 Speed 기준 약 {output / 1000:.3f}s"
        )

    def _validate_and_accept(self) -> None:
        if self.end_ms <= self.start_ms:
            QMessageBox.warning(
                self,
                "Trim",
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
