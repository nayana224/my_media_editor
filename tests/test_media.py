from pathlib import Path
import unittest

from media_editor.media import MediaKind, classify_media, format_duration


class ClassifyMediaTest(unittest.TestCase):
    def test_classifies_supported_image(self) -> None:
        self.assertIs(
            classify_media(Path("photo.JPG")),
            MediaKind.IMAGE,
        )

    def test_classifies_supported_video(self) -> None:
        self.assertIs(
            classify_media(Path("clip.webm")),
            MediaKind.VIDEO,
        )

    def test_rejects_unsupported_file(self) -> None:
        with self.assertRaises(ValueError):
            classify_media(Path("document.pdf"))


class FormatDurationTest(unittest.TestCase):
    def test_formats_minutes_and_seconds(self) -> None:
        self.assertEqual(format_duration(125_900), "02:05")

    def test_clamps_negative_duration(self) -> None:
        self.assertEqual(format_duration(-1), "00:00")


if __name__ == "__main__":
    unittest.main()
