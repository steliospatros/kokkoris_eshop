"""Tests for smart storefront search."""
from django.test import TestCase

from products.models import AnimalType, Category, Company, Favourite, Product
from products.search import parse_search_query, search_products


class SmartSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dog = AnimalType.objects.create(name="Dog", slug="dog")
        cls.cat = AnimalType.objects.create(name="Cat", slug="cat")
        cls.dry = Category.objects.create(name="Dry Food", slug="dry-food")
        cls.litter = Category.objects.create(name="Litter", slug="litter")
        cls.canned = Category.objects.create(name="Canned Food", slug="canned-food")
        cls.ownat = Company.objects.create(name="OWNAT", code="OWN")
        cls.ever = Company.objects.create(name="EVERCLEAN", code="EVR")

        cls.dog_dry = Product.objects.create(
            name="Adult Chicken & Rice",
            company=cls.ownat,
            animal_type=cls.dog,
            category=cls.dry,
            description="Complete dry food for adult dogs",
            is_active=True,
        )
        cls.dog_chicken = Product.objects.create(
            name="Κοτοπουλο Premium",
            company=cls.ownat,
            animal_type=cls.dog,
            category=cls.dry,
            is_active=True,
        )
        cls.cat_litter = Product.objects.create(
            name="Clumping Litter",
            company=cls.ever,
            animal_type=cls.cat,
            category=cls.litter,
            is_active=True,
        )
        cls.cat_sterile = Product.objects.create(
            name="Sterilised Chicken & Rice",
            company=cls.ownat,
            animal_type=cls.cat,
            category=cls.dry,
            is_active=True,
        )
        Favourite.objects.filter(product=cls.dog_chicken).update(purchase_count=50)
        Favourite.objects.filter(product=cls.dog_dry).update(purchase_count=10)

    def test_dog_greek_returns_all_dogs_favourites_first(self):
        results = search_products("σκύλος", limit=10)
        ids = [p.id for p in results]
        self.assertIn(self.dog_chicken.id, ids)
        self.assertIn(self.dog_dry.id, ids)
        self.assertNotIn(self.cat_litter.id, ids)
        self.assertEqual(ids[0], self.dog_chicken.id)

    def test_greeklish_skilotrofi(self):
        intent = parse_search_query("skilotrofi")
        self.assertEqual(intent.animals, {"dog"})

    def test_dry_food_and_dog(self):
        intent = parse_search_query("ξηρά τροφή σκύλου")
        self.assertEqual(intent.animals, {"dog"})
        self.assertEqual(intent.categories, {"dry-food"})

    def test_ammos_misspelling(self):
        intent = parse_search_query("αμος")
        self.assertEqual(intent.categories, {"litter"})
        results = search_products("ammos")
        self.assertEqual([p.id for p in results], [self.cat_litter.id])

    def test_brand_ownat(self):
        results = search_products("ουνατ")
        self.assertTrue(results)
        self.assertTrue(all(p.company.name == "OWNAT" for p in results))

    def test_chicken_synonym_or(self):
        results = search_products("κοτόπουλο")
        ids = {p.id for p in results}
        self.assertIn(self.dog_chicken.id, ids)
        self.assertIn(self.dog_dry.id, ids)

    def test_sterilized(self):
        results = search_products("στειρωμένα")
        self.assertEqual([p.id for p in results], [self.cat_sterile.id])
