from enum import Enum
from pathlib import Path


class MediaKind(Enum):
    IMAGE = "image"
    VIDEO = "video"


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
VIDEO_SUFFIXES = {".webm", ".mp4"}


def classify_media(path: Path) -> MediaKind:
    """지원하는 이미지 또는 영상 파일 종류를 판별한다."""
    suffix = path.suffix.lower()

    if suffix in IMAGE_SUFFIXES:
        return MediaKind.IMAGE

    if suffix in VIDEO_SUFFIXES:
        return MediaKind.VIDEO

    raise ValueError(
        "지원하지 않는 파일 형식입니다. "
        "PNG, JPG, JPEG, WebM, MP4 파일을 사용해 주세요."
    )


def format_duration(milliseconds: int) -> str:
    """밀리초 시간을 MM:SS 형식으로 표시한다."""
    total_seconds = max(0, milliseconds // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"
