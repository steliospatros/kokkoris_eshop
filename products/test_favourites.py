from django.test import TestCase

from products.favourites import increment_favourite_counts
from products.models import AnimalType, Category, Company, Favourite, Product, ProductVariant


class FavouriteCounterTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Alpha Co", code="ALP")
        self.category = Category.objects.create(name="Dry Food")
        self.dog = AnimalType.objects.create(name="Dog", slug="dog")
        self.product = Product.objects.create(
            name="Adult Mix",
            company=self.company,
            category=self.category,
            animal_type=self.dog,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            weight=2,
            price=10,
            stock=5,
        )

    def test_increment_favourite_counts_from_cart_items(self):
        class CartLine:
            def __init__(self, variant, quantity):
                self.product_variant = variant
                self.quantity = quantity

        increment_favourite_counts([CartLine(self.variant, 3)])
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.purchase_count, 3)

        increment_favourite_counts([CartLine(self.variant, 2)])
        favourite.refresh_from_db()
        self.assertEqual(favourite.purchase_count, 5)
