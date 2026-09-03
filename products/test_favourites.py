from django.test import RequestFactory, TestCase
from django.urls import reverse

from products.favourites import (
    increment_favourite_counts,
    record_product_view,
    record_wishlist_change,
)
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
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            weight=2,
            price=10,
            stock=5,
        )
        self.factory = RequestFactory()

    def test_increment_favourite_counts_from_cart_items(self):
        class CartLine:
            def __init__(self, variant, quantity):
                self.product_variant = variant
                self.quantity = quantity

        increment_favourite_counts([CartLine(self.variant, 3)])
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.purchase_count, 3)
        self.assertEqual(favourite.score, 15)

        increment_favourite_counts([CartLine(self.variant, 2)])
        favourite.refresh_from_db()
        self.assertEqual(favourite.purchase_count, 5)
        self.assertEqual(favourite.score, 25)

    def test_wishlist_add_and_remove_adjusts_score(self):
        record_wishlist_change(self.product, added=True)
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.wishlist_count, 1)
        self.assertEqual(favourite.score, 3)

        record_wishlist_change(self.product, added=False)
        favourite.refresh_from_db()
        self.assertEqual(favourite.wishlist_count, 0)
        self.assertEqual(favourite.score, 0)

    def test_product_view_counts_once_per_session(self):
        request = self.factory.get("/")
        request.session = {}
        request.user = None

        self.assertTrue(record_product_view(request, self.product))
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.view_count, 1)
        self.assertEqual(favourite.score, 1)

        self.assertFalse(record_product_view(request, self.product))
        favourite.refresh_from_db()
        self.assertEqual(favourite.view_count, 1)
        self.assertEqual(favourite.score, 1)

    def test_product_detail_page_records_a_view(self):
        url = reverse("products:detail", kwargs={"slug": self.product.slug})
        self.client.get(url)
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.view_count, 1)
        self.assertEqual(favourite.score, 1)

        self.client.get(url)
        favourite.refresh_from_db()
        self.assertEqual(favourite.view_count, 1)

    def test_wishlist_toggle_awards_points(self):
        response = self.client.post(
            reverse("wishlist:toggle"),
            data={"product_id": self.product.pk},
        )
        self.assertEqual(response.status_code, 200)
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.wishlist_count, 1)
        self.assertEqual(favourite.score, 3)

        self.client.post(
            reverse("wishlist:toggle"),
            data={"product_id": self.product.pk},
        )
        favourite.refresh_from_db()
        self.assertEqual(favourite.wishlist_count, 0)
        self.assertEqual(favourite.score, 0)
