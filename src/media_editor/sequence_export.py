from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

from media_editor.ffmpeg import find_ffmpeg
from media_editor.runtime_tools import find_runtime_tool


@dataclass(frozen=True)
class VideoProbe:
    width: int
    height: int
    duration_seconds: float
    has_audio: bool
    rotation: int = 0

    @property
    def editing_size(self) -> tuple[int, int]:
        # FFmpeg autorotates before applying crop filters.
        return (self.height, self.width) if self.rotation % 180 == 90 else (self.width, self.height)


def find_ffprobe() -> str:
    """FFmpeg와 동일한 배포 경로에서 ffprobe를 찾는다."""
    return find_runtime_tool("ffprobe")


def probe_video(path: Path, *, require_duration: bool = True) -> VideoProbe:
    """Sequence 정규화에 필요한 video metadata를 읽는다."""
    command = [
        find_ffprobe(),
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,width,height:stream_tags=rotate:stream_side_data=rotation:format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("영상 정보 읽기 시간이 초과됐습니다. 다른 파일로 다시 시도해 주세요.") from exc
    if completed.returncode != 0:
        raise RuntimeError(
            f"영상 정보를 읽지 못했습니다: {path}\n{completed.stderr.strip()}"
        )

    data = json.loads(completed.stdout)
    streams = data.get("streams", [])
    video_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise ValueError(f"video stream이 없습니다: {path}")

    duration = float(data.get("format", {}).get("duration", 0.0) or 0.0)
    if require_duration and duration <= 0:
        raise ValueError(f"영상 길이를 읽지 못했습니다: {path}")

    width, height = int(video_stream["width"]), int(video_stream["height"])
    if width <= 0 or height <= 0:
        raise ValueError(f"영상 해상도를 읽지 못했습니다: {path}")
    rotation = video_stream.get("tags", {}).get("rotate", 0)
    for side_data in video_stream.get("side_data_list", []):
        if "rotation" in side_data:
            rotation = side_data["rotation"]
    return VideoProbe(
        width=width,
        height=height,
        duration_seconds=duration,
        rotation=round(float(rotation)) % 360,
        has_audio=any(
            stream.get("codec_type") == "audio" for stream in streams
        ),
    )


def make_sequence_output_path(first_path: Path) -> Path:
    """첫 clip 옆에 중복되지 않는 sequence output 경로를 만든다."""
    candidate = first_path.with_name(f"{first_path.stem}_sequence.mp4")
    if not candidate.exists():
        return candidate

    index = 1
    while True:
        indexed = first_path.with_name(
            f"{first_path.stem}_sequence_{index}.mp4"
        )
        if not indexed.exists():
            return indexed
        index += 1


def build_sequence_command(paths: list[Path]) -> list[str]:
    """여러 video를 첫 clip 해상도에 맞춰 재인코딩 후 concat한다."""
    if len(paths) < 2:
        raise ValueError("Sequence에는 video가 2개 이상 필요합니다.")

    probes = [probe_video(path) for path in paths]
    target_width = probes[0].width
    target_height = probes[0].height

    command = [find_ffmpeg(), "-hide_banner", "-y"]
    for path in paths:
        command.extend(["-i", str(path)])

    filters: list[str] = []
    concat_inputs: list[str] = []

    for index, probe in enumerate(probes):
        filters.append(
            f"[{index}:v]"
            f"scale={target_width}:{target_height}:"
            "force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,setpts=PTS-STARTPTS,format=yuv420p"
            f"[v{index}]"
        )

        if probe.has_audio:
            filters.append(
                f"[{index}:a]"
                "aresample=48000,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                "asetpts=PTS-STARTPTS"
                f"[a{index}]"
            )
        else:
            filters.append(
                "anullsrc=r=48000:cl=stereo,"
                f"atrim=duration={probe.duration_seconds:.6f},"
                "asetpts=PTS-STARTPTS"
                f"[a{index}]"
            )

        concat_inputs.extend([f"[v{index}]", f"[a{index}]"])

    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(paths)}:v=1:a=1[vout][aout]"
    )

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
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
        ]
    )
    return command
