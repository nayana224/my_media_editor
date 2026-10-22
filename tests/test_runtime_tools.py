from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from media_editor.runtime_tools import (
    configure_runtime_path,
    find_runtime_tool,
)


class RuntimeToolsTest(unittest.TestCase):
    def test_finds_bundled_tool_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            appdir = Path(temp_dir)
            tool_dir = appdir / "usr" / "bin"
            tool_dir.mkdir(parents=True)
            tool_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
            tool = tool_dir / tool_name
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


class PackagedToolPathsTest(unittest.TestCase):
    def test_nuitka_onefile_uses_original_bundle_for_both_tools(self):
        from types import SimpleNamespace
        import media_editor.runtime_tools as runtime
        from media_editor.sequence_export import find_ffprobe

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "설치 폴더"
            (bundle / "bin").mkdir(parents=True)
            extracted = root / "onefile_temp"
            extracted.mkdir()
            for name in ("ffmpeg", "ffprobe"):
                (bundle / "bin" / (name + ".exe")).touch()
            with patch.dict(os.environ, {"PATH": ""}, clear=True), \
                 patch.object(runtime.sys, "platform", "win32"), \
                 patch.object(runtime.sys, "executable", str(extracted / "MyMediaEditor.exe")), \
                 patch.object(runtime, "__compiled__", SimpleNamespace(containing_dir=str(bundle)), create=True):
                self.assertEqual(runtime.find_runtime_tool("ffmpeg", bundled_only=True), str(bundle / "bin/ffmpeg.exe"))
                self.assertEqual(find_ffprobe(), str(bundle / "bin/ffprobe.exe"))

    def test_bundled_only_does_not_accept_system_tools(self):
        import media_editor.runtime_tools as runtime
        with patch.object(runtime, "_runtime_tool_directories", return_value=[]), \
             patch.object(runtime.shutil, "which", return_value="/usr/bin/ffprobe") as which:
            with self.assertRaises(FileNotFoundError):
                runtime.find_runtime_tool("ffprobe", bundled_only=True)
            which.assert_not_called()


if __name__ == "__main__":
    unittest.main()
