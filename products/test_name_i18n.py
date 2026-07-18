"""Tests for subject-first Greek product titles."""
from django.test import SimpleTestCase

from products.name_i18n import build_meaning_title, needs_greek_translation


class SubjectFirstTitleTests(SimpleTestCase):
    def test_beef_in_jelly_sachet(self):
        self.assertEqual(
            build_meaning_title(
                "adult-all-breeds-beef-in-jelly",
                "dog",
                category_slug="sachets",
            ),
            "Βοδινό σε ζελέ φακελάκι - για ενήλικους σκύλους κάθε ράτσας",
        )

    def test_dry_food_small_breeds(self):
        self.assertEqual(
            build_meaning_title(
                "adult-small-breeds-chicken",
                "dog",
                category_slug="dry-food",
            ),
            "Κοτόπουλο ξηρά τροφή - για ενήλικους σκύλους μικρόσωμων ρατσών",
        )

    def test_classic_duck(self):
        self.assertEqual(
            build_meaning_title(
                "classic-adult-duck",
                "dog",
                category_slug="dry-food",
            ),
            "Πάπια ξηρά τροφή Classic - για ενήλικους σκύλους",
        )

    def test_puppies_all_breeds(self):
        self.assertEqual(
            build_meaning_title(
                "puppies-all-breeds",
                "dog",
                category_slug="dry-food",
            ),
            "Ξηρά τροφή - για κουτάβια κάθε ράτσας",
        )

    def test_sterilized_cat(self):
        self.assertEqual(
            build_meaning_title(
                "sterilized-chicken",
                "cat",
                category_slug="dry-food",
            ),
            "Κοτόπουλο ξηρά τροφή - για στειρωμένες γάτες",
        )

    def test_canned_mono(self):
        self.assertEqual(
            build_meaning_title(
                "single-protein-arni",
                "dog",
                category_slug="canned-food",
            ),
            "Αρνί κονσέρβα Μονοπρωτεϊνική - για ενήλικους σκύλους",
        )

    def test_needs_old_audience_first(self):
        self.assertTrue(needs_greek_translation("Για ενήλικες γάτες · Κοτόπουλο"))
        self.assertFalse(
            needs_greek_translation(
                "Βοδινό σε ζελέ φακελάκι - για ενήλικους σκύλους κάθε ράτσας"
            )
        )
