from django.test import SimpleTestCase

from products.description_sync import sync_description_title


class SyncDescriptionTitleTests(SimpleTestCase):
    def test_replaces_quoted_english_title(self):
        desc = (
            "Το PROFINE «Adult Large Chicken & Potatoes» αποτελεί πλήρη "
            "καθημερινή διατροφή για ενήλικους σκύλους μεγαλόσωμων φυλών."
        )
        out = sync_description_title(
            desc,
            "Για ενήλικους σκύλους μεγαλόσωμων ρατσών · Κοτόπουλο και Πατάτες",
        )
        self.assertIn(
            "«Για ενήλικους σκύλους μεγαλόσωμων ρατσών · Κοτόπουλο και Πατάτες»",
            out,
        )
        self.assertNotIn("Adult Large", out)
        self.assertIn("μεγαλόσωμων ρατσών", out)
        self.assertNotIn("φυλών", out)

    def test_all_breeds_phrase(self):
        desc = "Ιδανικό για κουτάβια όλων των φυλών."
        out = sync_description_title(desc, "Για κουτάβια κάθε ράτσας")
        self.assertEqual(out, "Ιδανικό για κουτάβια κάθε ράτσας.")

    def test_noop_when_already_synced(self):
        name = "Για γατάκια · Κοτόπουλο"
        desc = f"Το PROFINE «{name}» αποτελεί ιδανική επιλογή για γατάκια."
        self.assertEqual(sync_description_title(desc, name), desc)
