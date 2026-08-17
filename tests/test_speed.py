from pathlib import Path
import unittest
from unittest.mock import patch

from media_editor.edit_state import EditState
from media_editor.ffmpeg import _atempo_filter, build_save_command
from media_editor.media import MediaKind


class SpeedRenderTest(unittest.TestCase):
    def test_builds_quality_safe_atempo_chain(self) -> None:
        self.assertEqual(
            _atempo_filter(0.25),
            "atempo=0.500000,atempo=0.500000",
        )
        self.assertEqual(
            _atempo_filter(4.0),
            "atempo=2.000000,atempo=2.000000",
        )

    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_speed_is_applied_to_video_and_audio(self, _mock_find_ffmpeg) -> None:
        command = build_save_command(
            Path("input.mp4"),
            Path("output.mp4"),
            MediaKind.VIDEO,
            EditState(speed=1.5),
        )

        video_filter = command[command.index("-vf") + 1]
        audio_filter = command[command.index("-af") + 1]
        self.assertIn("setpts=PTS/1.500000", video_filter)
        self.assertEqual(audio_filter, "atempo=1.500000")

    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_rejects_speed_on_image(self, _mock_find_ffmpeg) -> None:
        with self.assertRaises(ValueError):
            build_save_command(
                Path("input.png"),
                Path("output.png"),
                MediaKind.IMAGE,
                EditState(speed=2.0),
            )


if __name__ == "__main__":
    unittest.main()
