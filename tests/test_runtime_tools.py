from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from media_editor.runtime_tools import (
    configure_runtime_path,
    find_runtime_tool,
)


class RuntimeToolsTest(unittest.TestCase):
    def test_finds_appimage_bundled_tool_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            appdir = Path(temp_dir)
            tool_dir = appdir / "usr" / "bin"
            tool_dir.mkdir(parents=True)
            tool = tool_dir / "ffmpeg"
            tool.write_text("test", encoding="utf-8")

            with patch.dict(os.environ, {"APPDIR": str(appdir)}, clear=False):
                self.assertEqual(find_runtime_tool("ffmpeg"), str(tool))

    def test_configure_runtime_path_prepends_appimage_bin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            appdir = Path(temp_dir)
            tool_dir = appdir / "usr" / "bin"
            tool_dir.mkdir(parents=True)

            with patch.dict(
                os.environ,
                {"APPDIR": str(appdir), "PATH": "/usr/bin"},
                clear=False,
            ):
                configure_runtime_path()
                self.assertEqual(
                    os.environ["PATH"].split(os.pathsep)[0],
                    str(tool_dir),
                )


if __name__ == "__main__":
    unittest.main()
