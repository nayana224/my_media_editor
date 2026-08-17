from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _capture_parent_preview(parent: QWidget | None) -> QImage:
    """현재 선택된 이미지 또는 video frame을 preview용 QImage로 가져온다."""
    if parent is None:
        return QImage()

    current_asset = getattr(parent, "current_asset", None)
    if current_asset is not None:
        kind = getattr(current_asset, "kind", None)
        if getattr(kind, "value", "") == "image":
            image = QImage(str(current_asset.path))
            if not image.isNull():
                return image

    video_widget = getattr(parent, "video_widget", None)
    if video_widget is not None:
        frame = video_widget.videoSink().videoFrame()
        if frame.isValid():
            image = frame.toImage()
            if not image.isNull():
                return image.copy()

    return QImage()


class ImagePreviewLabel(QLabel):
    """편집 결과를 일정한 preview canvas에 표시한다."""

    def __init__(self, image: QImage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("editPreview")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(560, 315)
        self._image = image.copy()
        self._update_pixmap()

    def set_preview_image(self, image: QImage) -> None:
        self._image = image.copy()
        self._update_pixmap()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self) -> None:
        if self._image.isNull():
            self.setPixmap(QPixmap())
            self.setText("Preview를 준비하지 못했습니다.")
            return

        self.setText("")
        self.setPixmap(
            QPixmap.fromImage(self._image).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class CropSelectionWidget(QWidget):
    """실제 frame 위에서 crop, zoom, pan을 직접 조작한다."""

    selection_changed = Signal(object)
    view_changed = Signal(float)

    HANDLE_SIZE = 12.0
    MIN_SELECTION_PX = 2.0
    MIN_VIEW_SIZE = 32.0

    def __init__(
        self,
        preview_image: QImage,
        source_width: int,
        source_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumSize(680, 400)
        self.setMouseTracking(True)

        self._preview_pixmap = QPixmap.fromImage(preview_image)
        self._source_width = source_width
        self._source_height = source_height
        self._selection = QRectF(
            0.0, 0.0, float(source_width), float(source_height)
        )
        self._view_rect = QRectF(self._selection)
        self._aspect_ratio: float | None = None

        self._drag_mode: str | None = None
        self._press_source = QPointF()
        self._initial_selection = QRectF()
        self._press_display = QPointF()
        self._initial_view_rect = QRectF()

    @property
    def source_rect(self) -> tuple[int, int, int, int]:
        rect = self._selection.normalized()
        x = max(0, round(rect.x()))
        y = max(0, round(rect.y()))
        width = min(max(1, round(rect.width())), self._source_width - x)
        height = min(max(1, round(rect.height())), self._source_height - y)
        return x, y, max(1, width), max(1, height)

    @property
    def zoom_percent(self) -> float:
        if self._view_rect.width() <= 0:
            return 100.0
        return 100.0 * self._source_width / self._view_rect.width()

    def set_source_rect(self, rect: tuple[int, int, int, int]) -> None:
        x, y, width, height = rect
        x = min(max(0, x), self._source_width - 1)
        y = min(max(0, y), self._source_height - 1)
        width = min(max(1, width), self._source_width - x)
        height = min(max(1, height), self._source_height - y)
        self._selection = QRectF(
            float(x), float(y), float(width), float(height)
        )
        self.selection_changed.emit(self.source_rect)
        self.update()

    def set_aspect_ratio(self, ratio: float | None) -> None:
        self._aspect_ratio = ratio
        if ratio is None:
            return

        width = min(
            float(self._source_width),
            float(self._source_height) * ratio,
        )
        height = width / ratio
        if height > self._source_height:
            height = float(self._source_height)
            width = height * ratio

        self._selection = QRectF(
            (self._source_width - width) / 2,
            (self._source_height - height) / 2,
            width,
            height,
        )
        self.selection_changed.emit(self.source_rect)
        self.update()

    def reset_full_frame(self) -> None:
        self._aspect_ratio = None
        self.set_source_rect(
            (0, 0, self._source_width, self._source_height)
        )

    def reset_view(self) -> None:
        self._view_rect = QRectF(
            0.0, 0.0, float(self._source_width), float(self._source_height)
        )
        self._emit_view_changed()

    def fit_selection(self) -> None:
        selection = self._selection.normalized()
        margin_x = max(8.0, selection.width() * 0.15)
        margin_y = max(8.0, selection.height() * 0.15)
        self._view_rect = self._clamp_view_rect(
            selection.adjusted(-margin_x, -margin_y, margin_x, margin_y)
        )
        self._emit_view_changed()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            return

        center = self._display_to_source(event.position(), clamp=True)
        if center is None:
            return

        factor = 0.8 if event.angleDelta().y() > 0 else 1.25
        self._zoom_at(center, factor)
        event.accept()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        media_rect = self._media_rect()
        painter.fillRect(self.rect(), QColor("#0c0e12"))

        if self._preview_pixmap.isNull():
            painter.setPen(QColor("#8f96a3"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Preview를 준비하지 못했습니다.",
            )
        else:
            painter.drawPixmap(
                media_rect.toRect(),
                self._preview_pixmap,
                self._view_rect.toRect(),
            )

        if self._selection.intersected(self._view_rect).isEmpty():
            return

        selection_rect = self._source_to_display_rect(self._selection)
        visible_selection = media_rect.intersected(selection_rect)
        self._paint_shade(
            painter,
            media_rect,
            visible_selection,
            QColor(0, 0, 0, 150),
        )

        border_pen = QPen(QColor("#7f96ff"))
        border_pen.setWidth(2)
        painter.setPen(border_pen)
        painter.drawRect(selection_rect)

        grid_pen = QPen(QColor(255, 255, 255, 120))
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
            if self.rect().intersects(handle.toRect()):
                painter.drawRoundedRect(handle, 2.0, 2.0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._drag_mode = "pan"
            self._press_display = event.position()
            self._initial_view_rect = QRectF(self._view_rect)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

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
        if self._drag_mode == "pan":
            self._pan_view(event.position())
            return

        if self._drag_mode is None:
            self._update_cursor(event.position())
            return

        source_point = self._display_to_source(event.position(), clamp=True)
        if source_point is None:
            return

        if self._drag_mode == "move":
            self._move_selection(source_point)
        elif self._drag_mode == "new":
            self._selection = self._rect_from_anchor(
                self._press_source, source_point
            )
        else:
            self._resize_from_handle(self._drag_mode, source_point)

        self.selection_changed.emit(self.source_rect)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.MiddleButton
            and self._drag_mode == "pan"
        ):
            self._drag_mode = None
            self._update_cursor(event.position())
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_mode = None
            self.selection_changed.emit(self.source_rect)
            self._update_cursor(event.position())
            self.update()
        event.accept()

    def _pan_view(self, point: QPointF) -> None:
        media = self._media_rect()
        if media.width() <= 0 or media.height() <= 0:
            return

        delta = point - self._press_display
        source_dx = delta.x() * self._initial_view_rect.width() / media.width()
        source_dy = delta.y() * self._initial_view_rect.height() / media.height()

        target = QRectF(self._initial_view_rect)
        target.translate(-source_dx, -source_dy)
        self._view_rect = self._clamp_view_rect(target)
        self._emit_view_changed()

    def _zoom_at(self, center: QPointF, factor: float) -> None:
        current = self._view_rect
        width = min(
            float(self._source_width),
            max(self.MIN_VIEW_SIZE, current.width() * factor),
        )
        height = min(
            float(self._source_height),
            max(self.MIN_VIEW_SIZE, current.height() * factor),
        )
        rel_x = (
            (center.x() - current.left()) / current.width()
            if current.width() > 0
            else 0.5
        )
        rel_y = (
            (center.y() - current.top()) / current.height()
            if current.height() > 0
            else 0.5
        )
        self._view_rect = self._clamp_view_rect(
            QRectF(
                center.x() - rel_x * width,
                center.y() - rel_y * height,
                width,
                height,
            )
        )
        self._emit_view_changed()

    def _emit_view_changed(self) -> None:
        self.view_changed.emit(self.zoom_percent)
        self.update()

    def _clamp_view_rect(self, rect: QRectF) -> QRectF:
        width = min(
            max(self.MIN_VIEW_SIZE, rect.width()),
            float(self._source_width),
        )
        height = min(
            max(self.MIN_VIEW_SIZE, rect.height()),
            float(self._source_height),
        )
        left = min(
            max(0.0, rect.left()),
            float(self._source_width) - width,
        )
        top = min(
            max(0.0, rect.top()),
            float(self._source_height) - height,
        )
        return QRectF(left, top, width, height)

    def _paint_shade(
        self,
        painter: QPainter,
        media: QRectF,
        selection: QRectF,
        shade: QColor,
    ) -> None:
        painter.fillRect(
            QRectF(
                media.left(),
                media.top(),
                media.width(),
                max(0.0, selection.top() - media.top()),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                media.left(),
                selection.bottom(),
                media.width(),
                max(0.0, media.bottom() - selection.bottom()),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                media.left(),
                selection.top(),
                max(0.0, selection.left() - media.left()),
                selection.height(),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                selection.right(),
                selection.top(),
                max(0.0, media.right() - selection.right()),
                selection.height(),
            ),
            shade,
        )

    def _media_rect(self) -> QRectF:
        available = QRectF(self.rect()).adjusted(8.0, 8.0, -8.0, -8.0)
        scale = min(
            available.width() / self._view_rect.width(),
            available.height() / self._view_rect.height(),
        )
        width = self._view_rect.width() * scale
        height = self._view_rect.height() * scale
        return QRectF(
            available.center().x() - width / 2,
            available.center().y() - height / 2,
            width,
            height,
        )

    def _source_to_display_rect(self, rect: QRectF) -> QRectF:
        media = self._media_rect()
        sx = media.width() / self._view_rect.width()
        sy = media.height() / self._view_rect.height()
        return QRectF(
            media.left() + (rect.left() - self._view_rect.left()) * sx,
            media.top() + (rect.top() - self._view_rect.top()) * sy,
            rect.width() * sx,
            rect.height() * sy,
        )

    def _display_to_source(
        self,
        point: QPointF,
        clamp: bool = False,
    ) -> QPointF | None:
        media = self._media_rect()
        if not media.contains(point) and not clamp:
            return None

        x = (
            self._view_rect.left()
            + (point.x() - media.left())
            * self._view_rect.width()
            / media.width()
        )
        y = (
            self._view_rect.top()
            + (point.y() - media.top())
            * self._view_rect.height()
            / media.height()
        )
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

    def _hit_handle(self, point: QPointF, rect: QRectF) -> str | None:
        for name, handle in self._handle_rects(rect).items():
            if handle.contains(point):
                return name
        return None

    def _update_cursor(self, point: QPointF) -> None:
        selection = self._source_to_display_rect(self._selection)
        handle = self._hit_handle(point, selection)
        if handle in ("top_left", "bottom_right"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in ("top_right", "bottom_left"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif selection.contains(point):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _move_selection(self, point: QPointF) -> None:
        rect = QRectF(self._initial_selection)
        rect.translate(point - self._press_source)
        if rect.left() < 0:
            rect.moveLeft(0)
        if rect.top() < 0:
            rect.moveTop(0)
        if rect.right() > self._source_width:
            rect.moveRight(self._source_width)
        if rect.bottom() > self._source_height:
            rect.moveBottom(self._source_height)
        self._selection = rect

    def _resize_from_handle(self, handle: str, point: QPointF) -> None:
        rect = self._initial_selection
        anchors = {
            "top_left": rect.bottomRight(),
            "top_right": rect.bottomLeft(),
            "bottom_left": rect.topRight(),
            "bottom_right": rect.topLeft(),
        }
        self._selection = self._rect_from_anchor(anchors[handle], point)

    def _rect_from_anchor(self, anchor: QPointF, point: QPointF) -> QRectF:
        dx = point.x() - anchor.x()
        dy = point.y() - anchor.y()
        sx = 1.0 if dx >= 0 else -1.0
        sy = 1.0 if dy >= 0 else -1.0
        width = max(self.MIN_SELECTION_PX, abs(dx))
        height = max(self.MIN_SELECTION_PX, abs(dy))

        if self._aspect_ratio is not None:
            if width / height > self._aspect_ratio:
                height = width / self._aspect_ratio
            else:
                width = height * self._aspect_ratio

        max_width = (
            self._source_width - anchor.x() if sx > 0 else anchor.x()
        )
        max_height = (
            self._source_height - anchor.y() if sy > 0 else anchor.y()
        )
        factor = min(
            1.0,
            max_width / width if width else 1.0,
            max_height / height if height else 1.0,
        )
        width *= factor
        height *= factor

        return QRectF(
            anchor,
            QPointF(anchor.x() + width * sx, anchor.y() + height * sy),
        ).normalized()


class CropDialog(QDialog):
    """실제 frame 위에서 crop 영역과 view를 직접 조절한다."""

    ASPECTS = [
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
        self.resize(980, 800)
        self.setMinimumSize(820, 680)

        self._source_width = source_width
        self._source_height = source_height
        self._syncing = False

        description = QLabel(
            "영역을 드래그하세요. Ctrl + 휠: 확대/축소 · "
            "가운데 휠 버튼 드래그: 화면 이동"
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescription")

        self.crop_preview = CropSelectionWidget(
            _capture_parent_preview(parent),
            source_width,
            source_height,
            self,
        )
        self.crop_preview.selection_changed.connect(
            self._sync_fields_from_preview
        )
        self.crop_preview.view_changed.connect(self._update_zoom_label)

        self.aspect_combo = QComboBox()
        for label, value in self.ASPECTS:
            self.aspect_combo.addItem(label, value)
        self.aspect_combo.currentIndexChanged.connect(self._apply_aspect)

        fit_button = QPushButton("선택 영역 맞춤")
        fit_button.setObjectName("secondaryButton")
        fit_button.clicked.connect(self.crop_preview.fit_selection)

        view_all_button = QPushButton("전체 보기")
        view_all_button.setObjectName("secondaryButton")
        view_all_button.clicked.connect(self.crop_preview.reset_view)

        center_button = QPushButton("가운데 80%")
        center_button.setObjectName("secondaryButton")
        center_button.clicked.connect(self._center_eighty)

        full_button = QPushButton("전체 프레임")
        full_button.setObjectName("secondaryButton")
        full_button.clicked.connect(self._full_frame)

        self.zoom_label = QLabel("Zoom 100%")
        self.zoom_label.setObjectName("selectionInfo")

        top = QHBoxLayout()
        top.addWidget(QLabel("Aspect"))
        top.addWidget(self.aspect_combo)
        top.addWidget(self.zoom_label)
        top.addStretch()
        top.addWidget(fit_button)
        top.addWidget(view_all_button)
        top.addWidget(center_button)
        top.addWidget(full_button)

        self.info = QLabel()
        self.info.setObjectName("selectionInfo")
        self.x_spin = self._spin(0, source_width - 1, 0)
        self.y_spin = self._spin(0, source_height - 1, 0)
        self.width_spin = self._spin(1, source_width, source_width)
        self.height_spin = self._spin(1, source_height, source_height)
        for spin in (
            self.x_spin,
            self.y_spin,
            self.width_spin,
            self.height_spin,
        ):
            spin.valueChanged.connect(self._sync_preview_from_fields)

        fields = QFormLayout()
        fields.addRow("X", self.x_spin)
        fields.addRow("Y", self.y_spin)
        fields.addRow("Width", self.width_spin)
        fields.addRow("Height", self.height_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(description)
        layout.addLayout(top)
        layout.addWidget(self.crop_preview, stretch=1)
        layout.addWidget(self.info)
        layout.addLayout(fields)
        layout.addWidget(buttons)

        self._sync_fields_from_preview(self.crop_preview.source_rect)

    @property
    def crop_rect(self) -> tuple[int, int, int, int]:
        return self.crop_preview.source_rect

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(" px")
        return spin

    def _sync_fields_from_preview(self, rect) -> None:
        if self._syncing:
            return
        x, y, width, height = rect
        self._syncing = True
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self._syncing = False

        area = width * height * 100 / (
            self._source_width * self._source_height
        )
        self.info.setText(
            f"선택 영역 {width} × {height} px · "
            f"위치 ({x}, {y}) · 원본의 {area:.1f}%"
        )

    def _sync_preview_from_fields(self) -> None:
        if self._syncing:
            return
        self.crop_preview.set_source_rect(
            (
                self.x_spin.value(),
                self.y_spin.value(),
                self.width_spin.value(),
                self.height_spin.value(),
            )
        )

    def _apply_aspect(self) -> None:
        value = self.aspect_combo.currentData()
        if value == "source":
            value = self._source_width / self._source_height
        self.crop_preview.set_aspect_ratio(value)

    def _center_eighty(self) -> None:
        width = round(self._source_width * 0.8)
        height = round(self._source_height * 0.8)
        self.crop_preview.set_source_rect(
            (
                (self._source_width - width) // 2,
                (self._source_height - height) // 2,
                width,
                height,
            )
        )
        self.crop_preview.fit_selection()

    def _full_frame(self) -> None:
        self.aspect_combo.setCurrentIndex(0)
        self.crop_preview.reset_full_frame()
        self.crop_preview.reset_view()

    def _update_zoom_label(self, zoom: float) -> None:
        self.zoom_label.setText(f"Zoom {zoom:.0f}%")

    def _validate_and_accept(self) -> None:
        x, y, width, height = self.crop_rect
        if (
            x + width > self._source_width
            or y + height > self._source_height
        ):
            QMessageBox.warning(
                self,
                "Crop",
                "Crop 영역이 원본 frame을 벗어났습니다.",
            )
            return
        self.accept()


class ResizeDialog(QDialog):
    """실제 frame을 보면서 출력 해상도를 지정한다."""

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
        self.resize(760, 650)

        self._source_width = source_width
        self._source_height = source_height
        self._source_image = _capture_parent_preview(parent)
        self._syncing = False

        self.preview = ImagePreviewLabel(self._source_image)
        self.preset_combo = QComboBox()
        for name, _ in self.PRESETS:
            self.preset_combo.addItem(name)

        self.width_spin = self._size_spin(source_width)
        self.height_spin = self._size_spin(source_height)
        self.keep_ratio = QCheckBox("가로세로 비율 유지")
        self.keep_ratio.setChecked(True)
        self.result_label = QLabel()
        self.result_label.setObjectName("selectionInfo")

        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        self.keep_ratio.toggled.connect(self._apply_preset)
        self.width_spin.valueChanged.connect(self._width_changed)
        self.height_spin.valueChanged.connect(self._height_changed)

        form = QFormLayout()
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
        layout.addWidget(QLabel("현재 frame을 보면서 출력 크기를 조절하세요."))
        layout.addWidget(self.preview, stretch=1)
        layout.addWidget(self.result_label)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._refresh_preview()

    @property
    def output_size(self) -> tuple[int, int]:
        return self.width_spin.value(), self.height_spin.value()

    def _size_spin(self, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, 16384)
        spin.setValue(value)
        spin.setSuffix(" px")
        return spin

    def _apply_preset(self) -> None:
        index = self.preset_combo.currentIndex()
        _, size = self.PRESETS[index]
        if index == 0:
            size = (self._source_width, self._source_height)
        if size is None:
            self._refresh_preview()
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
        self._refresh_preview()

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
        self._refresh_preview()

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
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        width, height = self.output_size
        if not self._source_image.isNull():
            self.preview.set_preview_image(
                self._source_image.scaled(
                    width,
                    height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        percent = width * 100 / self._source_width
        self.result_label.setText(
            f"출력 {width} × {height} px · "
            f"가로 기준 원본의 {percent:.0f}%"
        )


class RotateDialog(QDialog):
    """실제 frame을 보면서 회전 방향을 선택한다."""

    OPTIONS = [
        ("↻ 90°", 90),
        ("↕ 180°", 180),
        ("↺ 90°", 270),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rotate")
        self.setModal(True)
        self.resize(720, 600)

        self._source_image = _capture_parent_preview(parent)
        self.preview = ImagePreviewLabel(self._source_image)
        self.group = QButtonGroup(self)

        choices = QHBoxLayout()
        for index, (text, degrees) in enumerate(self.OPTIONS):
            radio = QRadioButton(text)
            radio.setProperty("degrees", degrees)
            radio.toggled.connect(self._refresh_preview)
            self.group.addButton(radio)
            choices.addWidget(radio)
            if index == 0:
                radio.setChecked(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("회전 결과를 확인한 뒤 적용하세요."))
        layout.addWidget(self.preview, stretch=1)
        layout.addLayout(choices)
        layout.addWidget(buttons)
        self._refresh_preview()

    @property
    def degrees(self) -> int:
        button = self.group.checkedButton()
        return int(button.property("degrees"))

    def _refresh_preview(self) -> None:
        if (
            self._source_image.isNull()
            or self.group.checkedButton() is None
        ):
            return

        self.preview.set_preview_image(
            self._source_image.transformed(
                QTransform().rotate(self.degrees),
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class UpscaleDialog(QDialog):
    """현재 frame과 예상 출력 해상도를 함께 보여준다."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Upscale")
        self.setModal(True)
        self.resize(720, 600)

        source_image = _capture_parent_preview(parent)
        media_size = getattr(parent, "_current_media_size", lambda: None)()

        if media_size is None:
            self._source_width = source_image.width()
            self._source_height = source_image.height()
        else:
            self._source_width, self._source_height = media_size

        self.preview = ImagePreviewLabel(source_image)
        self.group = QButtonGroup(self)

        options = QHBoxLayout()
        for index, (label, scale) in enumerate(
            (
                ("2× · 일반적인 확대", 2),
                ("4× · 큰 출력", 4),
            )
        ):
            radio = QRadioButton(label)
            radio.setProperty("scale", scale)
            radio.toggled.connect(self._update_info)
            self.group.addButton(radio)
            options.addWidget(radio)
            if index == 0:
                radio.setChecked(True)

        self.info = QLabel()
        self.info.setObjectName("selectionInfo")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "현재 frame을 기준으로 확인합니다. "
                "Standard Upscale은 Lanczos로 확대합니다."
            )
        )
        layout.addWidget(self.preview, stretch=1)
        layout.addLayout(options)
        layout.addWidget(self.info)
        layout.addWidget(buttons)
        self._update_info()

    @property
    def scale(self) -> int:
        return int(self.group.checkedButton().property("scale"))

    def _update_info(self) -> None:
        if self.group.checkedButton() is None:
            return
        scale = self.scale
        self.info.setText(
            f"예상 출력 {self._source_width * scale} × "
            f"{self._source_height * scale} px"
        )
