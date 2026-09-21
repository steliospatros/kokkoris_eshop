from django.test import TestCase

from accounts.floor_options import FLOOR_OTHER_LABEL, FLOOR_PRESET_OPTIONS


class FloorOptionsTests(TestCase):
    def test_presets_stop_at_fifth_floor(self):
        self.assertEqual(FLOOR_PRESET_OPTIONS[0], "Ισόγειο")
        self.assertEqual(FLOOR_PRESET_OPTIONS[-1], "5ος όροφος")
        self.assertEqual(FLOOR_OTHER_LABEL, "Άλλο")
        self.assertNotIn("6ος όροφος", FLOOR_PRESET_OPTIONS)
        self.assertNotIn("9ος όροφος", FLOOR_PRESET_OPTIONS)
        self.assertNotIn("Εισόγειο", FLOOR_PRESET_OPTIONS)
