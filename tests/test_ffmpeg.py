from pathlib import Path
import unittest
from unittest.mock import patch

from media_editor.ffmpeg import build_upscale_command
from media_editor.media import MediaKind


class BuildUpscaleCommandTest(unittest.TestCase):
    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_builds_video_upscale_command(self, _mock_find_ffmpeg) -> None:
        command = build_upscale_command(
            Path("input.webm"),
            Path("output.mp4"),
            MediaKind.VIDEO,
            2,
        )

        self.assertIn("scale=iw*2:ih*2:flags=lanczos", command)
        self.assertIn("libx264", command)
        self.assertIn("aac", command)
        vsync_index = command.index("-vsync")
        self.assertEqual(command[vsync_index + 1], "0")

    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_builds_image_upscale_command(self, _mock_find_ffmpeg) -> None:
        command = build_upscale_command(
            Path("input.jpg"),
            Path("output.png"),
            MediaKind.IMAGE,
            4,
        )

        self.assertIn("scale=iw*4:ih*4:flags=lanczos", command)
        self.assertIn("-frames:v", command)
        self.assertNotIn("libx264", command)

    def test_rejects_unsupported_scale(self) -> None:
        with self.assertRaises(ValueError):
            build_upscale_command(
                Path("input.webm"),
                Path("output.mp4"),
                MediaKind.VIDEO,
                3,
            )


if __name__ == "__main__":
    unittest.main()
