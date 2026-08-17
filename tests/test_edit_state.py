import unittest

from media_editor.edit_state import EditState


class EditStateTest(unittest.TestCase):
    def test_reports_pending_labels_in_render_order(self) -> None:
        state = EditState(
            trim=(1_000, 4_000),
            crop=(10, 20, 640, 480),
            rotation=90,
            resize=(1280, 720),
            upscale=2,
            speed=1.5,
        )

        self.assertTrue(state.has_changes)
        self.assertEqual(
            state.labels(),
            [
                "Trim 1.000-4.000s",
                "Crop 640x480",
                "Rotate 90°",
                "Resize 1280x720",
                "Upscale 2x",
                "Speed 1.50x",
            ],
        )

    def test_clear_removes_all_pending_edits(self) -> None:
        state = EditState(
            crop=(0, 0, 100, 100),
            upscale=2,
            speed=0.5,
        )
        state.clear()

        self.assertFalse(state.has_changes)
        self.assertEqual(state.labels(), [])
        self.assertIsNone(state.speed)


if __name__ == "__main__":
    unittest.main()
