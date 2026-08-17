import unittest

from PySide6.QtGui import QImage

from media_editor.edit_state import EditState
from media_editor.live_edit_dialogs import _pending_state, _render_pending


class FakeParent:
    def __init__(self) -> None:
        self.state = EditState(
            crop=(10, 5, 80, 40),
            rotation=90,
            resize=(120, 60),
            speed=1.5,
        )
        self.image = QImage(100, 50, QImage.Format.Format_RGB32)

    def _current_edits(self) -> EditState:
        return self.state

    def _source_preview_image(self) -> QImage:
        return self.image


class LiveEditPreviewTest(unittest.TestCase):
    def test_temporary_override_does_not_mutate_pending_state(self) -> None:
        parent = FakeParent()

        temporary = _pending_state(parent, rotation=180)

        self.assertEqual(temporary.rotation, 180)
        self.assertEqual(temporary.crop, parent.state.crop)
        self.assertEqual(parent.state.rotation, 90)

    def test_render_uses_complete_pending_pipeline_with_override(self) -> None:
        parent = FakeParent()

        rendered = _render_pending(
            parent,
            rotation=180,
            resize=(64, 32),
        )

        self.assertEqual((rendered.width(), rendered.height()), (64, 32))
        self.assertEqual(parent.state.resize, (120, 60))


if __name__ == "__main__":
    unittest.main()
