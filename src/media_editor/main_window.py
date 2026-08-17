from pathlib import Path

from PySide6.QtCore import QProcess, QUrl, Qt
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from media_editor.ffmpeg import (
    build_mp4_export_command,
    build_trim_command,
    build_upscale_command,
    make_mp4_output_path,
    make_trim_output_path,
    make_upscale_output_path,
)
from media_editor.media import MediaKind, format_duration
from media_editor.project import MediaAsset, MediaProject
from media_editor.trim_dialog import TrimDialog
from media_editor.widgets import DropPreviewWidget


ASSET_ROLE = Qt.ItemDataRole.UserRole


class MainWindow(QMainWindow):
    """Media library와 preview를 제공하는 Media Editor 주 창."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Editor")
        self.resize(1180, 780)
        self.setMinimumSize(900, 640)

        self.project = MediaProject()
        self.current_asset: MediaAsset | None = None
        self._slider_is_pressed = False
        self._ffmpeg_process: QProcess | None = None
        self._ffmpeg_output_path: Path | None = None
        self._ffmpeg_action = ""

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self._build_ui()
        self._connect_player()
        self._update_playback_controls(False)
        self._update_media_tools()

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
        subtitle = QLabel("이미지와 영상을 하나의 project에서 편집하고 변환합니다")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        open_button = QPushButton("Import Media")
        open_button.setObjectName("primaryButton")
        open_button.clicked.connect(self._open_file_dialog)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(open_button)
        main_layout.addLayout(header_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        library_card = QFrame()
        library_card.setObjectName("libraryCard")
        library_layout = QVBoxLayout(library_card)
        library_layout.setContentsMargins(14, 14, 14, 14)

        library_title = QLabel("MEDIA")
        library_title.setObjectName("sectionTitle")
        self.media_list = QListWidget()
        self.media_list.setObjectName("mediaList")
        self.media_list.currentItemChanged.connect(
            self._on_library_selection_changed
        )

        library_layout.addWidget(library_title)
        library_layout.addWidget(self.media_list)
        splitter.addWidget(library_card)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(10)

        self.preview = DropPreviewWidget()
        self.preview.files_dropped.connect(self._import_paths)
        self.preview.open_requested.connect(self._open_file_dialog)
        self.preview.set_video_widget(self.video_widget)

        self.file_info = QLabel(
            "파일을 import하거나 preview 영역에 드래그 앤 드롭하세요."
        )
        self.file_info.setObjectName("fileInfo")
        self.file_info.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        preview_layout.addWidget(self.preview, stretch=1)
        preview_layout.addWidget(self.file_info)
        splitter.addWidget(preview_container)
        splitter.setSizes([230, 850])

        main_layout.addWidget(splitter, stretch=1)

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
        self.resize_button = QPushButton("Resize")
        self.upscale_button = QPushButton("Upscale")
        self.export_button = QPushButton("Export MP4")

        self.trim_button.setObjectName("toolButton")
        self.trim_button.clicked.connect(self._request_trim)

        self.upscale_button.setObjectName("toolButton")
        self.upscale_button.clicked.connect(self._request_upscale)

        self.export_button.setObjectName("toolButton")
        self.export_button.clicked.connect(self._request_mp4_export)

        for button in (self.crop_button, self.resize_button):
            button.setObjectName("toolButton")
            button.setEnabled(False)
            button.setToolTip("다음 개발 단계에서 구현할 기능입니다.")

        controls_layout.addWidget(self.play_button)
        controls_layout.addSpacing(8)
        controls_layout.addWidget(self.trim_button)
        controls_layout.addWidget(self.crop_button)
        controls_layout.addWidget(self.resize_button)
        controls_layout.addWidget(self.upscale_button)
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
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Media",
            "",
            (
                "Supported Media (*.png *.jpg *.jpeg *.webm *.mp4);;"
                "Images (*.png *.jpg *.jpeg);;"
                "Videos (*.webm *.mp4)"
            ),
        )
        if filenames:
            self._import_paths([Path(filename) for filename in filenames])

    def _import_paths(self, paths: list[Path]) -> None:
        errors: list[str] = []

        for path in paths:
            if not path.is_file():
                errors.append(f"파일을 찾을 수 없습니다: {path}")
                continue

            try:
                added = self.project.add_paths([path])
            except ValueError as exc:
                errors.append(f"{path.name}: {exc}")
                continue

            for asset in added:
                item = QListWidgetItem(asset.path.name)
                item.setToolTip(str(asset.path))
                item.setData(ASSET_ROLE, asset)
                self.media_list.addItem(item)

        if self.media_list.currentItem() is None and self.media_list.count() > 0:
            self.media_list.setCurrentRow(0)

        if errors:
            self._show_error("\n".join(errors))

    def _select_asset_path(self, path: Path) -> None:
        resolved = path.resolve()
        for row in range(self.media_list.count()):
            item = self.media_list.item(row)
            asset = item.data(ASSET_ROLE)
            if isinstance(asset, MediaAsset) and asset.path.resolve() == resolved:
                self.media_list.setCurrentItem(item)
                return

    def _on_library_selection_changed(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        del previous
        if current is None:
            return

        asset = current.data(ASSET_ROLE)
        if isinstance(asset, MediaAsset):
            self._load_asset(asset)

    def _load_asset(self, asset: MediaAsset) -> None:
        self.player.stop()
        self.current_asset = asset
        self.file_info.setText(str(asset.path))
        self._update_media_tools()

        if asset.kind is MediaKind.IMAGE:
            self.player.setSource(QUrl())
            try:
                self.preview.set_image(asset.path)
            except ValueError as exc:
                self._show_error(str(exc))
                return
            self._update_playback_controls(False)
            return

        self.preview.set_video_widget(self.video_widget)
        self.player.setSource(QUrl.fromLocalFile(str(asset.path)))
        self._update_playback_controls(True)

    def _update_playback_controls(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.timeline.setEnabled(enabled)

        if not enabled:
            self.timeline.setRange(0, 0)
            self.current_time.setText("00:00")
            self.duration_time.setText("00:00")
            self.play_button.setText("▶  Play")

    def _update_media_tools(self) -> None:
        busy = self._ffmpeg_process is not None
        has_asset = self.current_asset is not None
        has_video = has_asset and self.current_asset.kind is MediaKind.VIDEO

        self.upscale_button.setEnabled(has_asset and not busy)
        self.trim_button.setEnabled(has_video and not busy)
        self.export_button.setEnabled(has_video and not busy)

    def _request_trim(self) -> None:
        if (
            self.current_asset is None
            or self.current_asset.kind is not MediaKind.VIDEO
            or self._ffmpeg_process is not None
        ):
            return

        duration_ms = self.player.duration()
        if duration_ms <= 0:
            self._show_error(
                "영상 길이를 아직 읽지 못했습니다. 잠시 후 다시 시도해 주세요."
            )
            return

        self.player.pause()
        dialog = TrimDialog(
            duration_ms,
            self.player.position(),
            self,
        )
        if not dialog.exec():
            return

        output_path = make_trim_output_path(self.current_asset.path)
        try:
            command = build_trim_command(
                self.current_asset.path,
                output_path,
                dialog.start_ms,
                dialog.end_ms,
            )
        except (FileNotFoundError, ValueError) as exc:
            self._show_error(str(exc))
            return

        self._start_ffmpeg_job(command, output_path, "Trim")

    def _request_upscale(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        choices = ["Standard 2×", "Standard 4×", "AI Upscale (준비 중)"]
        choice, accepted = QInputDialog.getItem(
            self,
            "Upscale",
            "Upscale mode",
            choices,
            0,
            False,
        )
        if not accepted:
            return

        if choice.startswith("AI"):
            QMessageBox.information(
                self,
                "AI Upscale",
                "AI Upscale은 다음 단계에서 Real-ESRGAN backend로 추가할 예정입니다.",
            )
            return

        scale = 2 if "2×" in choice else 4
        output_path = make_upscale_output_path(
            self.current_asset.path,
            self.current_asset.kind,
            scale,
        )

        try:
            command = build_upscale_command(
                self.current_asset.path,
                output_path,
                self.current_asset.kind,
                scale,
            )
        except (FileNotFoundError, ValueError) as exc:
            self._show_error(str(exc))
            return

        self._start_ffmpeg_job(command, output_path, "Upscale")

    def _request_mp4_export(self) -> None:
        if (
            self.current_asset is None
            or self.current_asset.kind is not MediaKind.VIDEO
            or self._ffmpeg_process is not None
        ):
            return

        default_path = make_mp4_output_path(self.current_asset.path)
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export MP4",
            str(default_path),
            "MP4 Video (*.mp4)",
        )
        if not filename:
            return

        output_path = Path(filename)
        if output_path.suffix.lower() != ".mp4":
            output_path = output_path.with_suffix(".mp4")

        if output_path.resolve() == self.current_asset.path.resolve():
            self._show_error("입력 영상과 같은 경로로 export할 수 없습니다.")
            return

        try:
            command = build_mp4_export_command(
                self.current_asset.path,
                output_path,
            )
        except FileNotFoundError as exc:
            self._show_error(str(exc))
            return

        self._start_ffmpeg_job(command, output_path, "MP4 Export")

    def _start_ffmpeg_job(
        self,
        command: list[str],
        output_path: Path,
        action: str,
    ) -> None:
        if self._ffmpeg_process is not None:
            return

        process = QProcess(self)
        process.finished.connect(self._on_ffmpeg_finished)
        process.errorOccurred.connect(self._on_ffmpeg_process_error)

        self._ffmpeg_process = process
        self._ffmpeg_output_path = output_path
        self._ffmpeg_action = action
        self._update_media_tools()
        self.file_info.setText(f"{action} 실행 중... → {output_path}")
        process.start(command[0], command[1:])

    def _on_ffmpeg_finished(
        self,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        process = self._ffmpeg_process
        output_path = self._ffmpeg_output_path
        action = self._ffmpeg_action

        self._ffmpeg_process = None
        self._ffmpeg_output_path = None
        self._ffmpeg_action = ""
        self._update_media_tools()

        if process is None or output_path is None:
            return

        if exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            stderr = bytes(process.readAllStandardError()).decode(
                errors="replace"
            ).strip()
            self._show_error(f"{action}에 실패했습니다.\n\n{stderr}")
            return

        self._import_paths([output_path])
        self._select_asset_path(output_path)
        self.file_info.setText(f"{action} 완료: {output_path}")
        QMessageBox.information(
            self,
            f"{action} 완료",
            f"파일을 만들었습니다.\n\n{output_path}",
        )

    def _on_ffmpeg_process_error(self, error: QProcess.ProcessError) -> None:
        if error != QProcess.ProcessError.FailedToStart:
            return

        action = self._ffmpeg_action or "FFmpeg 작업"
        self._ffmpeg_process = None
        self._ffmpeg_output_path = None
        self._ffmpeg_action = ""
        self._update_media_tools()
        self._show_error(
            f"{action}을 시작하지 못했습니다. ffmpeg 설치 상태를 확인해 주세요."
        )

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
