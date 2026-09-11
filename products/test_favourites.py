from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
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
        self.assertEqual(favourite.score, 60)

        increment_favourite_counts([CartLine(self.variant, 2)])
        favourite.refresh_from_db()
        self.assertEqual(favourite.purchase_count, 5)
        self.assertEqual(favourite.score, 100)

    def test_wishlist_add_and_remove_adjusts_score(self):
        record_wishlist_change(self.product, added=True)
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.wishlist_count, 1)
        self.assertEqual(favourite.score, 4)

        record_wishlist_change(self.product, added=False)
        favourite.refresh_from_db()
        self.assertEqual(favourite.wishlist_count, 0)
        self.assertEqual(favourite.score, 0)

    def test_product_view_counts_once_per_visitor(self):
        request = self.factory.get("/")
        request.session = {}
        request.COOKIES = {}
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
        self.client.get(url)
        favourite.refresh_from_db()
        self.assertEqual(favourite.view_count, 1)
        self.assertEqual(favourite.score, 1)

    def test_logged_in_user_does_not_score_again_from_another_browser(self):
        User = get_user_model()
        user = User.objects.create_user(email="viewer@example.com", password="test-pass-123")
        url = reverse("products:detail", kwargs={"slug": self.product.slug})

        first = Client()
        first.force_login(user)
        first.get(url)

        second = Client()
        second.force_login(user)
        second.get(url)

        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.view_count, 1)
        self.assertEqual(favourite.score, 1)

    def test_two_visitors_each_add_one_view(self):
        url = reverse("products:detail", kwargs={"slug": self.product.slug})
        Client().get(url)
        Client().get(url)
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.view_count, 2)
        self.assertEqual(favourite.score, 2)

    def test_wishlist_toggle_awards_points(self):
        response = self.client.post(
            reverse("wishlist:toggle"),
            data={"product_id": self.product.pk},
        )
        self.assertEqual(response.status_code, 200)
        favourite = Favourite.objects.get(product=self.product)
        self.assertEqual(favourite.wishlist_count, 1)
        self.assertEqual(favourite.score, 4)

        self.client.post(
            reverse("wishlist:toggle"),
            data={"product_id": self.product.pk},
        )
        favourite.refresh_from_db()
        self.assertEqual(favourite.wishlist_count, 0)
        self.assertEqual(favourite.score, 0)
