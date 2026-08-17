from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CropDialog(QDialog):
    """원본 크기를 기준으로 crop 영역을 pixel 단위로 지정한다."""

    def __init__(
        self,
        source_width: int,
        source_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crop")
        self.setModal(True)
        self.setMinimumWidth(430)
        self._source_width = source_width
        self._source_height = source_height

        description = QLabel(
            f"원본 크기: {source_width} × {source_height} px\n"
            "남길 영역의 위치와 크기를 지정하세요."
        )
        description.setObjectName("dialogDescription")

        self.x_spin = self._create_spin(0, source_width - 1, 0)
        self.y_spin = self._create_spin(0, source_height - 1, 0)
        self.width_spin = self._create_spin(1, source_width, source_width)
        self.height_spin = self._create_spin(1, source_height, source_height)

        reset_button = QPushButton("전체 영역")
        reset_button.setObjectName("secondaryButton")
        reset_button.clicked.connect(self._reset_full_frame)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Width", self.width_spin)
        form.addRow("Height", self.height_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(description)
        layout.addWidget(reset_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def crop_rect(self) -> tuple[int, int, int, int]:
        return (
            self.x_spin.value(),
            self.y_spin.value(),
            self.width_spin.value(),
            self.height_spin.value(),
        )

    def _create_spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(" px")
        return spin

    def _reset_full_frame(self) -> None:
        self.x_spin.setValue(0)
        self.y_spin.setValue(0)
        self.width_spin.setValue(self._source_width)
        self.height_spin.setValue(self._source_height)

    def _validate_and_accept(self) -> None:
        x, y, width, height = self.crop_rect
        if x + width > self._source_width or y + height > self._source_height:
            QMessageBox.warning(
                self,
                "Crop",
                "Crop 영역이 원본 크기를 벗어났습니다.",
            )
            return
        self.accept()


class ResizeDialog(QDialog):
    """출력 해상도를 GUI에서 지정한다."""

    PRESETS = [
        ("Original", None),
        ("1920 × 1080", (1920, 1080)),
        ("1280 × 720", (1280, 720)),
        ("854 × 480", (854, 480)),
        ("640 × 360", (640, 360)),
        ("Custom", None),
    ]

    def __init__(
        self,
        source_width: int,
        source_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resize")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._source_width = source_width
        self._source_height = source_height
        self._syncing = False

        description = QLabel(
            f"원본 크기: {source_width} × {source_height} px"
        )
        description.setObjectName("dialogDescription")

        self.preset_combo = QComboBox()
        for name, _ in self.PRESETS:
            self.preset_combo.addItem(name)
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)

        self.width_spin = self._create_size_spin(source_width)
        self.height_spin = self._create_size_spin(source_height)
        self.keep_ratio = QCheckBox("가로세로 비율 유지")
        self.keep_ratio.setChecked(True)
        self.keep_ratio.toggled.connect(self._reapply_current_preset)

        self.width_spin.valueChanged.connect(self._width_changed)
        self.height_spin.valueChanged.connect(self._height_changed)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Preset", self.preset_combo)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(description)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def output_size(self) -> tuple[int, int]:
        return self.width_spin.value(), self.height_spin.value()

    def _create_size_spin(self, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, 16384)
        spin.setValue(value)
        spin.setSuffix(" px")
        return spin

    def _apply_preset(self, index: int) -> None:
        _, size = self.PRESETS[index]
        if index == 0:
            size = (self._source_width, self._source_height)
        if size is None:
            return

        width, height = size
        if self.keep_ratio.isChecked() and index != 0:
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

    def _reapply_current_preset(self) -> None:
        self._apply_preset(self.preset_combo.currentIndex())

    def _width_changed(self, width: int) -> None:
        if self._syncing or not self.keep_ratio.isChecked():
            return
        self._syncing = True
        height = round(width * self._source_height / self._source_width)
        self.height_spin.setValue(max(1, height))
        self._syncing = False

    def _height_changed(self, height: int) -> None:
        if self._syncing or not self.keep_ratio.isChecked():
            return
        self._syncing = True
        width = round(height * self._source_width / self._source_height)
        self.width_spin.setValue(max(1, width))
        self._syncing = False


class RotateDialog(QDialog):
    """90도 단위 회전 방향을 선택한다."""

    OPTIONS = [
        ("90° clockwise", 90),
        ("180°", 180),
        ("90° counter-clockwise", 270),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rotate")
        self.setModal(True)
        self.setMinimumWidth(360)

        description = QLabel("회전할 방향을 선택하세요.")
        description.setObjectName("dialogDescription")

        self.combo = QComboBox()
        for label, degrees in self.OPTIONS:
            self.combo.addItem(label, degrees)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(description)
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

    @property
    def degrees(self) -> int:
        return int(self.combo.currentData())


class UpscaleDialog(QDialog):
    """Standard upscale 배율을 선택한다."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Upscale")
        self.setModal(True)
        self.setMinimumWidth(380)

        description = QLabel(
            "Standard Upscale은 Lanczos filter를 사용합니다.\n"
            "AI Upscale은 이후 Real-ESRGAN backend로 추가할 예정입니다."
        )
        description.setObjectName("dialogDescription")

        self.combo = QComboBox()
        self.combo.addItem("Standard 2×", 2)
        self.combo.addItem("Standard 4×", 4)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(description)
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

    @property
    def scale(self) -> int:
        return int(self.combo.currentData())
