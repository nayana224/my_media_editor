from pathlib import Path
import shutil

from media_editor.media import MediaKind


def find_ffmpeg() -> str:
    """PATH에서 ffmpeg 실행 파일을 찾는다."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise FileNotFoundError(
            "ffmpeg를 찾을 수 없습니다. Ubuntu에서는 'sudo apt install ffmpeg'로 "
            "설치하고 Windows에서는 ffmpeg를 PATH에 추가해 주세요."
        )
    return ffmpeg_path


def make_upscale_output_path(input_path: Path, kind: MediaKind, scale: int) -> Path:
    """원본을 덮어쓰지 않는 upscale output 경로를 만든다."""
    suffix = ".png" if kind is MediaKind.IMAGE else ".mp4"
    candidate = input_path.with_name(f"{input_path.stem}_upscaled_{scale}x{suffix}")
    index = 1

    while candidate.exists():
        candidate = input_path.with_name(
            f"{input_path.stem}_upscaled_{scale}x_{index}{suffix}"
        )
        index += 1

    return candidate


def build_upscale_command(
    input_path: Path,
    output_path: Path,
    kind: MediaKind,
    scale: int,
) -> list[str]:
    """Lanczos 기반 standard upscale용 ffmpeg 명령을 만든다."""
    if scale not in (2, 4):
        raise ValueError("Standard upscale scale은 2 또는 4만 지원합니다.")

    command = [
        find_ffmpeg(),
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"scale=iw*{scale}:ih*{scale}:flags=lanczos",
    ]

    if kind is MediaKind.IMAGE:
        command.extend(["-frames:v", "1", str(output_path)])
        return command

    command.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vsync",
            "0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return command
