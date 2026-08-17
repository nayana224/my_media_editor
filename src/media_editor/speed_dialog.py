from PySide6.QtCore import Qt, Signal
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


class SpeedDialog(QDialog):
    """슬라이더와 preset으로 영상 배속을 설정한다."""

    rate_changed = Signal(float)

    PRESETS = (0.5, 1.0, 1.5, 2.0, 4.0)

    def __init__(
        self,
        current_rate: float,
        source_duration_ms: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Speed")
        self.setModal(True)
        self.resize(620, 330)
        self.setMinimumWidth(560)

        self._source_duration_ms = max(0, source_duration_ms)
        self._syncing = False

        description = QLabel(
            "재생 속도를 조절하세요. 슬라이더를 움직이면 Preview 배속도 즉시 바뀝니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

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

        preset_layout = QHBoxLayout()
        for rate in self.PRESETS:
            button = QPushButton(f"{rate:g}×")
            button.setObjectName("secondaryButton")
            button.clicked.connect(
                lambda _checked=False, value=rate: self.set_rate(value)
            )
            preset_layout.addWidget(button)

        scale_labels = QHBoxLayout()
        scale_labels.addWidget(QLabel("0.25×"))
        scale_labels.addStretch()
        scale_labels.addWidget(QLabel("1×"))
        scale_labels.addStretch()
        scale_labels.addWidget(QLabel("4×"))

        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Speed"))
        rate_row.addWidget(self.slider, stretch=1)
        rate_row.addWidget(self.rate_spin)

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
        layout.setSpacing(14)
        layout.addWidget(description)
        layout.addWidget(self.rate_label)
        layout.addLayout(rate_row)
        layout.addLayout(scale_labels)
        layout.addLayout(preset_layout)
        layout.addWidget(self.duration_label)
        layout.addStretch()
        layout.addWidget(buttons)

        self.slider.valueChanged.connect(self._slider_changed)
        self.rate_spin.valueChanged.connect(self._spin_changed)

        self.set_rate(current_rate, emit_signal=False)

    @property
    def rate(self) -> float:
        return round(self.rate_spin.value(), 2)

    def set_rate(self, rate: float, emit_signal: bool = True) -> None:
        rate = min(4.0, max(0.25, float(rate)))
        self._syncing = True
        self.slider.setValue(round(rate * 100))
        self.rate_spin.setValue(rate)
        self._syncing = False
        self._refresh_info()
        if emit_signal:
            self.rate_changed.emit(self.rate)

    def _slider_changed(self, value: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        self.rate_spin.setValue(value / 100)
        self._syncing = False
        self._refresh_info()
        self.rate_changed.emit(self.rate)

    def _spin_changed(self, value: float) -> None:
        if self._syncing:
            return
        self._syncing = True
        self.slider.setValue(round(value * 100))
        self._syncing = False
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
            f"예상 길이  {self._format_time(output_ms)}  "
            f"· 원본/선택 구간 {self._format_time(self._source_duration_ms)}"
        )

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds) / 1000
        minutes = int(total_seconds // 60)
        seconds = total_seconds - minutes * 60
        return f"{minutes:02d}:{seconds:05.2f}"
