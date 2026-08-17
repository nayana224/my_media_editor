from pathlib import Path
import shutil

from media_editor.edit_state import EditState
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


def _make_unique_path(candidate: Path) -> Path:
    if not candidate.exists():
        return candidate

    index = 1
    while True:
        indexed = candidate.with_name(f"{candidate.stem}_{index}{candidate.suffix}")
        if not indexed.exists():
            return indexed
        index += 1


def make_upscale_output_path(input_path: Path, kind: MediaKind, scale: int) -> Path:
    suffix = ".png" if kind is MediaKind.IMAGE else ".mp4"
    return _make_unique_path(
        input_path.with_name(f"{input_path.stem}_upscaled_{scale}x{suffix}")
    )


def make_edit_output_path(input_path: Path, kind: MediaKind, action: str) -> Path:
    suffix = ".png" if kind is MediaKind.IMAGE else ".mp4"
    return _make_unique_path(input_path.with_name(f"{input_path.stem}_{action}{suffix}"))


def make_trim_output_path(input_path: Path) -> Path:
    return _make_unique_path(input_path.with_name(f"{input_path.stem}_trimmed.mp4"))


def make_mp4_output_path(input_path: Path) -> Path:
    candidate = (
        input_path.with_suffix(".mp4")
        if input_path.suffix.lower() == ".webm"
        else input_path.with_name(f"{input_path.stem}_export.mp4")
    )
    return _make_unique_path(candidate)


def make_save_output_path(input_path: Path, kind: MediaKind) -> Path:
    suffix = ".png" if kind is MediaKind.IMAGE else ".mp4"
    return _make_unique_path(input_path.with_name(f"{input_path.stem}_edited{suffix}"))


def _atempo_filter(rate: float) -> str:
    """0.25x~4x를 0.5~2.0 범위의 atempo chain으로 만든다."""
    if rate < 0.25 or rate > 4.0:
        raise ValueError("Speed는 0.25× 이상 4.00× 이하만 지원합니다.")

    factors: list[float] = []
    remaining = rate
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    if abs(remaining - 1.0) > 1e-9 or not factors:
        factors.append(remaining)
    return ",".join(f"atempo={factor:.6f}" for factor in factors)


def _h264_mp4_options(
    video_filter: str | None = None,
    audio_filter: str | None = None,
) -> list[str]:
    options = ["-map", "0:v:0", "-map", "0:a?"]
    if video_filter is not None:
        options.extend(["-vf", video_filter])
    if audio_filter is not None:
        options.extend(["-af", audio_filter])
    options.extend(
        [
            "-vsync", "0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
        ]
    )
    return options


def _build_filter_command(
    input_path: Path,
    output_path: Path,
    kind: MediaKind,
    video_filter: str,
) -> list[str]:
    command = [find_ffmpeg(), "-hide_banner", "-y", "-i", str(input_path)]
    if kind is MediaKind.IMAGE:
        command.extend(["-vf", video_filter, "-frames:v", "1", str(output_path)])
        return command
    command.extend(
        _h264_mp4_options(f"{video_filter},pad=ceil(iw/2)*2:ceil(ih/2)*2")
    )
    command.append(str(output_path))
    return command


def build_upscale_command(input_path: Path, output_path: Path, kind: MediaKind, scale: int) -> list[str]:
    if scale not in (2, 4):
        raise ValueError("Standard upscale scale은 2 또는 4만 지원합니다.")
    return _build_filter_command(
        input_path, output_path, kind, f"scale=iw*{scale}:ih*{scale}:flags=lanczos"
    )


def build_crop_command(
    input_path: Path,
    output_path: Path,
    kind: MediaKind,
    x: int,
    y: int,
    width: int,
    height: int,
) -> list[str]:
    if min(x, y) < 0 or width <= 0 or height <= 0:
        raise ValueError("Crop 위치와 크기를 확인해 주세요.")
    return _build_filter_command(
        input_path, output_path, kind, f"crop={width}:{height}:{x}:{y}"
    )


def build_resize_command(
    input_path: Path,
    output_path: Path,
    kind: MediaKind,
    width: int,
    height: int,
) -> list[str]:
    if width <= 0 or height <= 0:
        raise ValueError("Resize 해상도는 1 px 이상이어야 합니다.")
    return _build_filter_command(
        input_path, output_path, kind, f"scale={width}:{height}:flags=lanczos"
    )


def build_rotate_command(
    input_path: Path,
    output_path: Path,
    kind: MediaKind,
    degrees: int,
) -> list[str]:
    filters = {90: "transpose=1", 180: "hflip,vflip", 270: "transpose=2"}
    if degrees not in filters:
        raise ValueError("Rotate는 90, 180, 270도만 지원합니다.")
    return _build_filter_command(input_path, output_path, kind, filters[degrees])


def build_trim_command(input_path: Path, output_path: Path, start_ms: int, end_ms: int) -> list[str]:
    if start_ms < 0:
        raise ValueError("Trim 시작 시간은 0 이상이어야 합니다.")
    if end_ms <= start_ms:
        raise ValueError("Trim 끝 시간은 시작 시간보다 커야 합니다.")
    command = [
        find_ffmpeg(), "-hide_banner", "-y", "-i", str(input_path),
        "-ss", f"{start_ms / 1000:.3f}",
        "-t", f"{(end_ms - start_ms) / 1000:.3f}",
    ]
    command.extend(_h264_mp4_options("pad=ceil(iw/2)*2:ceil(ih/2)*2"))
    command.append(str(output_path))
    return command


def build_mp4_export_command(input_path: Path, output_path: Path) -> list[str]:
    command = [find_ffmpeg(), "-hide_banner", "-y", "-i", str(input_path)]
    command.extend(_h264_mp4_options("pad=ceil(iw/2)*2:ceil(ih/2)*2"))
    command.append(str(output_path))
    return command


def build_save_command(
    input_path: Path,
    output_path: Path,
    kind: MediaKind,
    edits: EditState,
) -> list[str]:
    """누적 편집 상태를 한 번의 FFmpeg 실행으로 저장한다."""
    filters: list[str] = []

    if edits.crop is not None:
        x, y, width, height = edits.crop
        if min(x, y) < 0 or width <= 0 or height <= 0:
            raise ValueError("Crop 위치와 크기를 확인해 주세요.")
        filters.append(f"crop={width}:{height}:{x}:{y}")

    if edits.rotation is not None:
        rotations = {90: "transpose=1", 180: "hflip,vflip", 270: "transpose=2"}
        if edits.rotation not in rotations:
            raise ValueError("Rotate는 90, 180, 270도만 지원합니다.")
        filters.append(rotations[edits.rotation])

    if edits.resize is not None:
        width, height = edits.resize
        if width <= 0 or height <= 0:
            raise ValueError("Resize 해상도는 1 px 이상이어야 합니다.")
        filters.append(f"scale={width}:{height}:flags=lanczos")

    if edits.upscale is not None:
        if edits.upscale not in (2, 4):
            raise ValueError("Standard upscale scale은 2 또는 4만 지원합니다.")
        filters.append(f"scale=iw*{edits.upscale}:ih*{edits.upscale}:flags=lanczos")

    command = [find_ffmpeg(), "-hide_banner", "-y", "-i", str(input_path)]

    if kind is MediaKind.VIDEO and edits.trim is not None:
        start_ms, end_ms = edits.trim
        if start_ms < 0 or end_ms <= start_ms:
            raise ValueError("Trim 구간을 확인해 주세요.")
        command.extend(
            ["-ss", f"{start_ms / 1000:.3f}", "-t", f"{(end_ms - start_ms) / 1000:.3f}"]
        )

    if kind is MediaKind.IMAGE:
        if edits.trim is not None:
            raise ValueError("이미지에는 Trim을 적용할 수 없습니다.")
        if edits.speed is not None:
            raise ValueError("이미지에는 Speed를 적용할 수 없습니다.")
        if filters:
            command.extend(["-vf", ",".join(filters)])
        command.extend(["-frames:v", "1", str(output_path)])
        return command

    audio_filter: str | None = None
    if edits.speed is not None:
        rate = edits.speed
        if rate < 0.25 or rate > 4.0:
            raise ValueError("Speed는 0.25× 이상 4.00× 이하만 지원합니다.")
        filters.append(f"setpts=PTS/{rate:.6f}")
        audio_filter = _atempo_filter(rate)

    filters.append("pad=ceil(iw/2)*2:ceil(ih/2)*2")
    command.extend(_h264_mp4_options(",".join(filters), audio_filter))
    command.append(str(output_path))
    return command
