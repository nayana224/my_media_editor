from PySide6.QtWidgets import QDialog

from media_editor.live_edit_dialogs import (
    LiveCropDialog,
    LiveResizeDialog,
    LiveRotateDialog,
    LiveTrimDialog,
    LiveUpscaleDialog,
)
from media_editor.media import MediaKind


class LiveDialogMixin:
    """모든 편집 dialog를 동일한 누적 live preview 규칙으로 연다."""

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
        dialog = LiveTrimDialog(duration_ms, self.player.position(), self)
        state = self._current_edits()
        if state is not None and state.trim is not None:
            dialog.start_slider.setValue(state.trim[0])
            dialog.end_slider.setValue(state.trim[1])

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        state = self._current_edits()
        if state is not None:
            state.trim = (dialog.start_ms, dialog.end_ms)
        self._update_edit_status()
        self._update_media_tools()

    def _request_crop(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        self.player.pause()
        media_size = self._source_media_size()
        if media_size is None:
            self._show_error(
                "미디어 해상도를 아직 읽지 못했습니다. 잠시 후 다시 시도해 주세요."
            )
            return

        dialog = LiveCropDialog(*media_size, self)
        state = self._current_edits()
        if state is not None and state.crop is not None:
            dialog.crop_preview.set_source_rect(state.crop)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        state = self._current_edits()
        if state is not None:
            dialog_crop = dialog.crop_rect
            full_crop = (0, 0, media_size[0], media_size[1])
            state.crop = None if dialog_crop == full_crop else dialog_crop
        self._update_edit_status()
        self._update_media_tools()

    def _request_resize(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        self.player.pause()
        media_size = self._size_before_resize()
        if media_size is None:
            self._show_error(
                "미디어 해상도를 아직 읽지 못했습니다. 잠시 후 다시 시도해 주세요."
            )
            return

        dialog = LiveResizeDialog(*media_size, self)
        state = self._current_edits()
        if state is not None and state.resize is not None:
            dialog.width_spin.setValue(state.resize[0])
            dialog.height_spin.setValue(state.resize[1])

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        state = self._current_edits()
        if state is not None:
            state.resize = (
                None if dialog.output_size == media_size else dialog.output_size
            )
        self._update_edit_status()
        self._update_media_tools()

    def _request_rotate(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        self.player.pause()
        state = self._current_edits()
        initial = 0 if state is None or state.rotation is None else state.rotation
        dialog = LiveRotateDialog(initial, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        state = self._current_edits()
        if state is not None:
            state.rotation = None if dialog.degrees == 0 else dialog.degrees
        self._update_edit_status()
        self._update_media_tools()

    def _request_upscale(self) -> None:
        if self.current_asset is None or self._ffmpeg_process is not None:
            return

        self.player.pause()
        state = self._current_edits()
        initial = None if state is None else state.upscale
        dialog = LiveUpscaleDialog(initial, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        state = self._current_edits()
        if state is not None:
            state.upscale = dialog.scale
        self._update_edit_status()
        self._update_media_tools()
