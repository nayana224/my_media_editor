from PySide6.QtCore import Qt
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
    """슬라이더와 시간 입력으로 영상 trim 구간을 선택한다."""

    def __init__(
        self,
        duration_ms: int,
        current_position_ms: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trim Video")
        self.setModal(True)
        self.setMinimumWidth(520)

        self._duration_ms = duration_ms
        self._current_position_ms = current_position_ms
        self._syncing = False

        description = QLabel(
            "남길 구간의 시작과 끝을 슬라이더로 조절하세요. "
            "현재 preview 위치를 바로 시작/끝으로 지정할 수도 있습니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        self.start_slider = self._create_slider()
        self.end_slider = self._create_slider()
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

        start_row = self._build_row(
            "Start",
            self.start_slider,
            self.start_spin,
            self._set_start_to_current,
        )
        end_row = self._build_row(
            "End",
            self.end_slider,
            self.end_spin,
            self._set_end_to_current,
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addWidget(description)
        layout.addWidget(start_row)
        layout.addWidget(end_row)
        layout.addWidget(buttons)

    @property
    def start_ms(self) -> int:
        return self.start_slider.value()

    @property
    def end_ms(self) -> int:
        return self.end_slider.value()

    def _create_slider(self) -> QSlider:
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

    def _build_row(
        self,
        label_text: str,
        slider: QSlider,
        spin: QDoubleSpinBox,
        current_callback,
    ) -> QWidget:
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        header = QHBoxLayout()
        label = QLabel(label_text)
        label.setObjectName("sectionTitle")
        current_button = QPushButton("현재 위치 사용")
        current_button.setObjectName("secondaryButton")
        current_button.clicked.connect(current_callback)

        header.addWidget(label)
        header.addStretch()
        header.addWidget(spin)
        header.addWidget(current_button)

        row_layout.addLayout(header)
        row_layout.addWidget(slider)
        return row

    def _sync_from_sliders(self) -> None:
        if self._syncing:
            return

        self._syncing = True
        self.start_spin.setValue(self.start_slider.value() / 1000)
        self.end_spin.setValue(self.end_slider.value() / 1000)
        self._syncing = False

    def _sync_from_spins(self) -> None:
        if self._syncing:
            return

        self._syncing = True
        self.start_slider.setValue(round(self.start_spin.value() * 1000))
        self.end_slider.setValue(round(self.end_spin.value() * 1000))
        self._syncing = False

    def _set_start_to_current(self) -> None:
        self.start_slider.setValue(self._current_position_ms)

    def _set_end_to_current(self) -> None:
        self.end_slider.setValue(self._current_position_ms)

    def _validate_and_accept(self) -> None:
        if self.end_ms <= self.start_ms:
            QMessageBox.warning(
                self,
                "Trim Video",
                "End는 Start보다 뒤에 있어야 합니다.",
            )
            return

        self.accept()
