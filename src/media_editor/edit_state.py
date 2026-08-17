from dataclasses import dataclass


@dataclass
class EditState:
    """원본을 변경하지 않고 Save 시 적용할 편집 상태를 보관한다."""

    trim: tuple[int, int] | None = None
    crop: tuple[int, int, int, int] | None = None
    rotation: int | None = None
    resize: tuple[int, int] | None = None
    upscale: int | None = None
    speed: float | None = None

    @property
    def has_changes(self) -> bool:
        return any(
            value is not None
            for value in (
                self.trim,
                self.crop,
                self.rotation,
                self.resize,
                self.upscale,
                self.speed,
            )
        )

    def labels(self) -> list[str]:
        """현재 누적된 편집 항목을 표시 순서대로 반환한다."""
        labels: list[str] = []
        if self.trim is not None:
            start_ms, end_ms = self.trim
            labels.append(f"Trim {start_ms / 1000:.3f}-{end_ms / 1000:.3f}s")
        if self.crop is not None:
            _, _, width, height = self.crop
            labels.append(f"Crop {width}x{height}")
        if self.rotation is not None:
            labels.append(f"Rotate {self.rotation}°")
        if self.resize is not None:
            width, height = self.resize
            labels.append(f"Resize {width}x{height}")
        if self.upscale is not None:
            labels.append(f"Upscale {self.upscale}x")
        if self.speed is not None:
            labels.append(f"Speed {self.speed:.2f}x")
        return labels

    def clear(self) -> None:
        self.trim = None
        self.crop = None
        self.rotation = None
        self.resize = None
        self.upscale = None
        self.speed = None
