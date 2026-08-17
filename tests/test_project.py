from pathlib import Path
import tempfile
import unittest

from media_editor.media import MediaKind
from media_editor.project import MediaProject


class MediaProjectTest(unittest.TestCase):
    def test_adds_supported_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "image.png"
            video = Path(temp_dir) / "video.webm"
            image.touch()
            video.touch()

            project = MediaProject()
            added = project.add_paths([image, video])

            self.assertEqual(len(added), 2)
            self.assertEqual(project.assets[0].kind, MediaKind.IMAGE)
            self.assertEqual(project.assets[1].kind, MediaKind.VIDEO)

    def test_does_not_add_same_path_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "image.png"
            image.touch()

            project = MediaProject()
            project.add_paths([image])
            added = project.add_paths([image])

            self.assertEqual(added, [])
            self.assertEqual(len(project.assets), 1)

    def test_removes_asset_from_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "video.mp4"
            video.touch()

            project = MediaProject()
            asset = project.add_paths([video])[0]
            project.remove(asset)

            self.assertEqual(project.assets, [])


if __name__ == "__main__":
    unittest.main()
