from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap
from PySide6.QtMultimedia import QVideoFrame, QVideoSink
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from media_editor.edit_state import EditState
from media_editor.preview_transform import apply_preview_edits


class EditedVideoWidget(QLabel):
    """QVideoSink frame에 pending edit을 적용해 표시한다."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("imagePreview")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)

        self._video_sink = QVideoSink(self)
        self._video_sink.videoFrameChanged.connect(self._on_video_frame_changed)
        self._edit_provider: Callable[[], EditState | None] | None = None
        self._source_image = QImage()
        self._preview_image = QImage()

    def videoSink(self) -> QVideoSink:
        return self._video_sink

    def set_edit_provider(
        self,
        provider: Callable[[], EditState | None],
    ) -> None:
        self._edit_provider = provider

    def source_image(self) -> QImage:
        return self._source_image.copy()

    def preview_image(self) -> QImage:
        return self._preview_image.copy()

    def refresh_edits(self) -> None:
        if self._source_image.isNull():
            return

        edits = self._edit_provider() if self._edit_provider is not None else None
        self._preview_image = apply_preview_edits(self._source_image, edits)
        self._update_pixmap()

    def clear_frame(self) -> None:
        self._source_image = QImage()
        self._preview_image = QImage()
        self.clear()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_pixmap()

    def _on_video_frame_changed(self, frame: QVideoFrame) -> None:
        if not frame.isValid():
            return

        image = frame.toImage()
        if image.isNull():
            return

        self._source_image = image.copy()
        self.refresh_edits()

    def _update_pixmap(self) -> None:
        if self._preview_image.isNull():
            return

        self.setPixmap(
            QPixmap.fromImage(self._preview_image).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class DropPreviewWidget(QFrame):
    """파일 drop과 image/video preview를 담당한다."""

    files_dropped = Signal(object)
    open_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewCard")
        self.setAcceptDrops(True)

        self.stack = QStackedWidget(self)
        self.empty_page = self._create_empty_page()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setObjectName("imagePreview")
        self.image_label.setMinimumSize(320, 240)
        self.video_page = QWidget()

        self.stack.addWidget(self.empty_page)
        self.stack.addWidget(self.image_label)
        self.stack.addWidget(self.video_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self._image = QImage()

    def _create_empty_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        icon_label = QLabel("＋")
        icon_label.setObjectName("dropIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("미디어 파일을 여기에 놓으세요")
        title_label.setObjectName("dropTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description_label = QLabel(
            "여러 PNG · JPG · JPEG · WebM · MP4 파일을 지원합니다"
        )
        description_label.setObjectName("dropDescription")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        open_button = QPushButton("파일 열기")
        open_button.setObjectName("secondaryButton")
        open_button.clicked.connect(self.open_requested)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(6)
        layout.addWidget(open_button, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def set_image(self, path: Path) -> None:
        image = QImage(str(path))
        if image.isNull():
            raise ValueError(f"이미지를 불러올 수 없습니다: {path}")
        self.set_image_data(image)

    def set_image_data(self, image: QImage) -> None:
        self._image = image.copy()
        self.stack.setCurrentWidget(self.image_label)
        self._update_scaled_image()

    def set_video_widget(self, video_widget: QWidget) -> None:
        layout = self.video_page.layout()
        if layout is None:
            layout = QVBoxLayout(self.video_page)
            layout.setContentsMargins(0, 0, 0, 0)

        if layout.indexOf(video_widget) < 0:
            layout.addWidget(video_widget)

        self.stack.setCurrentWidget(self.video_page)

    def show_empty(self) -> None:
        self._image = QImage()
        self.image_label.clear()
        self.stack.setCurrentWidget(self.empty_page)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_scaled_image()

    def _update_scaled_image(self) -> None:
        if self._image.isNull():
            return

        self.image_label.setPixmap(
            QPixmap.fromImage(self._image).scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if not paths:
            event.ignore()
            return

        self.files_dropped.emit(paths)
        event.acceptProposedAction()
