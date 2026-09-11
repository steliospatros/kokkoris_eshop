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

    def test_core_dry_override(self):
        self.assertEqual(
            build_meaning_title(
                "adult-ocean-dog",
                "dog",
                current_name="Adult Ocean (Dog)",
                category_slug="dry-food",
            ),
            "Σολομός και Τόνος ξηρά τροφή Ocean - για ενήλικους σκύλους",
        )

    def test_core_savoury_medleys(self):
        self.assertEqual(
            build_meaning_title(
                "savoury-medleys-kotopoulo-papia-arakas-karota",
                "dog",
                current_name="Savoury Medleys - Κοτόπουλο, Πάπια, Αρακάς, Καρότα",
                category_slug="canned-food",
            ),
            "Κοτόπουλο, Πάπια, Αρακάς και Καρότα κονσέρβα Savoury Medleys - "
            "για ενήλικους σκύλους",
        )

    def test_core_single_protein_from_can_label(self):
        self.assertEqual(
            build_meaning_title(
                "single-protein-7876340",
                "dog",
                current_name="Single Protein 7876340",
                category_slug="canned-food",
            ),
            "Κοτόπουλο με Πάπια και Καρότα κονσέρβα Duo Protein - για ενήλικους σκύλους",
        )

    def test_everclean_does_not_repeat_ammos(self):
        self.assertEqual(
            build_meaning_title(
                "ammos-ugieines-total-cover",
                "cat",
                current_name="Άμμος υγιεινής Total Cover",
                category_slug="litter",
            ),
            "Άμμος υγιεινής Total Cover - για γάτες",
        )

    def test_everclean_senior(self):
        self.assertEqual(
            build_meaning_title(
                "ammos-ugieines-senior-cat",
                "cat",
                current_name="Άμμος υγιεινής Senior Cat",
                category_slug="litter",
            ),
            "Άμμος υγιεινής Senior Cat - για ηλικιωμένες γάτες",
        )

    def test_wild_side_keeps_line_name(self):
        self.assertEqual(
            build_meaning_title(
                "salmon-hunter-xera-trophe-gia-gates",
                "cat",
                current_name="Salmon Hunter ξηρά τροφή - για γάτες",
                category_slug="dry-food",
            ),
            "Salmon Hunter ξηρά τροφή - για γάτες",
        )

    def test_core_wet_accents(self):
        self.assertEqual(
            build_meaning_title(
                "bodino-me-mprokolo",
                "dog",
                current_name="Βοδινο Με Μπροκολο",
                category_slug="canned-food",
            ),
            "Βοδινό με Μπρόκολο κονσέρβα - για ενήλικους σκύλους",
        )

    def test_kitten_pate(self):
        self.assertEqual(
            build_meaning_title(
                "kitten-pate-kotopoulo-ue-tono",
                "cat",
                current_name="Kitten - Πατέ Κοτόπουλο µε Τόνο",
                category_slug="canned-food",
            ),
            "Κοτόπουλο με Τόνο πατέ κονσέρβα - για γατάκια",
        )

    def test_needs_old_audience_first(self):
        self.assertTrue(needs_greek_translation("Για ενήλικες γάτες · Κοτόπουλο"))
        self.assertFalse(
            needs_greek_translation(
                "Βοδινό σε ζελέ φακελάκι - για ενήλικους σκύλους κάθε ράτσας"
            )
        )
