from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administration.models import AdministrationUser
from administration.permissions import user_is_administration_user
from orders.models import Order
from products.models import AnimalType, Category, Company, Product, ProductVariant


class AdministrationAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="test-pass-123",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True},
        )

    def test_allow_list_grants_access(self):
        self.assertTrue(user_is_administration_user(self.admin_user))
        self.assertFalse(user_is_administration_user(self.other_user))

    def test_inactive_administration_user_is_denied(self):
        AdministrationUser.objects.filter(email="steliospatros@gmail.com").update(is_active=False)
        self.assertFalse(user_is_administration_user(self.admin_user))

    def test_administration_hub_requires_allow_list(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("administration:hub"))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Προϊόντα")

    def test_account_hub_shows_management_link_only_for_admins(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("accounts:hub"))
        self.assertNotContains(response, "Διαχείριση")

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("accounts:hub"))
        self.assertContains(response, "Διαχείριση")


class AdministrationInventoryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True},
        )

        self.company = Company.objects.create(name="Alpha Co", code="ALP")
        self.category = Category.objects.create(name="Dry Food")
        self.dog = AnimalType.objects.create(name="Dog", slug="dog")
        self.cat = AnimalType.objects.create(name="Cat", slug="cat")

        product_dog = Product.objects.create(
            name="Adult Mix",
            company=self.company,
            category=self.category,
            animal_type=self.dog,
        )
        product_cat = Product.objects.create(
            name="Kitten Mix",
            company=self.company,
            category=self.category,
            animal_type=self.cat,
        )
        ProductVariant.objects.create(product=product_dog, weight=2, price=10, stock=5)
        ProductVariant.objects.create(product=product_dog, weight=10, price=40, stock=12)
        ProductVariant.objects.create(product=product_cat, weight=1, price=8, stock=3)

    def test_inventory_lists_variants_separately_and_grouped(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:inventory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha Co")
        self.assertContains(response, "Dry Food")
        self.assertContains(response, "Dog")
        self.assertContains(response, "Cat")
        self.assertContains(response, "Adult Mix")
        self.assertContains(response, "Kitten Mix")
        self.assertContains(response, "Απόθεμα")
        self.assertContains(response, "12")
        self.assertContains(response, "3")

    def test_favourites_page_lists_products_by_purchase_count(self):
        product = Product.objects.get(name="Adult Mix")
        from products.models import Favourite

        Favourite.objects.filter(product=product).update(purchase_count=12)

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:favourites"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adult Mix")
        self.assertContains(response, "12")
        self.assertContains(response, "Favourites")

    def test_adjust_stock_add_and_remove(self):
        variant = ProductVariant.objects.get(product__name="Adult Mix", weight=2)
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "5"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 10)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "-3"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 7)

    def test_stock_zero_sets_out_of_stock_for_available_now(self):
        variant = ProductVariant.objects.get(product__name="Adult Mix", weight=2)
        variant.availability = ProductVariant.AVAILABILITY_AVAILABLE_NOW
        variant.stock = 2
        variant.save()
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "-2"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 0)
        self.assertEqual(variant.availability, ProductVariant.AVAILABILITY_OUT_OF_STOCK)

    def test_product_pause_hides_from_storefront(self):
        product = Product.objects.get(name="Adult Mix")
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:toggle_product_pause", args=[product.pk]),
            {"pause": "1"},
        )
        product.refresh_from_db()
        self.assertFalse(product.is_active)

        self.client.post(
            reverse("administration:toggle_product_pause", args=[product.pk]),
            {"pause": "0"},
        )
        product.refresh_from_db()
        self.assertTrue(product.is_active)

    def test_non_admin_cannot_adjust_stock(self):
        User = get_user_model()
        other = User.objects.create_user(email="other@example.com", password="x")
        variant = ProductVariant.objects.first()
        self.client.force_login(other)
        response = self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "10"},
        )
        self.assertEqual(response.status_code, 403)


class AdministrationOrdersPanelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
        )
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="test-pass-123",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True},
        )
        Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_CANCELLATION_REQUESTED,
            cart_cost=10,
            total_cost=10,
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Οδός 1",
            delivery_postal_code="11111",
            delivery_latitude=37.98,
            delivery_longitude=23.72,
            stripe_payment_intent_id="pi_test_123",
            cancellation_requested_at=timezone.now(),
        )

    def test_orders_page_lists_cancellation_requests(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:orders"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Αιτήματα ακύρωσης")
        self.assertContains(response, "customer@example.com")

    def test_payments_page_loads(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:payments"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pi_test_123")

    def test_orders_filter_by_user(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("administration:orders"),
            {"user": "customer@example.com", "period": "month"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "customer@example.com")
