import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from media_editor.transform_dialogs import (
    CropSelectionWidget,
    UpscaleDialog,
)


class TransformDialogsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_crop_starts_with_full_frame_selection(self) -> None:
        widget = CropSelectionWidget(QImage(640, 480, QImage.Format.Format_RGB32), 640, 480)

        self.assertTrue(widget._selection_is_full_frame())
        self.assertEqual(widget.source_rect, (0, 0, 640, 480))

    def test_crop_detects_non_full_selection(self) -> None:
        widget = CropSelectionWidget(QImage(640, 480, QImage.Format.Format_RGB32), 640, 480)
        widget.set_source_rect((10, 20, 320, 240))

        self.assertFalse(widget._selection_is_full_frame())

    def test_upscale_dialog_initializes_without_signal_order_error(self) -> None:
        dialog = UpscaleDialog()

        self.assertEqual(dialog.scale, 2)
        self.assertIn("0 × 0", dialog.info.text())


if __name__ == "__main__":
    unittest.main()
