from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CropSelectionWidget(QWidget):
    """Preview 위에서 crop 영역을 직접 선택한다."""

    selection_changed = Signal(object)

    HANDLE_SIZE = 12.0
    MIN_SELECTION_PX = 2.0

    def __init__(
        self,
        preview_pixmap: QPixmap,
        source_width: int,
        source_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 360)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._preview_pixmap = preview_pixmap
        self._source_width = source_width
        self._source_height = source_height
        self._selection = QRectF(
            0.0,
            0.0,
            float(source_width),
            float(source_height),
        )
        self._aspect_ratio: float | None = None
        self._drag_mode: str | None = None
        self._press_source = QPointF()
        self._initial_selection = QRectF()

    @property
    def source_rect(self) -> tuple[int, int, int, int]:
        rect = self._selection.normalized()
        x = max(0, round(rect.x()))
        y = max(0, round(rect.y()))
        width = max(1, round(rect.width()))
        height = max(1, round(rect.height()))

        if x + width > self._source_width:
            width = self._source_width - x
        if y + height > self._source_height:
            height = self._source_height - y

        return x, y, max(1, width), max(1, height)

    def set_source_rect(self, rect: tuple[int, int, int, int]) -> None:
        x, y, width, height = rect
        x = min(max(0, x), self._source_width - 1)
        y = min(max(0, y), self._source_height - 1)
        width = min(max(1, width), self._source_width - x)
        height = min(max(1, height), self._source_height - y)

        self._selection = QRectF(
            float(x),
            float(y),
            float(width),
            float(height),
        )
        self.selection_changed.emit(self.source_rect)
        self.update()

    def set_aspect_ratio(self, ratio: float | None) -> None:
        self._aspect_ratio = ratio
        if ratio is None:
            return

        max_width = float(self._source_width)
        max_height = float(self._source_height)
        width = min(max_width, max_height * ratio)
        height = width / ratio
        if height > max_height:
            height = max_height
            width = height * ratio

        x = (max_width - width) / 2
        y = (max_height - height) / 2
        self._selection = QRectF(x, y, width, height)
        self.selection_changed.emit(self.source_rect)
        self.update()

    def reset_full_frame(self) -> None:
        self._aspect_ratio = None
        self.set_source_rect(
            (0, 0, self._source_width, self._source_height)
        )

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        media_rect = self._media_rect()
        painter.fillRect(self.rect(), QColor("#0c0e12"))
        if not self._preview_pixmap.isNull():
            painter.drawPixmap(media_rect.toRect(), self._preview_pixmap)

        selection_rect = self._source_to_display_rect(self._selection)
        shade = QColor(0, 0, 0, 150)

        painter.fillRect(
            QRectF(
                media_rect.left(),
                media_rect.top(),
                media_rect.width(),
                max(0.0, selection_rect.top() - media_rect.top()),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                media_rect.left(),
                selection_rect.bottom(),
                media_rect.width(),
                max(0.0, media_rect.bottom() - selection_rect.bottom()),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                media_rect.left(),
                selection_rect.top(),
                max(0.0, selection_rect.left() - media_rect.left()),
                selection_rect.height(),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                selection_rect.right(),
                selection_rect.top(),
                max(0.0, media_rect.right() - selection_rect.right()),
                selection_rect.height(),
            ),
            shade,
        )

        border_pen = QPen(QColor("#7f96ff"))
        border_pen.setWidth(2)
        painter.setPen(border_pen)
        painter.drawRect(selection_rect)

        grid_pen = QPen(QColor(255, 255, 255, 120))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for fraction in (1 / 3, 2 / 3):
            x = selection_rect.left() + selection_rect.width() * fraction
            y = selection_rect.top() + selection_rect.height() * fraction
            painter.drawLine(
                QPointF(x, selection_rect.top()),
                QPointF(x, selection_rect.bottom()),
            )
            painter.drawLine(
                QPointF(selection_rect.left(), y),
                QPointF(selection_rect.right(), y),
            )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        for handle in self._handle_rects(selection_rect).values():
            painter.drawRoundedRect(handle, 2.0, 2.0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        source_point = self._display_to_source(event.position())
        if source_point is None:
            return

        display_selection = self._source_to_display_rect(self._selection)
        handle = self._hit_handle(event.position(), display_selection)

        self._press_source = source_point
        self._initial_selection = QRectF(self._selection)

        if handle is not None:
            self._drag_mode = handle
        elif display_selection.contains(event.position()):
            self._drag_mode = "move"
        else:
            self._drag_mode = "new"

        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_mode is None:
            self._update_cursor(event.position())
            return

        source_point = self._display_to_source(event.position(), clamp=True)
        if source_point is None:
            return

        if self._drag_mode == "move":
            self._move_selection(source_point)
        elif self._drag_mode == "new":
            self._resize_from_anchor(self._press_source, source_point)
        else:
            self._resize_from_handle(self._drag_mode, source_point)

        self.selection_changed.emit(self.source_rect)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_mode = None
            self.selection_changed.emit(self.source_rect)
            self.update()
        event.accept()

    def _media_rect(self) -> QRectF:
        available = QRectF(self.rect()).adjusted(8.0, 8.0, -8.0, -8.0)
        scale = min(
            available.width() / self._source_width,
            available.height() / self._source_height,
        )
        width = self._source_width * scale
        height = self._source_height * scale
        return QRectF(
            available.center().x() - width / 2,
            available.center().y() - height / 2,
            width,
            height,
        )

    def _source_to_display_rect(self, source_rect: QRectF) -> QRectF:
        media = self._media_rect()
        scale_x = media.width() / self._source_width
        scale_y = media.height() / self._source_height
        return QRectF(
            media.left() + source_rect.left() * scale_x,
            media.top() + source_rect.top() * scale_y,
            source_rect.width() * scale_x,
            source_rect.height() * scale_y,
        )

    def _display_to_source(
        self,
        point: QPointF,
        clamp: bool = False,
    ) -> QPointF | None:
        media = self._media_rect()
        if not media.contains(point) and not clamp:
            return None

        x = (point.x() - media.left()) * self._source_width / media.width()
        y = (point.y() - media.top()) * self._source_height / media.height()
        if clamp:
            x = min(max(0.0, x), float(self._source_width))
            y = min(max(0.0, y), float(self._source_height))
        return QPointF(x, y)

    def _handle_rects(self, rect: QRectF) -> dict[str, QRectF]:
        half = self.HANDLE_SIZE / 2
        return {
            "top_left": QRectF(
                rect.left() - half,
                rect.top() - half,
                self.HANDLE_SIZE,
                self.HANDLE_SIZE,
            ),
            "top_right": QRectF(
                rect.right() - half,
                rect.top() - half,
                self.HANDLE_SIZE,
                self.HANDLE_SIZE,
            ),
            "bottom_left": QRectF(
                rect.left() - half,
                rect.bottom() - half,
                self.HANDLE_SIZE,
                self.HANDLE_SIZE,
            ),
            "bottom_right": QRectF(
                rect.right() - half,
                rect.bottom() - half,
                self.HANDLE_SIZE,
                self.HANDLE_SIZE,
            ),
        }

    def _hit_handle(
        self,
        point: QPointF,
        rect: QRectF,
    ) -> str | None:
        for name, handle in self._handle_rects(rect).items():
            if handle.contains(point):
                return name
        return None

    def _update_cursor(self, point: QPointF) -> None:
        display_selection = self._source_to_display_rect(self._selection)
        handle = self._hit_handle(point, display_selection)
        if handle in ("top_left", "bottom_right"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in ("top_right", "bottom_left"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif display_selection.contains(point):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _move_selection(self, source_point: QPointF) -> None:
        delta = source_point - self._press_source
        rect = QRectF(self._initial_selection)
        rect.translate(delta)

        if rect.left() < 0:
            rect.moveLeft(0)
        if rect.top() < 0:
            rect.moveTop(0)
        if rect.right() > self._source_width:
            rect.moveRight(self._source_width)
        if rect.bottom() > self._source_height:
            rect.moveBottom(self._source_height)

        self._selection = rect

    def _resize_from_handle(
        self,
        handle: str,
        source_point: QPointF,
    ) -> None:
        rect = self._initial_selection

        if handle == "top_left":
            anchor = rect.bottomRight()
        elif handle == "top_right":
            anchor = rect.bottomLeft()
        elif handle == "bottom_left":
            anchor = rect.topRight()
        else:
            anchor = rect.topLeft()

        self._selection = self._rect_from_anchor(anchor, source_point)

    def _resize_from_anchor(
        self,
        anchor: QPointF,
        source_point: QPointF,
    ) -> None:
        self._selection = self._rect_from_anchor(anchor, source_point)

    def _rect_from_anchor(
        self,
        anchor: QPointF,
        point: QPointF,
    ) -> QRectF:
        dx = point.x() - anchor.x()
        dy = point.y() - anchor.y()
        sign_x = 1.0 if dx >= 0 else -1.0
        sign_y = 1.0 if dy >= 0 else -1.0

        width = max(self.MIN_SELECTION_PX, abs(dx))
        height = max(self.MIN_SELECTION_PX, abs(dy))

        if self._aspect_ratio is not None:
            ratio = self._aspect_ratio
            if height == 0 or width / height > ratio:
                height = width / ratio
            else:
                width = height * ratio

        max_width = (
            self._source_width - anchor.x()
            if sign_x > 0
            else anchor.x()
        )
        max_height = (
            self._source_height - anchor.y()
            if sign_y > 0
            else anchor.y()
        )

        if self._aspect_ratio is not None:
            factor = min(
                1.0,
                max_width / width if width > 0 else 1.0,
                max_height / height if height > 0 else 1.0,
            )
            width *= factor
            height *= factor
        else:
            width = min(width, max_width)
            height = min(height, max_height)

        end = QPointF(
            anchor.x() + width * sign_x,
            anchor.y() + height * sign_y,
        )
        return QRectF(anchor, end).normalized()


class CropDialog(QDialog):
    """Preview에서 crop 영역을 직접 선택한다."""

    ASPECT_RATIOS = [
        ("자유", None),
        ("원본 비율", "source"),
        ("16 : 9", 16 / 9),
        ("4 : 3", 4 / 3),
        ("1 : 1", 1.0),
    ]

    def __init__(
        self,
        source_width: int,
        source_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crop")
        self.setModal(True)
        self.resize(900, 700)
        self.setMinimumSize(760, 620)

        self._source_width = source_width
        self._source_height = source_height
        self._syncing = False

        preview_pixmap = self._capture_parent_preview(parent)
        self.crop_preview = CropSelectionWidget(
            preview_pixmap,
            source_width,
            source_height,
            self,
        )
        self.crop_preview.selection_changed.connect(
            self._sync_fields_from_preview
        )

        description = QLabel(
            "미리보기에서 마우스로 영역을 새로 그리거나 이동하세요. "
            "네 모서리의 흰색 핸들을 드래그하면 크기를 조절할 수 있습니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        self.aspect_combo = QComboBox()
        for label, value in self.ASPECT_RATIOS:
            self.aspect_combo.addItem(label, value)
        self.aspect_combo.currentIndexChanged.connect(
            self._apply_aspect_ratio
        )

        self.x_spin = self._create_spin(0, source_width - 1, 0)
        self.y_spin = self._create_spin(0, source_height - 1, 0)
        self.width_spin = self._create_spin(1, source_width, source_width)
        self.height_spin = self._create_spin(1, source_height, source_height)

        self.x_spin.valueChanged.connect(self._sync_preview_from_fields)
        self.y_spin.valueChanged.connect(self._sync_preview_from_fields)
        self.width_spin.valueChanged.connect(self._size_field_changed)
        self.height_spin.valueChanged.connect(self._size_field_changed)

        full_button = QPushButton("전체 프레임")
        full_button.setObjectName("secondaryButton")
        full_button.clicked.connect(self._reset_full_frame)

        center_button = QPushButton("가운데 80%")
        center_button.setObjectName("secondaryButton")
        center_button.clicked.connect(self._center_eighty_percent)

        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Aspect"))
        quick_layout.addWidget(self.aspect_combo)
        quick_layout.addStretch()
        quick_layout.addWidget(center_button)
        quick_layout.addWidget(full_button)

        fields = QGridLayout()
        fields.setHorizontalSpacing(10)
        fields.setVerticalSpacing(8)
        fields.addWidget(QLabel("X"), 0, 0)
        fields.addWidget(self.x_spin, 0, 1)
        fields.addWidget(QLabel("Y"), 0, 2)
        fields.addWidget(self.y_spin, 0, 3)
        fields.addWidget(QLabel("Width"), 1, 0)
        fields.addWidget(self.width_spin, 1, 1)
        fields.addWidget(QLabel("Height"), 1, 2)
        fields.addWidget(self.height_spin, 1, 3)

        self.selection_info = QLabel()
        self.selection_info.setObjectName("selectionInfo")
        self._update_selection_info()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(description)
        layout.addLayout(quick_layout)
        layout.addWidget(self.crop_preview, stretch=1)
        layout.addWidget(self.selection_info)
        layout.addLayout(fields)
        layout.addWidget(buttons)

    @property
    def crop_rect(self) -> tuple[int, int, int, int]:
        return self.crop_preview.source_rect

    def _capture_parent_preview(
        self,
        parent: QWidget | None,
    ) -> QPixmap:
        if parent is None:
            return QPixmap()

        preview = getattr(parent, "preview", None)
        if preview is None:
            return QPixmap()

        pixmap = preview.grab()
        if pixmap.isNull():
            return pixmap

        width = pixmap.width()
        height = pixmap.height()
        if width <= 0 or height <= 0:
            return pixmap

        source_ratio = self._source_width / self._source_height
        preview_ratio = width / height

        if preview_ratio > source_ratio:
            content_height = height
            content_width = round(content_height * source_ratio)
            x = max(0, (width - content_width) // 2)
            y = 0
        else:
            content_width = width
            content_height = round(content_width / source_ratio)
            x = 0
            y = max(0, (height - content_height) // 2)

        return pixmap.copy(x, y, content_width, content_height)

    def _create_spin(
        self,
        minimum: int,
        maximum: int,
        value: int,
    ) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(" px")
        return spin

    def _sync_fields_from_preview(
        self,
        rect: tuple[int, int, int, int],
    ) -> None:
        if self._syncing:
            return

        self._syncing = True
        x, y, width, height = rect
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.width_spin.setMaximum(self._source_width - x)
        self.height_spin.setMaximum(self._source_height - y)
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self._syncing = False
        self._update_selection_info()

    def _sync_preview_from_fields(self) -> None:
        if self._syncing:
            return

        self._syncing = True
        x = self.x_spin.value()
        y = self.y_spin.value()
        self.width_spin.setMaximum(max(1, self._source_width - x))
        self.height_spin.setMaximum(max(1, self._source_height - y))
        rect = (
            x,
            y,
            self.width_spin.value(),
            self.height_spin.value(),
        )
        self._syncing = False
        self.crop_preview.set_source_rect(rect)
        self._update_selection_info()

    def _size_field_changed(self) -> None:
        if self._syncing:
            return

        if self.aspect_combo.currentData() is not None:
            self.aspect_combo.setCurrentIndex(0)
        self._sync_preview_from_fields()

    def _apply_aspect_ratio(self) -> None:
        value = self.aspect_combo.currentData()
        if value == "source":
            ratio = self._source_width / self._source_height
        elif value is None:
            ratio = None
        else:
            ratio = float(value)
        self.crop_preview.set_aspect_ratio(ratio)

    def _reset_full_frame(self) -> None:
        self.aspect_combo.setCurrentIndex(0)
        self.crop_preview.reset_full_frame()

    def _center_eighty_percent(self) -> None:
        self.aspect_combo.setCurrentIndex(0)
        width = max(1, round(self._source_width * 0.8))
        height = max(1, round(self._source_height * 0.8))
        x = (self._source_width - width) // 2
        y = (self._source_height - height) // 2
        self.crop_preview.set_source_rect((x, y, width, height))

    def _update_selection_info(self) -> None:
        x, y, width, height = self.crop_preview.source_rect
        percent = width * height / (
            self._source_width * self._source_height
        ) * 100
        self.selection_info.setText(
            f"선택 영역  {width} × {height} px"
            f"   ·   위치 ({x}, {y})"
            f"   ·   원본의 {percent:.1f}%"
        )

    def _validate_and_accept(self) -> None:
        x, y, width, height = self.crop_rect
        if width < 2 or height < 2:
            QMessageBox.warning(
                self,
                "Crop",
                "Crop 영역은 최소 2 × 2 px 이상이어야 합니다.",
            )
            return

        if x + width > self._source_width or y + height > self._source_height:
            QMessageBox.warning(
                self,
                "Crop",
                "Crop 영역이 원본 크기를 벗어났습니다.",
            )
            return

        self.accept()


class ResizeDialog(QDialog):
    """출력 해상도를 preset 또는 직접 입력으로 지정한다."""

    PRESETS = [
        ("Original", None),
        ("1920 × 1080 (1080p)", (1920, 1080)),
        ("1280 × 720 (720p)", (1280, 720)),
        ("854 × 480 (480p)", (854, 480)),
        ("640 × 360 (360p)", (640, 360)),
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
        self.setMinimumWidth(440)
        self._source_width = source_width
        self._source_height = source_height
        self._syncing = False

        description = QLabel(
            f"원본 크기: {source_width} × {source_height} px\n"
            "Preset을 선택하거나 원하는 출력 크기를 직접 입력하세요."
        )
        description.setWordWrap(True)
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

        self.result_info = QLabel()
        self.result_info.setObjectName("selectionInfo")
        self._update_result_info()
        self.width_spin.valueChanged.connect(self._update_result_info)
        self.height_spin.valueChanged.connect(self._update_result_info)

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
        layout.addWidget(self.result_info)
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
        self._update_result_info()

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

    def _update_result_info(self) -> None:
        width, height = self.output_size
        scale = min(
            width / self._source_width,
            height / self._source_height,
        )
        self.result_info.setText(
            f"출력  {width} × {height} px"
            f"   ·   원본 대비 약 {scale * 100:.0f}%"
        )


class RotateDialog(QDialog):
    """90도 단위 회전 방향을 버튼으로 선택한다."""

    OPTIONS = [
        ("↻  90°", 90),
        ("↕  180°", 180),
        ("↺  90°", 270),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rotate")
        self.setModal(True)
        self.setMinimumWidth(420)

        description = QLabel(
            "회전할 방향을 선택하세요. 원본 파일은 변경하지 않습니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        self.group = QButtonGroup(self)
        option_layout = QHBoxLayout()
        for index, (label, degrees) in enumerate(self.OPTIONS):
            radio = QRadioButton(label)
            radio.setProperty("degrees", degrees)
            self.group.addButton(radio)
            option_layout.addWidget(radio)
            if index == 0:
                radio.setChecked(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addWidget(description)
        layout.addLayout(option_layout)
        layout.addWidget(buttons)

    @property
    def degrees(self) -> int:
        button = self.group.checkedButton()
        return int(button.property("degrees"))


class UpscaleDialog(QDialog):
    """Standard upscale 배율을 버튼으로 선택한다."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Upscale")
        self.setModal(True)
        self.setMinimumWidth(430)

        description = QLabel(
            "Standard Upscale은 Lanczos filter로 해상도를 확대합니다.\n"
            "2×는 일반적인 확대에, 4×는 작은 이미지/영상 확대에 적합합니다."
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        self.group = QButtonGroup(self)
        two_x = QRadioButton("2×  ·  빠르고 일반적인 확대")
        four_x = QRadioButton("4×  ·  더 큰 출력")
        two_x.setProperty("scale", 2)
        four_x.setProperty("scale", 4)
        two_x.setChecked(True)
        self.group.addButton(two_x)
        self.group.addButton(four_x)

        ai_note = QLabel(
            "AI Upscale은 이후 Real-ESRGAN backend로 별도 추가할 예정입니다."
        )
        ai_note.setObjectName("selectionInfo")
        ai_note.setWordWrap(True)

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
        layout.addWidget(two_x)
        layout.addWidget(four_x)
        layout.addWidget(ai_note)
        layout.addWidget(buttons)

    @property
    def scale(self) -> int:
        button = self.group.checkedButton()
        return int(button.property("scale"))
