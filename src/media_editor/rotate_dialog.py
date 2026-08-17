from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QTransform
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDial,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from media_editor.preview_transform import PREVIEW_MAX_DIMENSION
from media_editor.transform_dialogs import ImagePreviewLabel


class RotateDialog(QDialog):
    """Dial과 quick preset으로 90도 단위 회전을 미리 본다."""

    ROTATIONS = (0, 90, 180, 270)

    def __init__(
        self,
        base_image: QImage,
        current_degrees: int = 0,
        post_resize: tuple[int, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rotate")
        self.setModal(True)
        self.resize(780, 690)
        self.setMinimumSize(680, 600)

        self._base_image = base_image.copy()
        self._post_resize = post_resize

        description = QLabel(
            "다이얼을 드래그해 회전하세요. 최종 출력은 0° / 90° / 180° / 270°에 스냅됩니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        self.preview = ImagePreviewLabel(self._base_image)

        self.angle_label = QLabel()
        self.angle_label.setObjectName("selectionInfo")
        self.angle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dial = QDial()
        self.dial.setRange(0, 3)
        self.dial.setSingleStep(1)
        self.dial.setPageStep(1)
        self.dial.setWrapping(True)
        self.dial.setNotchesVisible(True)
        self.dial.setFixedSize(150, 150)
        self.dial.valueChanged.connect(self._refresh_preview)

        presets = QHBoxLayout()
        for degrees, label in (
            (0, "0°"),
            (90, "↻ 90°"),
            (180, "180°"),
            (270, "↺ 90°"),
        ):
            button = QPushButton(label)
            button.setObjectName("secondaryButton")
            button.clicked.connect(
                lambda _checked=False, value=degrees: self.set_degrees(value)
            )
            presets.addWidget(button)

        dial_row = QHBoxLayout()
        dial_row.addStretch()
        dial_row.addWidget(self.dial)
        dial_row.addStretch()

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
        layout.addWidget(self.angle_label)
        layout.addLayout(dial_row)
        layout.addLayout(presets)
        layout.addWidget(buttons)

        self.set_degrees(current_degrees)

    @property
    def degrees(self) -> int:
        return self.ROTATIONS[self.dial.value()]

    def set_degrees(self, degrees: int) -> None:
        normalized = degrees % 360
        if normalized not in self.ROTATIONS:
            normalized = min(
                self.ROTATIONS,
                key=lambda value: min(
                    abs(value - normalized),
                    360 - abs(value - normalized),
                ),
            )
        self.dial.setValue(self.ROTATIONS.index(normalized))
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        degrees = self.degrees
        self.angle_label.setText(
            f"{degrees}° · 다이얼 또는 아래 preset 버튼으로 조절"
        )

        if self._base_image.isNull():
            return

        image = self._base_image
        if degrees:
            image = image.transformed(
                QTransform().rotate(degrees),
                Qt.TransformationMode.SmoothTransformation,
            )

        if self._post_resize is not None:
            width, height = self._post_resize
            largest = max(width, height)
            if largest > PREVIEW_MAX_DIMENSION:
                scale = PREVIEW_MAX_DIMENSION / largest
                width = max(1, round(width * scale))
                height = max(1, round(height * scale))
            image = image.scaled(
                width,
                height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        self.preview.set_preview_image(image)
