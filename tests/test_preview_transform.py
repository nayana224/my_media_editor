import unittest

from PySide6.QtGui import QImage

from media_editor.edit_state import EditState
from media_editor.preview_transform import apply_preview_edits


class PreviewTransformTest(unittest.TestCase):
    def test_crop_changes_preview_size(self) -> None:
        image = QImage(640, 480, QImage.Format.Format_RGB32)
        result = apply_preview_edits(
            image,
            EditState(crop=(10, 20, 320, 200)),
        )
        self.assertEqual((result.width(), result.height()), (320, 200))

    def test_rotate_swaps_preview_dimensions(self) -> None:
        image = QImage(640, 480, QImage.Format.Format_RGB32)
        result = apply_preview_edits(
            image,
            EditState(rotation=90),
        )
        self.assertEqual((result.width(), result.height()), (480, 640))

    def test_resize_uses_requested_aspect_ratio(self) -> None:
        image = QImage(640, 480, QImage.Format.Format_RGB32)
        result = apply_preview_edits(
            image,
            EditState(resize=(1280, 720)),
        )
        self.assertEqual((result.width(), result.height()), (1280, 720))

    def test_upscale_does_not_allocate_large_preview(self) -> None:
        image = QImage(640, 480, QImage.Format.Format_RGB32)
        result = apply_preview_edits(
            image,
            EditState(upscale=4),
        )
        self.assertEqual((result.width(), result.height()), (640, 480))


if __name__ == "__main__":
    unittest.main()
