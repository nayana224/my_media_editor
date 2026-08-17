from dataclasses import dataclass

from media_editor.edit_state import EditState


@dataclass(frozen=True)
class TimelineMapping:
    """원본 source time과 편집 결과 timeline time 사이의 변환 정보."""

    source_start_ms: int
    source_end_ms: int
    speed: float

    @property
    def source_duration_ms(self) -> int:
        return max(0, self.source_end_ms - self.source_start_ms)

    @property
    def output_duration_ms(self) -> int:
        if self.speed <= 0:
            return self.source_duration_ms
        return round(self.source_duration_ms / self.speed)

    def source_to_output_ms(self, source_position_ms: int) -> int:
        """원본 player position을 편집 결과 timeline position으로 바꾼다."""
        source = min(
            max(source_position_ms, self.source_start_ms),
            self.source_end_ms,
        )
        relative = source - self.source_start_ms
        return min(
            self.output_duration_ms,
            max(0, round(relative / self.speed)),
        )

    def output_to_source_ms(self, output_position_ms: int) -> int:
        """편집 결과 timeline position을 원본 player position으로 바꾼다."""
        output = min(
            max(0, output_position_ms),
            self.output_duration_ms,
        )
        source = self.source_start_ms + round(output * self.speed)
        return min(self.source_end_ms, max(self.source_start_ms, source))


def build_timeline_mapping(
    source_duration_ms: int,
    edits: EditState | None,
) -> TimelineMapping:
    """현재 Trim/Speed를 반영한 결과 timeline mapping을 만든다."""
    duration = max(0, source_duration_ms)
    start_ms = 0
    end_ms = duration
    speed = 1.0

    if edits is not None:
        if edits.trim is not None:
            trim_start, trim_end = edits.trim
            start_ms = min(max(0, trim_start), duration)
            end_ms = min(max(start_ms, trim_end), duration)

        if edits.speed is not None:
            speed = edits.speed

    if speed <= 0:
        speed = 1.0

    return TimelineMapping(
        source_start_ms=start_ms,
        source_end_ms=end_ms,
        speed=speed,
    )


def format_timeline_time(milliseconds: int) -> str:
    """편집 timeline 시간을 MM:SS.mmm 형식으로 표시한다."""
    milliseconds = max(0, milliseconds)
    total_seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"
