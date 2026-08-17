from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TrimDialog(QDialog):
    """영상의 trim 시작/끝 시간을 선택한다."""

    def __init__(
        self,
        duration_ms: int,
        current_position_ms: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trim Video")
        self.setModal(True)
        self.setMinimumWidth(390)

        self._duration_ms = duration_ms
        self._current_position_ms = current_position_ms

        self.start_spin = self._create_time_spin()
        self.end_spin = self._create_time_spin()

        duration_seconds = duration_ms / 1000
        self.start_spin.setRange(0.0, duration_seconds)
        self.end_spin.setRange(0.0, duration_seconds)
        self.start_spin.setValue(0.0)
        self.end_spin.setValue(duration_seconds)

        description = QLabel(
            "남길 영상 구간을 지정하세요. 현재 preview 위치를 바로 사용할 수 있습니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Start", self._build_time_row(self.start_spin))
        form.addRow("End", self._build_time_row(self.end_spin))

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
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def start_ms(self) -> int:
        return round(self.start_spin.value() * 1000)

    @property
    def end_ms(self) -> int:
        return round(self.end_spin.value() * 1000)

    def _create_time_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setSingleStep(0.1)
        spin.setSuffix(" s")
        return spin

    def _build_time_row(self, spin: QDoubleSpinBox) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        use_current = QPushButton("현재 위치")
        use_current.setObjectName("secondaryButton")
        use_current.clicked.connect(
            lambda: spin.setValue(self._current_position_ms / 1000)
        )

        layout.addWidget(spin, stretch=1)
        layout.addWidget(use_current)
        return row

    def _validate_and_accept(self) -> None:
        if self.end_ms <= self.start_ms:
            QMessageBox.warning(
                self,
                "Trim Video",
                "End는 Start보다 뒤에 있어야 합니다.",
            )
            return

        if self.end_ms > self._duration_ms:
            QMessageBox.warning(
                self,
                "Trim Video",
                "End가 영상 길이를 초과했습니다.",
            )
            return

        self.accept()
