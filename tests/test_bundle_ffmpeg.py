import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("bundle_ffmpeg", Path(__file__).resolve().parents[1] / "scripts/bundle_ffmpeg.py")
bundler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundler)


class BundleFfmpegTest(unittest.TestCase):
    def test_checksum_mismatch_deletes_download(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "archive.zip"
            with patch.object(bundler.urllib.request, "urlopen", return_value=io.BytesIO(b"corrupt")):
                with self.assertRaisesRegex(RuntimeError, "SHA256 mismatch"):
                    bundler.download("https://example.invalid/archive.zip", target, "0" * 64)
            self.assertFalse(target.exists())

    def test_verified_archive_bundles_pair_and_notices_without_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            cache.mkdir()
            archive = cache / "pair.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("ffmpeg/bin/ffmpeg.exe", "encoder")
                z.writestr("ffmpeg/bin/ffprobe.exe", "probe")
                z.writestr("ffmpeg/LICENSE.txt", "supplier license")
            checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
            (root / "packaging").mkdir()
            manifest = {"windows-x64": {"url": "https://example.invalid/pair.zip", "sha256": checksum}}
            (root / "packaging/ffmpeg.json").write_text(json.dumps(manifest))
            with patch.object(bundler, "PROJECT_ROOT", root):
                bundler.bundle("windows-x64", root / "package", cache)
            self.assertEqual((root / "package/bin/ffprobe.exe").read_text(), "probe")
            self.assertTrue((root / "package/third-party/ffmpeg/LICENSE.txt").is_file())
            with zipfile.ZipFile(archive, "a") as z:
                z.writestr("ffmpeg/../../escape.txt", "unsafe")
            manifest["windows-x64"]["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
            (root / "packaging/ffmpeg.json").write_text(json.dumps(manifest))
            with patch.object(bundler, "PROJECT_ROOT", root):
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    bundler.bundle("windows-x64", root / "second", cache)
            self.assertFalse((root / "escape.txt").exists())
