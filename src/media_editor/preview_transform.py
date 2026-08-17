from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QTransform

from media_editor.edit_state import EditState


PREVIEW_MAX_DIMENSION = 1600


def apply_preview_edits(image: QImage, edits: EditState | None) -> QImage:
    """Save pipeline의 공간 편집을 빠른 화면 preview용으로 적용한다."""
    if image.isNull() or edits is None:
        return image.copy()

    result = image.copy()

    if edits.crop is not None:
        x, y, width, height = edits.crop
        x = min(max(0, x), max(0, result.width() - 1))
        y = min(max(0, y), max(0, result.height() - 1))
        width = min(max(1, width), result.width() - x)
        height = min(max(1, height), result.height() - y)
        result = result.copy(x, y, width, height)

    result = _limit_preview_size(result)

    if edits.rotation is not None:
        result = result.transformed(
            QTransform().rotate(edits.rotation),
            Qt.TransformationMode.SmoothTransformation,
        )

    if edits.resize is not None:
        width, height = edits.resize
        preview_width, preview_height = _bounded_dimensions(width, height)
        result = result.scaled(
            preview_width,
            preview_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    # Upscale은 pixel 수만 늘리고 화면 구성은 바꾸지 않으므로 preview에서는 생략한다.
    return result


def _limit_preview_size(image: QImage) -> QImage:
    if max(image.width(), image.height()) <= PREVIEW_MAX_DIMENSION:
        return image

    return image.scaled(
        PREVIEW_MAX_DIMENSION,
        PREVIEW_MAX_DIMENSION,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _bounded_dimensions(width: int, height: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        return 1, 1

    largest = max(width, height)
    if largest <= PREVIEW_MAX_DIMENSION:
        return width, height

    scale = PREVIEW_MAX_DIMENSION / largest
    return max(1, round(width * scale)), max(1, round(height * scale))
