import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QMouseEvent
from PySide6.QtWidgets import QApplication

from media_editor.app import PreviewReadyMainWindow
from media_editor.edit_state import EditState
from media_editor.ffmpeg import build_save_command
from media_editor.media import MediaKind
from media_editor.preview_transform import apply_preview_edits
from media_editor.sequence_export import VideoProbe
from media_editor.transform_dialogs import CropSelectionWidget


class CropRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def widget(self, display_width=640, source_width=640):
        w = CropSelectionWidget(QImage(display_width, 480, QImage.Format.Format_RGB32), source_width, 480)
        w.resize(800, 600)
        return w

    def test_initial_full_frame_edge_can_be_grabbed_from_outside_image(self):
        w = self.widget()
        media = w._media_rect()
        press = QPointF(media.right() + 3, media.top() + media.height() * .3)
        event = QMouseEvent(QEvent.Type.MouseButtonPress, press, press, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        w.mousePressEvent(event)
        self.assertEqual(w._drag_mode, "right")
        w._resize_from_handle(w._drag_mode, QPointF(500, 200))
        self.assertEqual(w.source_rect, (0, 0, 500, 480))

    def test_each_edge_only_changes_that_axis_and_keeps_opposite_edge(self):
        expectations = {
            "left": ((120, 80), (120, 50, 200, 200)),
            "right": ((280, 80), (100, 50, 180, 200)),
            "top": ((120, 80), (100, 80, 220, 170)),
            "bottom": ((120, 230), (100, 50, 220, 180)),
        }
        for handle, (point, expected) in expectations.items():
            with self.subTest(handle=handle):
                w = self.widget()
                w.set_source_rect((100, 50, 220, 200))
                w._initial_selection = QRectF(w._selection)
                w._resize_from_handle(handle, QPointF(*point))
                self.assertEqual(w.source_rect, expected)

    def test_corners_resize_from_the_first_drag_without_flipping(self):
        for handle, point, expected in [
            ("top_left", (120, 80), (120, 80, 200, 170)),
            ("top_right", (280, 80), (100, 80, 180, 170)),
            ("bottom_left", (120, 230), (120, 50, 200, 180)),
            ("bottom_right", (280, 230), (100, 50, 180, 180)),
        ]:
            with self.subTest(handle=handle):
                w = self.widget(); w.set_source_rect((100, 50, 220, 200))
                w._initial_selection = QRectF(w._selection)
                w._resize_from_handle(handle, QPointF(*point))
                self.assertEqual(w.source_rect, expected)
        w._resize_from_handle("bottom_right", QPointF(-10, -10))
        self.assertEqual(w.source_rect, (100, 50, 2, 2))

    def test_entire_border_is_draggable_and_has_directional_cursors(self):
        w = self.widget(); w.set_source_rect((100, 50, 220, 200))
        r = w._source_to_display_rect(w._selection)
        point = QPointF(r.left(), r.top() + r.height() * .25)
        self.assertEqual(w._hit_handle(point, r), "left")
        w._update_cursor(point)
        self.assertEqual(w.cursor().shape(), Qt.CursorShape.SizeHorCursor)

    def test_anamorphic_preview_keeps_display_aspect_but_uses_encoded_grid(self):
        w = self.widget(display_width=960, source_width=640)
        media = w._media_rect()
        self.assertAlmostEqual(media.width() / media.height(), 2)
        point = w._display_to_source(QPointF(media.center().x(), media.center().y()))
        self.assertAlmostEqual(point.x(), 320)
        self.assertAlmostEqual(point.y(), 240)
        w.set_aspect_ratio(1.0)
        rect = w._source_to_display_rect(w._selection)
        self.assertAlmostEqual(rect.width() / rect.height(), 1)

    def test_preview_crop_maps_encoded_coordinates_to_display_pixels(self):
        image = QImage(960, 480, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.red)
        # Encoded right half maps to the display image's right half.
        result = apply_preview_edits(image, EditState(crop=(320, 0, 320, 480)), source_size=(640, 480))
        self.assertEqual((result.width(), result.height()), (480, 480))

    def test_video_size_comes_from_probe_not_expanded_display_frame(self):
        fake = SimpleNamespace(current_asset=SimpleNamespace(kind=MediaKind.VIDEO), _video_source_size=(1920, 1080))
        self.assertEqual(PreviewReadyMainWindow._source_media_size(fake), (1920, 1080))
        self.assertEqual(VideoProbe(1920, 1080, 1, False, rotation=90).editing_size, (1080, 1920))

    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="ffmpeg")
    def test_save_rejects_screenshot_crop_before_starting_ffmpeg(self, _):
        with self.assertRaisesRegex(ValueError, "Crop"):
            build_save_command(Path("in.mp4"), Path("out.mp4"), MediaKind.VIDEO,
                               EditState(crop=(0, 0, 2536, 1058)), source_size=(1920, 1080))


class ProbeSizeRegressionTest(unittest.TestCase):
    @patch("media_editor.sequence_export.find_ffprobe", return_value="ffprobe")
    @patch("media_editor.sequence_export.subprocess.run")
    def test_size_probe_accepts_webm_without_duration_but_sequence_rejects_it(self, run, _):
        from media_editor.sequence_export import probe_video
        run.return_value = SimpleNamespace(returncode=0, stdout='{"streams":[{"codec_type":"video","width":640,"height":480}],"format":{}}')
        result = probe_video(Path("recording.webm"), require_duration=False)
        self.assertEqual(result.editing_size, (640, 480))
        with self.assertRaisesRegex(ValueError, "영상 길이"):
            probe_video(Path("recording.webm"))

    @patch("media_editor.sequence_export.find_ffprobe", return_value="ffprobe")
    @patch("media_editor.sequence_export.subprocess.run")
    def test_invalid_video_size_is_rejected_before_opening_crop(self, run, _):
        from media_editor.sequence_export import probe_video
        run.return_value = SimpleNamespace(returncode=0, stdout='{"streams":[{"codec_type":"video","width":0,"height":480}],"format":{}}')
        with self.assertRaisesRegex(ValueError, "영상 해상도"):
            probe_video(Path("broken.mp4"), require_duration=False)
