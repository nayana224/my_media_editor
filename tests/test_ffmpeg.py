from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from media_editor.ffmpeg import (
    build_crop_command,
    build_mp4_export_command,
    build_resize_command,
    build_rotate_command,
    build_trim_command,
    build_upscale_command,
    make_mp4_output_path,
)
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
        self.assertIn("pad=ceil(iw/2)*2:ceil(ih/2)*2", command)
        self.assertIn("libx264", command)
        self.assertIn("aac", command)

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


class BuildEditCommandTest(unittest.TestCase):
    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_builds_video_crop_command(self, _mock_find_ffmpeg) -> None:
        command = build_crop_command(
            Path("input.webm"),
            Path("cropped.mp4"),
            MediaKind.VIDEO,
            10,
            20,
            640,
            480,
        )
        self.assertIn("crop=640:480:10:20,pad=ceil(iw/2)*2:ceil(ih/2)*2", command)
        self.assertIn("libx264", command)

    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_builds_image_resize_command(self, _mock_find_ffmpeg) -> None:
        command = build_resize_command(
            Path("input.png"),
            Path("resized.png"),
            MediaKind.IMAGE,
            1280,
            720,
        )
        self.assertIn("scale=1280:720:flags=lanczos", command)
        self.assertIn("-frames:v", command)

    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_builds_counter_clockwise_rotate_command(self, _mock_find_ffmpeg) -> None:
        command = build_rotate_command(
            Path("input.mp4"),
            Path("rotated.mp4"),
            MediaKind.VIDEO,
            270,
        )
        self.assertIn("transpose=2,pad=ceil(iw/2)*2:ceil(ih/2)*2", command)

    def test_rejects_invalid_rotate_degrees(self) -> None:
        with self.assertRaises(ValueError):
            build_rotate_command(
                Path("input.mp4"),
                Path("rotated.mp4"),
                MediaKind.VIDEO,
                45,
            )


class BuildTrimCommandTest(unittest.TestCase):
    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_builds_trim_command_with_duration(self, _mock_find_ffmpeg) -> None:
        command = build_trim_command(
            Path("input.webm"),
            Path("trimmed.mp4"),
            1_500,
            4_750,
        )

        start_index = command.index("-ss")
        duration_index = command.index("-t")
        self.assertEqual(command[start_index + 1], "1.500")
        self.assertEqual(command[duration_index + 1], "3.250")
        self.assertIn("libx264", command)

    def test_rejects_invalid_trim_range(self) -> None:
        with self.assertRaises(ValueError):
            build_trim_command(
                Path("input.webm"),
                Path("trimmed.mp4"),
                5_000,
                5_000,
            )


class BuildMp4ExportCommandTest(unittest.TestCase):
    @patch("media_editor.ffmpeg.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_builds_h264_aac_export(self, _mock_find_ffmpeg) -> None:
        command = build_mp4_export_command(
            Path("input.webm"),
            Path("output.mp4"),
        )

        self.assertIn("libx264", command)
        self.assertIn("aac", command)
        self.assertIn("yuv420p", command)
        self.assertEqual(command[-1], "output.mp4")

    def test_webm_default_export_uses_mp4_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "sample.webm"
            self.assertEqual(
                make_mp4_output_path(input_path),
                Path(temp_dir) / "sample.mp4",
            )


if __name__ == "__main__":
    unittest.main()
