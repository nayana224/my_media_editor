from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class DropPreviewWidget(QFrame):
    """파일 drop과 이미지 preview를 담당한다."""

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

        self._image_pixmap: QPixmap | None = None

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

        description_label = QLabel("여러 PNG · JPG · JPEG · WebM · MP4 파일을 지원합니다")
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
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            raise ValueError(f"이미지를 불러올 수 없습니다: {path}")

        self._image_pixmap = pixmap
        self.stack.setCurrentWidget(self.image_label)
        self._update_scaled_image()

    def set_video_widget(self, video_widget: QWidget) -> None:
        layout = self.video_page.layout()
        if layout is None:
            layout = QVBoxLayout(self.video_page)
            layout.setContentsMargins(0, 0, 0, 0)

        if layout.indexOf(video_widget) < 0:
            layout.addWidget(video_widget)
            return

        self.stack.setCurrentWidget(self.video_page)

    def show_empty(self) -> None:
        self._image_pixmap = None
        self.stack.setCurrentWidget(self.empty_page)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_scaled_image()

    def _update_scaled_image(self) -> None:
        if self._image_pixmap is None:
            return

        size = self.image_label.size()
        scaled = self._image_pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

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
