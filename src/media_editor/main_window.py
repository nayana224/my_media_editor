from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from media_editor.media import MediaKind, classify_media, format_duration
from media_editor.widgets import DropPreviewWidget


class MainWindow(QMainWindow):
    """이미지와 영상을 preview하는 Media Editor 주 창."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Editor")
        self.resize(1100, 760)
        self.setMinimumSize(820, 620)

        self.current_path: Path | None = None
        self.current_kind: MediaKind | None = None
        self._slider_is_pressed = False

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self._build_ui()
        self._connect_player()
        self._update_playback_controls(False)

    def _build_ui(self) -> None:
        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        self.addAction(open_action)

        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        header_layout = QHBoxLayout()

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Media Editor")
        title.setObjectName("appTitle")
        subtitle = QLabel("빠르게 열고, 확인하고, 편집할 수 있는 데스크톱 미디어 도구")
        subtitle.setObjectName("appSubtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        open_button = QPushButton("Open Media")
        open_button.setObjectName("primaryButton")
        open_button.clicked.connect(self._open_file_dialog)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(open_button)

        main_layout.addLayout(header_layout)

        self.preview = DropPreviewWidget()
        self.preview.file_dropped.connect(self._load_media)
        self.preview.open_requested.connect(self._open_file_dialog)
        self.preview.set_video_widget(self.video_widget)
        main_layout.addWidget(self.preview, stretch=1)

        self.file_info = QLabel("파일을 열거나 preview 영역에 드래그 앤 드롭하세요.")
        self.file_info.setObjectName("fileInfo")
        self.file_info.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        main_layout.addWidget(self.file_info)

        playback_card = QFrame()
        playback_card.setObjectName("controlCard")
        playback_layout = QVBoxLayout(playback_card)
        playback_layout.setContentsMargins(18, 14, 18, 14)
        playback_layout.setSpacing(10)

        timeline_layout = QHBoxLayout()
        self.current_time = QLabel("00:00")
        self.current_time.setObjectName("timeLabel")
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 0)
        self.duration_time = QLabel("00:00")
        self.duration_time.setObjectName("timeLabel")

        timeline_layout.addWidget(self.current_time)
        timeline_layout.addWidget(self.timeline, stretch=1)
        timeline_layout.addWidget(self.duration_time)

        controls_layout = QHBoxLayout()

        self.play_button = QPushButton("▶  Play")
        self.play_button.setObjectName("primaryButton")
        self.play_button.clicked.connect(self._toggle_playback)

        self.trim_button = QPushButton("Trim")
        self.crop_button = QPushButton("Crop")
        self.rotate_button = QPushButton("Rotate")
        self.resize_button = QPushButton("Resize")
        self.export_button = QPushButton("Export")

        for button in (
            self.trim_button,
            self.crop_button,
            self.rotate_button,
            self.resize_button,
            self.export_button,
        ):
            button.setObjectName("toolButton")
            button.setEnabled(False)
            button.setToolTip("다음 단계에서 구현할 편집 기능입니다.")

        controls_layout.addWidget(self.play_button)
        controls_layout.addSpacing(8)
        controls_layout.addWidget(self.trim_button)
        controls_layout.addWidget(self.crop_button)
        controls_layout.addWidget(self.rotate_button)
        controls_layout.addWidget(self.resize_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.export_button)

        playback_layout.addLayout(timeline_layout)
        playback_layout.addLayout(controls_layout)
        main_layout.addWidget(playback_card)

        self.timeline.sliderPressed.connect(self._on_slider_pressed)
        self.timeline.sliderReleased.connect(self._on_slider_released)
        self.timeline.sliderMoved.connect(self._on_slider_moved)

    def _connect_player(self) -> None:
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(
            self._on_playback_state_changed
        )
        self.player.errorOccurred.connect(self._on_player_error)

    def _open_file_dialog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Media",
            "",
            (
                "Supported Media (*.png *.jpg *.jpeg *.webm *.mp4);;"
                "Images (*.png *.jpg *.jpeg);;"
                "Videos (*.webm *.mp4)"
            ),
        )
        if filename:
            self._load_media(Path(filename))

    def _load_media(self, path: Path) -> None:
        if not path.is_file():
            self._show_error(f"파일을 찾을 수 없습니다.\n\n{path}")
            return

        try:
            kind = classify_media(path)
        except ValueError as exc:
            self._show_error(str(exc))
            return

        self.player.stop()
        self.current_path = path
        self.current_kind = kind
        self.file_info.setText(str(path))

        if kind is MediaKind.IMAGE:
            self.player.setSource(QUrl())
            try:
                self.preview.set_image(path)
            except ValueError as exc:
                self._show_error(str(exc))
                return
            self._update_playback_controls(False)
            return

        self.preview.set_video_widget(self.video_widget)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self._update_playback_controls(True)

    def _update_playback_controls(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.timeline.setEnabled(enabled)

        if not enabled:
            self.timeline.setRange(0, 0)
            self.current_time.setText("00:00")
            self.duration_time.setText("00:00")
            self.play_button.setText("▶  Play")

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return

        self.player.play()

    def _on_playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("Ⅱ  Pause")
        else:
            self.play_button.setText("▶  Play")

    def _on_duration_changed(self, duration: int) -> None:
        self.timeline.setRange(0, max(0, duration))
        self.duration_time.setText(format_duration(duration))

    def _on_position_changed(self, position: int) -> None:
        if not self._slider_is_pressed:
            self.timeline.setValue(position)
        self.current_time.setText(format_duration(position))

    def _on_slider_pressed(self) -> None:
        self._slider_is_pressed = True

    def _on_slider_released(self) -> None:
        self._slider_is_pressed = False
        self.player.setPosition(self.timeline.value())

    def _on_slider_moved(self, position: int) -> None:
        self.current_time.setText(format_duration(position))

    def _on_player_error(
        self,
        error: QMediaPlayer.Error,
        error_string: str,
    ) -> None:
        if error == QMediaPlayer.Error.NoError:
            return

        message = error_string or "영상 재생 중 알 수 없는 오류가 발생했습니다."
        self._show_error(message)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Media Editor", message)
