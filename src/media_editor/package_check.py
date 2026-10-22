"""End-to-end diagnostics executed by the packaged application itself."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from media_editor.edit_state import EditState
from media_editor.ffmpeg import build_save_command
from media_editor.media import MediaKind
from media_editor.runtime_tools import find_runtime_tool
from media_editor.sequence_export import build_sequence_command, probe_video


def _run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]}\n{result.stderr}")
    return result.stdout


def _check_preview(path: Path) -> None:
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtMultimedia import QMediaPlayer, QVideoSink

    loop = QEventLoop()
    player = QMediaPlayer()
    sink = QVideoSink()
    player.setVideoSink(sink)
    frames = []
    errors = []

    def frame_ready(frame):
        if frame.isValid() and not frame.toImage().isNull():
            frames.append(True)
            loop.quit()

    def failed(error, message):
        errors.append(message)
        loop.quit()

    sink.videoFrameChanged.connect(frame_ready)
    player.errorOccurred.connect(failed)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    player.setSource(QUrl.fromLocalFile(str(path)))
    timer.start(20000)
    player.play()
    loop.exec()
    timer.stop()
    player.stop()
    player.setSource(QUrl())
    if not frames:
        raise RuntimeError(f"Qt Multimedia preview failed: {errors or 'no decoded frame within 20 seconds'}")


def run_checks() -> dict:
    # Require both external tools in the bundle, never accept the developer's PATH.
    tools = {name: find_runtime_tool(name, bundled_only=True) for name in ("ffmpeg", "ffprobe")}
    versions = {name: _run([tool, "-version"]).splitlines()[0] for name, tool in tools.items()}
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QApplication
    from media_editor.app import PreviewReadyMainWindow

    app = QApplication.instance() or QApplication(["MyMediaEditor", "--self-test"])
    window = PreviewReadyMainWindow()
    window.show()
    app.processEvents()
    try:
        with tempfile.TemporaryDirectory(prefix="media-editor-검증 ") as temp:
            root = Path(temp)
            first, second = root / "영상 one.mp4", root / "영상 two.mp4"
            ffmpeg = tools["ffmpeg"]
            _run([ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=10",
                  "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "0.6",
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(first)])
            _run([ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", "color=c=blue:size=80x60:rate=10",
                  "-t", "0.6", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(second)])
            if not probe_video(first).has_audio or probe_video(second).has_audio:
                raise RuntimeError("FFprobe audio metadata check failed")

            source = root / "이미지 source.png"
            image = QImage(64, 48, QImage.Format.Format_RGB32)
            image.fill(0xFF336699)
            if not image.save(str(source)):
                raise RuntimeError("Qt PNG image plugin missing")
            resized = root / "이미지 resized.png"
            _run(build_save_command(source, resized, MediaKind.IMAGE, EditState(resize=(32, 24))))
            output_image = QImage(str(resized))
            if (output_image.width(), output_image.height()) != (32, 24):
                raise RuntimeError("PNG export dimensions incorrect")

            edited = root / "영상 edited.mp4"
            _run(build_save_command(first, edited, MediaKind.VIDEO, EditState(resize=(32, 24))))
            probe = probe_video(edited)
            if (probe.width, probe.height) != (32, 24) or not probe.has_audio:
                raise RuntimeError("MP4 export metadata incorrect")
            webm = root / "영상 source.webm"
            _run([ffmpeg, "-hide_banner", "-y", "-i", str(first), "-c:v", "libvpx-vp9",
                  "-c:a", "libopus", str(webm)])
            converted = root / "영상 converted.mp4"
            _run(build_save_command(webm, converted, MediaKind.VIDEO, EditState()))
            probe_video(converted)

            sequence = root / "영상 sequence.mp4"
            _run(build_sequence_command([first, second]) + [str(sequence)])
            combined = probe_video(sequence)
            if combined.duration_seconds < 1.0 or not combined.has_audio:
                raise RuntimeError("Sequence export duration/audio incorrect")
            _check_preview(edited)
            _check_preview(webm)
    finally:
        window.shutdown()
        window.close()
        app.processEvents()
    return {"status": "passed", "tools": versions,
            "checks": ["GUI startup", "bundled FFmpeg/FFprobe", "PNG resize/export", "MP4 export",
                       "WebM conversion", "sequence with silent clip", "MP4/WebM decoded preview", "Unicode paths"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--self-test-report", type=Path)
    args = parser.parse_args()
    # On CI this also proves the package works without a system FFmpeg/FFprobe.
    previous_path = os.environ.get("PATH", "")
    os.environ["PATH"] = ""
    try:
        try:
            report = run_checks()
        except Exception as exc:
            report = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        os.environ["PATH"] = previous_path
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.self_test_report:
        args.self_test_report.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["status"] == "passed" else 1
