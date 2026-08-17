from pathlib import Path
import unittest
from unittest.mock import patch

from media_editor.sequence_export import VideoProbe, build_sequence_command


class SequenceExportTest(unittest.TestCase):
    @patch("media_editor.sequence_export.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("media_editor.sequence_export.probe_video")
    def test_builds_concat_with_silence_for_missing_audio(
        self,
        mock_probe,
        _mock_ffmpeg,
    ) -> None:
        mock_probe.side_effect = [
            VideoProbe(1920, 1080, 2.0, True),
            VideoProbe(1280, 720, 3.0, False),
        ]

        command = build_sequence_command(
            [Path("a.mp4"), Path("b.webm")]
        )
        joined = " ".join(command)

        self.assertIn("concat=n=2:v=1:a=1", joined)
        self.assertIn("scale=1920:1080", joined)
        self.assertIn("anullsrc=r=48000:cl=stereo", joined)
        self.assertIn("atrim=duration=3.000000", joined)
        self.assertIn("[vout]", command)
        self.assertIn("[aout]", command)

    def test_rejects_single_clip(self) -> None:
        with self.assertRaises(ValueError):
            build_sequence_command([Path("only.mp4")])


if __name__ == "__main__":
    unittest.main()
