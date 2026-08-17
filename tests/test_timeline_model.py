import unittest

from media_editor.edit_state import EditState
from media_editor.timeline_model import (
    build_timeline_mapping,
    format_timeline_time,
)


class TimelineMappingTest(unittest.TestCase):
    def test_trim_rebases_timeline_to_zero(self) -> None:
        mapping = build_timeline_mapping(
            32_200,
            EditState(trim=(6_696, 32_200)),
        )
        self.assertEqual(mapping.output_duration_ms, 25_504)
        self.assertEqual(mapping.source_to_output_ms(6_696), 0)
        self.assertEqual(mapping.source_to_output_ms(9_075), 2_379)
        self.assertEqual(mapping.output_to_source_ms(0), 6_696)

    def test_speed_changes_output_duration_and_seek_mapping(self) -> None:
        mapping = build_timeline_mapping(
            32_200,
            EditState(trim=(6_696, 32_200), speed=2.0),
        )
        self.assertEqual(mapping.output_duration_ms, 12_752)
        self.assertEqual(mapping.output_to_source_ms(5_000), 16_696)
        self.assertEqual(mapping.source_to_output_ms(16_696), 5_000)

    def test_without_edits_uses_full_source_duration(self) -> None:
        mapping = build_timeline_mapping(10_000, EditState())
        self.assertEqual(mapping.output_duration_ms, 10_000)
        self.assertEqual(mapping.source_start_ms, 0)
        self.assertEqual(mapping.source_end_ms, 10_000)

    def test_formats_milliseconds(self) -> None:
        self.assertEqual(format_timeline_time(12_752), "00:12.752")
        self.assertEqual(format_timeline_time(61_005), "01:01.005")


if __name__ == "__main__":
    unittest.main()
