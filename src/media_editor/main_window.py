from pathlib import Path

from PySide6.QtCore import QProcess, QUrl, Qt
from PySide6.QtGui import QAction, QImage
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
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

from media_editor.edit_state import EditState
from media_editor.ffmpeg import build_save_command, make_save_output_path
from media_editor.media import MediaKind, format_duration
from media_editor.project import MediaAsset, MediaProject
from media_editor.transform_dialogs import (
    CropDialog,
    ResizeDialog,
    RotateDialog,
    UpscaleDialog,
)
from media_editor.trim_dialog import TrimDialog
from media_editor.widgets import DropPreviewWidget


ASSET_ROLE = Qt.ItemDataRole.UserRole


class MainWindow(QMainWindow):
    """Media library와 비파괴 편집 상태를 제공하는 주 창."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Editor")
        self.resize(1180, 800)
        self.setMinimumSize(900, 660)

        self.project = MediaProject()
        self.current_asset: MediaAsset | None = None
        self._edit_states: dict[Path, EditState] = {}

        self._slider_is_pressed = False
        self._ffmpeg_process: QProcess | None = None
        self._ffmpeg_output_path: Path | None = None
        self._ffmpeg_action = ""
        self._ffmpeg_source_path: Path | None = None

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self._build_ui()
        self._connect_player()
        self._update_playback_controls(False)
        self._update_edit_status()
        self._update_media_tools()

    def _build_ui(self) -> None:
        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        self.addAction(open_action)

        remove_action = QAction("Remove Media", self)
        remove_action.setShortcut("Delete")
        remove_action.triggered.connect(self._remove_selected_media)
        self.addAction(remove_action)

        save_action = QAction("Save As", self)
        save_action.setShortcut("Ctrl+Shift+S")
        save_action.triggered.connect(self._request_save)
        self.addAction(save_action)

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
        subtitle = QLabel("편집 내용을 누적한 뒤 Save 시 한 번에 렌더링합니다")
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
        library_layout.setSpacing(10)

        library_header = QHBoxLayout()
        library_title = QLabel("MEDIA")
        library_title.setObjectName("sectionTitle")
        self.add_media_button = QPushButton("+ Add")
        self.add_media_button.setObjectName("secondaryButton")
        self.add_media_button.clicked.connect(self._open_file_dialog)
        self.remove_media_button = QPushButton("− Remove")
        self.remove_media_button.setObjectName("secondaryButton")
        self.remove_media_button.clicked.connect(self._remove_selected_media)

        library_header.addWidget(library_title)
        library_header.addStretch()
        library_header.addWidget(self.add_media_button)
        library_header.addWidget(self.remove_media_button)

        self.media_list = QListWidget()
        self.media_list.setObjectName("mediaList")
        self.media_list.currentItemChanged.connect(
            self._on_library_selection_changed
        )

        library_layout.addLayout(library_header)
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
        splitter.setSizes([250, 830])

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

        edit_status_layout = QHBoxLayout()
        self.edit_status = QLabel("Pending edits: 없음")
        self.edit_status.setObjectName("selectionInfo")
        self.reset_edits_button = QPushButton("Reset edits")
        self.reset_edits_button.setObjectName("secondaryButton")
        self.reset_edits_button.clicked.connect(self._reset_current_edits)

        edit_status_layout.addWidget(self.edit_status, stretch=1)
        edit_status_layout.addWidget(self.reset_edits_button)

        controls_layout = QHBoxLayout()
        self.play_button = QPushButton("▶  Play")
        self.play_button.setObjectName("primaryButton")
        self.play_button.clicked.connect(self._toggle_playback)

        self.trim_button = QPushButton("Trim")
        self.crop_button = QPushButton("Crop")
        self.resize_button = QPushButton("Resize")
        self.rotate_button = QPushButton("Rotate")
        self.upscale_button = QPushButton("Upscale")
        self.save_button = QPushButton("Save As…")

        for button in (
            self.trim_button,
            self.crop_button,
            self.resize_button,
            self.rotate_button,
            self.upscale_button,
        ):
            button.setObjectName("toolButton")
        self.save_button.setObjectName("primaryButton")

        self.trim_button.clicked.connect(self._request_trim)
        self.crop_button.clicked.connect(self._request_crop)
        self.resize_button.clicked.connect(self._request_resize)
        self.rotate_button.clicked.connect(self._request_rotate)
        self.upscale_button.clicked.connect(self._request_upscale)
        self.save_button.clicked.connect(self._request_save)

        controls_layout.addWidget(self.play_button)
        controls_layout.addSpacing(8)
        controls_layout.addWidget(self.trim_button)
        controls_layout.addWidget(self.crop_button)
        controls_layout.addWidget(self.resize_button)
        controls_layout.addWidget(self.rotate_button)
        controls_layout.addWidget(self.upscale_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.save_button)

        playback_layout.addLayout(timeline_layout)
        playback_layout.addLayout(edit_status_layout)
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

        self._update_media_tools()
        if errors:
            self._show_error("\n".join(errors))

    def _remove_selected_media(self) -> None:
        if self._ffmpeg_process is not None:
            return

        row = self.media_list.currentRow()
        if row < 0:
            return

        item = self.media_list.item(row)
        asset = item.data(ASSET_ROLE)
        if not isinstance(asset, MediaAsset):
            return

        self.player.stop()
        self.project.remove(asset)
        self._edit_states.pop(asset.path.resolve(), None)
        self.media_list.takeItem(row)

        if self.media_list.count() == 0:
            self.current_asset = None
            self.player.setSource(QUrl())
            self.preview.show_empty()
            self.file_info.setText(
                "파일을 import하거나 preview 영역에 드래그 앤 드롭하세요."
            )
            self._update_playback_controls(False)
            self._update_edit_status()
            self._update_media_tools()
            return

        self.media_list.setCurrentRow(min(row, self.media_list.count() - 1))

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
        self._update_edit_status()
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

    def _current_edits(self) -> EditState | None:
        if self.current_asset is None:
            return None

        key = self.current_asset.path.resolve()
        state = self._edit_states.get(key)
        if state is None:
            state = EditState()
            self._edit_states[key] = state
        return state

    def _source_media_size(self) -> tuple[int, int] | None:
        if self.current_asset is None:
            return None

        if self.current_asset.kind is MediaKind.IMAGE:
            image = QImage(str(self.current_asset.path))
            if image.isNull():
                return None
            return image.width(), image.height()

        size = self.video_widget.videoSink().videoSize()
        if not size.isValid() or size.width() <= 0 or size.height() <= 0:
            return None
        return size.width(), size.height()

    def _size_before_resize(self) -> tuple[int, int] | None:
        size = self._source_media_size()
        state = self._current_edits()
        if size is None or state is None:
            return size

        width, height = size
        if state.crop is not None:
            _, _, width, height = state.crop
        if state.rotation in (90, 270):
            width, height = height, width
        return width, height

    def _current_media_size(self) -> tuple[int, int] | None:
        """Upscale preview가 사용할 현재 pending 결과 크기를 계산한다."""
        size = self._size_before_resize()
        state = self._current_edits()
        if size is None or state is None:
            return size

        if state.resize is not None:
            return state.resize
        return size

    def _update_edit_status(self) -> None:
        state = self._current_edits()
        if state is None or not state.has_changes:
            self.edit_status.setText("Pending edits: 없음")
            self.reset_edits_button.setEnabled(False)
            return

        self.edit_status.setText("Pending edits: " + "  ·  ".join(state.labels()))
        self.reset_edits_button.setEnabled(self._ffmpeg_process is None)

    def _reset_current_edits(self) -> None:
        if self._ffmpeg_process is not None:
            return

        state = self._current_edits()
        if state is None or not state.has_changes:
            return

        answer = QMessageBox.question(
            self,
            "Reset edits",
            "현재 미디어에 설정한 편집 내용을 모두 초기화할까요?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        state.clear()
        self._update_edit_status()
        self._update_media_tools()

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

        self.add_media_button.setEnabled(not busy)
        self.remove_media_button.setEnabled(has_asset and not busy)
        self.crop_button.setEnabled(has_asset and not busy)
        self.resize_button.setEnabled(has_asset and not busy)
        self.rotate_button.setEnabled(has_asset and not busy)
        self.upscale_button.setEnabled(has_asset and not busy)
        self.trim_button.setEnabled(has_video and not busy)
        self.save_button.setEnabled(has_asset and not busy)

        state = self._current_edits()
        self.reset_edits_button.setEnabled(
            bool(state and state.has_changes and not busy)
        )

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
        dialog = TrimDialog(duration_ms, self.player.position(), self)
        state = self._current_edits()
        if state is not None and state.trim is not None:
            start_ms, end_ms = state.trim
            dialog.start_slider.setValue(start_ms)
            dialog.end_slider.setValue(end_ms)

        if not dialog.exec():
            return

        state = self._current_edits()
        if state is not None:
            state.trim = (dialog.start_ms, dialog.end_ms)
        self._update_edit_status()

    def _request_crop(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        media_size = self._source_media_size()
        if media_size is None:
            self._show_error(
                "미디어 해상도를 아직 읽지 못했습니다. 잠시 후 다시 시도해 주세요."
            )
            return

        dialog = CropDialog(*media_size, self)
        state = self._current_edits()
        if state is not None and state.crop is not None:
            dialog.crop_preview.set_source_rect(state.crop)

        if not dialog.exec():
            return

        state = self._current_edits()
        if state is not None:
            state.crop = dialog.crop_rect
        self._update_edit_status()

    def _request_resize(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        media_size = self._size_before_resize()
        if media_size is None:
            self._show_error(
                "미디어 해상도를 아직 읽지 못했습니다. 잠시 후 다시 시도해 주세요."
            )
            return

        dialog = ResizeDialog(*media_size, self)
        state = self._current_edits()
        if state is not None and state.resize is not None:
            width, height = state.resize
            dialog.width_spin.setValue(width)
            dialog.height_spin.setValue(height)

        if not dialog.exec():
            return

        state = self._current_edits()
        if state is not None:
            state.resize = dialog.output_size
        self._update_edit_status()

    def _request_rotate(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        dialog = RotateDialog(self)
        state = self._current_edits()
        if state is not None and state.rotation is not None:
            for button in dialog.group.buttons():
                if int(button.property("degrees")) == state.rotation:
                    button.setChecked(True)
                    break

        if not dialog.exec():
            return

        state = self._current_edits()
        if state is not None:
            state.rotation = dialog.degrees
        self._update_edit_status()

    def _request_upscale(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        dialog = UpscaleDialog(self)
        state = self._current_edits()
        if state is not None and state.upscale is not None:
            for button in dialog.group.buttons():
                if int(button.property("scale")) == state.upscale:
                    button.setChecked(True)
                    break

        if not dialog.exec():
            return

        state = self._current_edits()
        if state is not None:
            state.upscale = dialog.scale
        self._update_edit_status()

    def _request_save(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        state = self._current_edits()
        if state is None:
            return

        default_path = make_save_output_path(
            self.current_asset.path,
            self.current_asset.kind,
        )

        if self.current_asset.kind is MediaKind.VIDEO:
            file_filter = "MP4 Video (*.mp4)"
            suffix = ".mp4"
        else:
            file_filter = "PNG Image (*.png)"
            suffix = ".png"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Edited Media",
            str(default_path),
            file_filter,
        )
        if not filename:
            return

        output_path = Path(filename)
        if output_path.suffix.lower() != suffix:
            output_path = output_path.with_suffix(suffix)

        if output_path.resolve() == self.current_asset.path.resolve():
            self._show_error("원본 파일과 같은 경로로 저장할 수 없습니다.")
            return

        try:
            command = build_save_command(
                self.current_asset.path,
                output_path,
                self.current_asset.kind,
                state,
            )
        except (FileNotFoundError, ValueError) as exc:
            self._show_error(str(exc))
            return

        self._start_ffmpeg_job(
            command,
            output_path,
            "Save",
            self.current_asset.path,
        )

    def _start_ffmpeg_job(
        self,
        command: list[str],
        output_path: Path,
        action: str,
        source_path: Path | None = None,
    ) -> None:
        if self._ffmpeg_process is not None:
            return

        process = QProcess(self)
        process.finished.connect(self._on_ffmpeg_finished)
        process.errorOccurred.connect(self._on_ffmpeg_process_error)

        self._ffmpeg_process = process
        self._ffmpeg_output_path = output_path
        self._ffmpeg_action = action
        self._ffmpeg_source_path = source_path
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
        source_path = self._ffmpeg_source_path

        self._ffmpeg_process = None
        self._ffmpeg_output_path = None
        self._ffmpeg_action = ""
        self._ffmpeg_source_path = None

        if process is None or output_path is None:
            self._update_media_tools()
            return

        if exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            self._update_media_tools()
            stderr = bytes(process.readAllStandardError()).decode(
                errors="replace"
            ).strip()
            self._show_error(f"{action}에 실패했습니다.\n\n{stderr}")
            return

        if source_path is not None:
            self._edit_states.pop(source_path.resolve(), None)

        self._import_paths([output_path])
        self._select_asset_path(output_path)
        self.file_info.setText(f"{action} 완료: {output_path}")
        self._update_edit_status()
        self._update_media_tools()

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
        self._ffmpeg_source_path = None
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
